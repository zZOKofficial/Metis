import google.genai as genai
from typing import Optional
from ..core.config import settings


class GeminiService:
    """Service for interacting with Google Gemini AI."""

    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text from Gemini."""
        if not self.client:
            return "Gemini API key not configured."

        try:
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction,
            )

            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
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


gemini_service = GeminiService()
