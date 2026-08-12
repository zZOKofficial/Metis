import json
import httpx
import google.genai as genai
from datetime import datetime
from typing import Optional, Any
from ..core.config import settings

# Models with mandatory thinking attach a thought_signature to functionCall
# parts. The API validates that the signature is echoed back verbatim in the
# next request. When no real signature is available (e.g. history transferred
# from another flow), the documented placeholder below is accepted.
SKIP_THOUGHT_SIGNATURE = "skip_thought_signature_validator"
GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
        self._client: Optional[Any] = None
        # None = not yet loaded from the store; '' = saved key cleared
        self._saved_key: Optional[str] = None

    def configure(self, api_key: str) -> None:
        """Set the saved key in-process and force the client to rebuild."""
        self._saved_key = api_key
        self._client = None

    def _load_saved_key(self) -> str:
        try:
            from ..services.firestore import app_state_service
            doc = app_state_service.get('ai_config')
            return (doc or {}).get('api_key', '') or ''
        except Exception:
            return ''

    def _effective_key(self) -> str:
        """Saved key wins over the env key; unset keys report as unconfigured."""
        if self._saved_key is None:
            self._saved_key = self._load_saved_key()
        return self._saved_key or settings.GEMINI_API_KEY

    def _ensure_client(self) -> Optional[Any]:
        if self._client is None and self._effective_key():
            self._client = genai.Client(api_key=self._effective_key())
        return self._client

    def is_configured(self) -> bool:
        return bool(self._effective_key())

    def key_source(self) -> Optional[str]:
        if not self._effective_key():
            return None
        return 'user' if self._saved_key else 'env'

    @staticmethod
    def is_valid_model(model: str) -> bool:
        return any(m["id"] == model for m in GeminiService.AVAILABLE_MODELS)

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
    ) -> str:
        """Generate text from Gemini, optionally continuing a conversation history."""
        if not self._effective_key():
            return "Gemini API key not configured."

        try:
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction,
            )

            contents = self._format_turn(history or [])
            contents.append({'role': 'user', 'parts': [{'text': prompt}]})

            client = self._ensure_client()
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
    ) -> str:
        """Generate structured text (lower temperature for consistency)."""
        return self.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            max_tokens=2048,
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
        if not self._effective_key():
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

            data = self._post_generate(body, model=model)
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

    # === Raw REST helpers ===

    def _post_generate(self, body: dict[str, Any], model: Optional[str] = None) -> dict[str, Any]:
        """POST to the generateContent REST endpoint, returning the JSON dict."""
        url = GENERATE_CONTENT_URL.format(model=model or self.MODEL)
        try:
            payload = json.dumps(body, default=self._json_default)
            resp = httpx.post(
                url,
                content=payload,
                headers={
                    "x-goog-api-key": self._effective_key(),
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
