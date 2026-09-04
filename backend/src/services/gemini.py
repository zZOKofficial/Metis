import base64
import json
import re
import httpx
import google.genai as genai
from datetime import datetime
from typing import Optional, Any, Callable
from ..core.config import settings

# Models with mandatory thinking attach a thought_signature to functionCall
# parts. The API validates that the signature is echoed back verbatim in the
# next request. When no real signature is available (e.g. history transferred
# from another flow), the documented placeholder below is accepted.
SKIP_THOUGHT_SIGNATURE = "skip_thought_signature_validator"
GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS_LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiService:
    """Service for interacting with Google Gemini AI."""

    # Lightest verified model. Older 2.x models (e.g. gemini-2.0-flash,
    # gemini-2.5-pro) return 404 "no longer available to new users", and the
    # "-latest" aliases may resolve to heavier thinking models.
    MODEL = "gemini-flash-lite-latest"

    # Models selectable from the chat UI, ordered by speed / cost. All entries
    # verified available on the account's plan (2.x models are not).
    AVAILABLE_MODELS: list[dict[str, str]] = [
        {"id": "gemini-flash-lite-latest", "name": "Gemini Flash Lite (fastest / most economical)"},
        {"id": "gemini-flash-latest", "name": "Gemini Flash (default)"},
        {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite"},
        {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
        {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash"},
    ]

    def __init__(self):
        # Clients keyed by the API key that built them: one owner's client must
        # never serve another owner's request, and rebuilding per call would
        # throw away the connection pool.
        self._clients: dict[str, Any] = {}
        # Saved keys by scope. A scope absent from the dict has not been read
        # from the store yet; '' means it was read and there is no saved key.
        self._saved_keys: dict[Optional[str], str] = {}

    def reset_cache(self) -> None:
        """Forget every resolved key and client. For tests and key changes."""
        self._clients.clear()
        self._saved_keys.clear()

    @staticmethod
    def scope_doc_id(owner_uid: Optional[str]) -> str:
        """Where this caller's key lives.

        A signed-in owner gets their own document. With no identity -- auth
        disabled, or a business created before ownership existed -- it is the
        single global document a local install has always used.
        """
        return f'ai_config:{owner_uid}' if owner_uid else 'ai_config'

    def configure(self, api_key: str, owner_uid: Optional[str] = None) -> None:
        """Set one scope's saved key in-process and drop the stale clients."""
        self._saved_keys[owner_uid] = api_key
        self._clients.clear()

    def _load_saved_key(self, owner_uid: Optional[str]) -> str:
        try:
            from ..services.firestore import app_state_service
            doc = app_state_service.get(self.scope_doc_id(owner_uid))
            return (doc or {}).get('api_key', '') or ''
        except Exception:
            return ''

    def _effective_key(self, owner_uid: Optional[str] = None) -> str:
        """This caller's key: their own if they saved one, else the env key.

        An owner never falls back to another owner's saved key -- that is the
        whole point of scoping it, since the quota and the bill follow the key.
        They may fall back to GEMINI_API_KEY, which belongs to whoever runs the
        deployment and is deliberately shared.
        """
        if owner_uid not in self._saved_keys:
            self._saved_keys[owner_uid] = self._load_saved_key(owner_uid)
        return self._saved_keys[owner_uid] or settings.GEMINI_API_KEY

    def _ensure_client(self, owner_uid: Optional[str] = None) -> Optional[Any]:
        key = self._effective_key(owner_uid)
        if not key:
            return None
        if key not in self._clients:
            self._clients[key] = genai.Client(api_key=key)
        return self._clients[key]

    def is_configured(self, owner_uid: Optional[str] = None) -> bool:
        return settings.METIS_MOCK_AI or bool(self._effective_key(owner_uid))

    def key_source(self, owner_uid: Optional[str] = None) -> Optional[str]:
        if not self._effective_key(owner_uid):
            return 'mock' if settings.METIS_MOCK_AI else None
        return 'user' if self._saved_keys.get(owner_uid) else 'env'

    @staticmethod
    def is_valid_model(model: str) -> bool:
        return any(m["id"] == model for m in GeminiService.AVAILABLE_MODELS)

    def test_key(self, api_key: Optional[str] = None, owner_uid: Optional[str] = None) -> dict[str, Any]:
        """Live auth check: list models with the given (or currently effective) key.

        Costs no generation quota — it's a pure authentication probe.
        Returns {"valid": bool, "error": Optional[str]}.
        """
        key = api_key if api_key is not None else self._effective_key(owner_uid)
        if not key:
            if settings.METIS_MOCK_AI:
                return {"valid": True, "error": None}
            return {"valid": False, "error": "No API key configured."}

        try:
            resp = httpx.get(
                MODELS_LIST_URL,
                headers={"x-goog-api-key": key},
                params={"pageSize": 1},
                timeout=15,
            )
        except Exception as e:
            return {"valid": False, "error": f"Request failed: {str(e)}"}

        if resp.status_code != 200:
            try:
                message = resp.json().get("error", {}).get("message", resp.text[:200])
            except Exception:
                message = resp.text[:200]
            return {"valid": False, "error": f"{resp.status_code} {message}"}
        return {"valid": True, "error": None}

    @staticmethod
    def _format_turn(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert app role names to Gemini API roles, dropping leading model turns."""
        contents: list[dict[str, Any]] = []
        for turn in history:
            role = turn.get('role')
            if role == 'assistant':
                gemini_role = 'model'
            elif role == 'user':
                gemini_role = 'user'
            else:
                continue
            text = turn.get('content')
            if not text or not str(text).strip():
                continue
            if not contents and gemini_role == 'model':
                continue
            contents.append({'role': gemini_role, 'parts': [{'text': str(text)}]})
        return contents

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        history: Optional[list[dict[str, Any]]] = None,
        model: Optional[str] = None,
        owner_uid: Optional[str] = None,
    ) -> str:
        """Generate text from Gemini, optionally continuing a conversation history."""
        if not self._effective_key(owner_uid):
            return "Gemini API key not configured."

        try:
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction,
            )

            contents = self._format_turn(history or [])
            contents.append({'role': 'user', 'parts': [{'text': prompt}]})

            client = self._ensure_client(owner_uid)
            response = client.models.generate_content(
                model=model or self.MODEL,
                contents=contents,
                config=config,
            )
            return response.text.strip()
        except Exception as e:
            return f"AI generation error: {str(e)}"

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        owner_uid: Optional[str] = None,
    ) -> str:
        """Generate structured text (lower temperature for consistency)."""
        return self.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            max_tokens=2048,
            owner_uid=owner_uid,
        )

    def run_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        on_call: Any,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        history: Optional[list[dict[str, Any]]] = None,
        max_rounds: int = 5,
        model: Optional[str] = None,
        raw_message: Optional[str] = None,
        owner_uid: Optional[str] = None,
    ) -> dict[str, Any]:
        """Agentic function-calling loop.

        The model can call one or more tools per round; each round's results
        are fed back and the loop repeats until the model produces final text
        or `max_rounds` is reached. `on_call(name, args)` is invoked for every
        tool call and its return value is sent back to the model.

        Returns {"text": str, "agent_actions": [{"tool", "result"}]}.

        Implemented over the raw REST API because the google-genai SDK in this
        version drops `thoughtSignature` when parsing responses, which makes it
        impossible to echo the required signature back on follow-up calls.
        """
        if settings.METIS_MOCK_AI:
            return self._mock_run_with_tools(raw_message if raw_message is not None else prompt, on_call)

        if not self._effective_key(owner_uid):
            return {"text": "Gemini API key not configured.", "agent_actions": []}

        contents = self._format_turn(history or [])
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        actions: list[dict[str, Any]] = []

        for _ in range(max_rounds):
            body: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
                "tools": [{"functionDeclarations": tools}],
            }
            if system_instruction:
                body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            data = self._post_generate(body, model=model, owner_uid=owner_uid)
            if "error" in data:
                return {"text": f"AI generation error: {data['error']}", "agent_actions": actions}

            parts = self._response_parts(data)
            text = self._extract_text_from_parts(parts)
            calls = self._parse_function_calls(parts)

            if not calls:
                return {"text": text, "agent_actions": actions}

            contents.append({"role": "model", "parts": self._ensure_thought_signatures(parts)})

            response_parts: list[dict[str, Any]] = []
            for call in calls:
                outcome = on_call(call.get("name", ""), call.get("args") or {})
                actions.append({"tool": call.get("name"), "result": outcome})
                item: dict[str, Any] = {"name": call.get("name", ""), "response": outcome or {}}
                if call.get("id"):
                    item["id"] = call["id"]
                response_parts.append({"functionResponse": item})
            contents.append({"role": "user", "parts": response_parts})

        return {
            "text": "I reached the tool-call limit before I could finish. Please ask again or rephrase.",
            "agent_actions": actions,
        }

    # === Mock AI mode ===

    @staticmethod
    def _mock_run_with_tools(message: str, on_call: Callable[[str, dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        """Deterministic stand-in for the tool-calling loop, no Gemini key required.

        Recognizes a handful of common owner-chat intents by pattern-matching
        the raw message (restock / mark out of stock / set stock / add or
        delete a product / move an order to a status) and dispatches straight
        to the matching tool via `on_call`, the same callback the real loop
        uses. Anything else gets a canned help message.
        """
        text = (message or '').strip()
        low = text.lower()
        tool: Optional[str] = None
        args: dict[str, Any] = {}

        m = re.search(r'\bmark\s+(.+?)\s+(?:as\s+)?out of stock\b', low)
        if m:
            tool, args = 'set_stock', {'product_id': m.group(1).strip(), 'quantity': 0}

        if tool is None:
            m = re.search(r'\bset\s+(?:the\s+)?stock\s+(?:of|for)\s+(.+?)\s+to\s+(\d+)\b', low)
            if m:
                tool, args = 'set_stock', {'product_id': m.group(1).strip(), 'quantity': int(m.group(2))}

        if tool is None:
            m = re.search(r'\brestock\s+(.+?)\s+(?:by|with)\s+(\d+)\b', low)
            if m:
                tool, args = 'restock_product', {'product_id': m.group(1).strip(), 'quantity': int(m.group(2))}

        if tool is None:
            m = re.search(r'\badd\s+(\d+)\s+(?:units?\s+)?(?:of\s+)?(?:stock\s+)?(?:to|for)\s+(.+)', low)
            if m:
                tool, args = 'restock_product', {'product_id': m.group(2).strip(), 'quantity': int(m.group(1))}

        if tool is None:
            m = re.search(r'\b(?:delete|remove)\s+(?:the\s+)?product\s+(.+)', low)
            if m:
                tool, args = 'delete_product', {'product_id': m.group(1).strip().rstrip('.')}

        if tool is None:
            m = re.search(
                r'\b(?:add|create)\s+(?:a\s+)?(?:new\s+)?product\s+(?:called\s+|named\s+)?"?([^",]+?)"?\s+'
                r'(?:for|at|priced at|priced|price)\s+(?:[^\d\s]{1,4}\s*)?(\d+(?:\.\d+)?)',
                text,
                re.IGNORECASE,
            )
            if m:
                tool, args = 'create_product', {'name': m.group(1).strip(), 'price': float(m.group(2))}

        if tool is None:
            m = re.search(
                r'\border\s+([a-z0-9\-]{4,})\b.*?\b(pending|confirmed|processing|shipped|delivered|cancelled|returned)\b',
                low,
            )
            if m:
                tool, args = 'update_order_status', {'order_id': m.group(1), 'status': m.group(2)}

        if tool is None:
            return {
                'text': (
                    'Mock AI mode is on (no Gemini key needed). Try a command like: '
                    '"restock Blue Shirt by 10", "mark Blue Shirt out of stock", '
                    '"set stock of Blue Shirt to 5", \'add product "Red Cap" for 450\', '
                    '"delete product Red Cap", or "move order <id> to shipped".'
                ),
                'agent_actions': [],
            }

        outcome = on_call(tool, args)
        label = tool.replace('_', ' ')
        status = outcome.get('status')
        if status == 'executed':
            summary = f'Done — {label} completed.'
        elif status == 'staged':
            approval_id = str(outcome.get('approval_id') or '')
            summary = f'Staged for your approval (approval #{approval_id[:8].upper()}).' if approval_id else 'Staged for your approval.'
        else:
            summary = f"Couldn't do that — {outcome.get('error', 'unknown error')}."

        return {'text': summary, 'agent_actions': []}

    # === Photo → product draft ===

    _JSON_BLOCK = re.compile(r'\{.*\}', re.DOTALL)

    def draft_product_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = 'image/jpeg',
        owner_uid: Optional[str] = None,
    ) -> dict[str, Any]:
        """Ask Gemini vision to draft a product listing from a photo.

        Returns a dict with name/description/price/category (price 0 and
        empty strings on failure — the owner fills in the rest by hand).
        """
        if settings.METIS_MOCK_AI:
            return {
                'name': 'New product (from photo)',
                'description': 'Mock AI mode is on — describe this item and set its price by hand.',
                'price': 0.0,
                'category': '',
            }

        if not self._effective_key(owner_uid):
            return {'name': '', 'description': '', 'price': 0.0, 'category': ''}

        prompt = (
            'Look at this product photo and draft a catalog listing for it. '
            'Reply with ONLY a JSON object, no markdown fences, no commentary, '
            'shaped exactly like: '
            '{"name": "...", "description": "...", "price": 0, "category": "..."}. '
            'Keep the description to one short sentence. Estimate a reasonable '
            'retail price as a plain number (no currency symbol). If unsure, '
            'use your best guess rather than leaving a field empty.'
        )
        body = {
            'contents': [{
                'role': 'user',
                'parts': [
                    {'text': prompt},
                    {'inlineData': {'mimeType': mime_type, 'data': base64.b64encode(image_bytes).decode()}},
                ],
            }],
            'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 512},
        }
        data = self._post_generate(body, owner_uid=owner_uid)
        if 'error' in data:
            return {'name': '', 'description': '', 'price': 0.0, 'category': ''}

        raw_text = self._extract_text_from_parts(self._response_parts(data))
        match = self._JSON_BLOCK.search(raw_text)
        if not match:
            return {'name': '', 'description': '', 'price': 0.0, 'category': ''}

        try:
            parsed = json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return {'name': '', 'description': '', 'price': 0.0, 'category': ''}

        try:
            price = float(parsed.get('price') or 0)
        except (TypeError, ValueError):
            price = 0.0

        return {
            'name': str(parsed.get('name') or '').strip(),
            'description': str(parsed.get('description') or '').strip(),
            'price': price,
            'category': str(parsed.get('category') or '').strip(),
        }

    # === Raw REST helpers ===

    def _post_generate(
        self,
        body: dict[str, Any],
        model: Optional[str] = None,
        owner_uid: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST to the generateContent REST endpoint, returning the JSON dict."""
        url = GENERATE_CONTENT_URL.format(model=model or self.MODEL)
        try:
            payload = json.dumps(body, default=self._json_default)
            resp = httpx.post(
                url,
                content=payload,
                headers={
                    "x-goog-api-key": self._effective_key(owner_uid),
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
        except Exception as e:
            return {"error": f"request failed: {str(e)}"}

        if resp.status_code != 200:
            try:
                error = resp.json().get("error", {})
                message = error.get("message", resp.text[:300])
            except Exception:
                message = resp.text[:300]
            return {"error": f"{resp.status_code} {message}"}
        return resp.json()

    @staticmethod
    def _response_parts(data: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            candidates = data.get("candidates") or []
            if not candidates:
                return []
            return (candidates[0].get("content") or {}).get("parts") or []
        except Exception:
            return []

    @staticmethod
    def _extract_text_from_parts(parts: list[dict[str, Any]]) -> str:
        try:
            return "".join(
                p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")
            ).strip()
        except Exception:
            return ""

    @staticmethod
    def _parse_function_calls(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []
        try:
            for p in parts:
                if isinstance(p, dict) and "functionCall" in p:
                    fc = p["functionCall"] or {}
                    calls.append({
                        "id": fc.get("id"),
                        "name": fc.get("name", ""),
                        "args": fc.get("args") or {},
                        "thought_signature": p.get("thoughtSignature"),
                    })
        except Exception:
            pass
        return calls

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """JSON fallback for values inside tool results (datetimes etc.)."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    @staticmethod
    def _ensure_thought_signatures(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Make sure every functionCall part carries a thought signature.

        Real signatures received from the model are preserved verbatim; parts
        without one (e.g. parallel function calls) get the documented
        placeholder so the API still validates the turn.
        """
        result: list[dict[str, Any]] = []
        for p in parts:
            if isinstance(p, dict) and "functionCall" in p and not p.get("thoughtSignature"):
                p = {**p, "thoughtSignature": SKIP_THOUGHT_SIGNATURE}
            result.append(p)
        return result


gemini_service = GeminiService()
