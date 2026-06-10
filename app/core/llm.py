import logging
import os
from typing import Dict

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class GeminiAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code

_genai_client = None


def initialize_genai_client() -> None:
    """Create and cache the google.genai Client to avoid per-request initialization."""
    global _genai_client
    if _genai_client is not None:
        return
    import google.genai as genai

    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key or api_key == "your_gemma_api_key_here":
        logger.warning("GEMMA_API_KEY not set; GenAI client will not be initialized.")
        return
    _genai_client = genai.Client(api_key=api_key)


def call_gemma_model(prompt: str, model_name: str | None = None) -> Dict:
    import google.genai as genai
    from google.genai import errors as genai_errors

    global _genai_client
    if _genai_client is None:
        # lazy initialize if startup didn't run; keeps compatibility in tests
        initialize_genai_client()

    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key or api_key == "your_gemma_api_key_here":
        raise ValueError("GEMMA_API_KEY environment variable is not set or is using placeholder value")

    client = _genai_client or genai.Client(api_key=api_key)

    # Allow selecting model via environment variable `GEMMA_MODEL`.
    # If caller passes a `model_name`, it takes precedence; otherwise use env var or a sensible default.
    primary_model = model_name or os.getenv("GEMMA_MODEL", "models/gemma-2.5-flash")
    fallback_model = os.getenv("GEMMA_FALLBACK", "models/gemma-4-31b-it")

    def _call(model_to_use: str) -> Dict:
        response = client.models.generate_content(model=model_to_use, contents=prompt)
        # response may expose .text or nested fields depending on SDK; coerce to string
        text = getattr(response, "text", None) or str(response)
        model_version = model_to_use.split("/")[-1] if "/" in model_to_use else model_to_use
        return {"response": text, "llm_model": model_to_use, "llm_model_version": model_version}

    # First try primary model, then fallback to a lighter "flash" model on server errors.
    try:
        return _call(primary_model)
    except genai_errors.ServerError as exc:
        logger.warning("Primary Gemma model '%s' failed with server error, attempting fallback '%s'", primary_model, fallback_model)
        try:
            return _call(fallback_model)
        except Exception:
            logger.exception("Fallback Gemma model also failed")
            raise GeminiAPIError(f"Gemma generation failed for both '{primary_model}' and fallback '{fallback_model}'", status_code=503) from exc
    except genai_errors.ClientError as exc:
        # ClientErrors often indicate configuration or quota problems; surface as GeminiAPIError
        error_msg = str(exc)
        logger.exception("Gemma client error calling '%s'", primary_model)
        error_msg_lower = error_msg.lower()

        if "quota" in error_msg_lower or "rate limit" in error_msg_lower:
            raise GeminiAPIError(f"Gemini quota or rate limit reached for '{primary_model}': {error_msg}", status_code=429) from exc

        if "not found" in error_msg_lower or "is not found" in error_msg_lower:
            raise GeminiAPIError(f"Gemini model '{primary_model}' is not available for this API key: {error_msg}", status_code=502) from exc

        if "api key not valid" in error_msg_lower or "invalid api key" in error_msg_lower:
            raise ValueError(f"Invalid Gemma API key: {error_msg}") from exc

        raise GeminiAPIError(f"Gemini client error while calling '{primary_model}': {error_msg}", status_code=502) from exc
    except Exception as exc:
        logger.exception("Gemma generation failed for primary model '%s'", primary_model)
        # Try fallback for any other unexpected failures
        try:
            return _call(fallback_model)
        except Exception:
            logger.exception("Fallback Gemma model also failed")
            raise GeminiAPIError(f"Failed to generate model response: {exc}", status_code=503) from exc
