import base64
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import anthropic

from app.core.config import settings


@lru_cache
def get_client() -> anthropic.Anthropic:
    if settings.claude_provider == "foundry":
        return anthropic.AnthropicFoundry(api_key=settings.foundry_api_key, resource=settings.foundry_resource)
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def file_to_content_block(file_path: str, mime_type: str) -> dict:
    data = base64.standard_b64encode(Path(file_path).read_bytes()).decode("utf-8")
    if mime_type == "application/pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": mime_type, "data": data}}
    if mime_type.startswith("image/"):
        return {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": data}}
    # Fall back to plain text content for unsupported binary types
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    return {"type": "text", "text": text}


def call_structured(
    *,
    system: str,
    content: list[dict] | str,
    schema: dict,
    effort: str = "medium",
    use_thinking: bool = False,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call Claude with a JSON-schema-constrained response and return the parsed dict.

    Uses output_config.format so the response is guaranteed to validate against
    `schema` — no prefill, no manual JSON-extraction regexes.
    """
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": settings.claude_model,
        "max_tokens": max_tokens,
        "system": system,
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
        "messages": [{"role": "user", "content": content}],
    }
    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    response = client.messages.create(**kwargs)

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to process this request (safety refusal).")

    text = next((block.text for block in response.content if block.type == "text"), None)
    if text is None:
        raise RuntimeError(f"No text block in Claude response (stop_reason={response.stop_reason})")
    return json.loads(text)
