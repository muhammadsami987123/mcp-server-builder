"""Centralized OpenAI access. The only file in the codebase that imports `openai`."""

from __future__ import annotations

import json

from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError
from pydantic import BaseModel, ValidationError

from app import config


class OpenAIServiceError(Exception):
    """Raised when a structured OpenAI call cannot produce a valid response."""


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def call_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    *,
    retries: int = 2,
) -> BaseModel:
    if not config.OPENAI_API_KEY:
        raise OpenAIServiceError("OpenAI API key is not configured.")

    client = _client()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error: str = ""
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            completion = await client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            last_error = str(exc)
            break
        except Exception as exc:  # never leak raw SDK exceptions
            last_error = str(exc)
            break

        raw_content = completion.choices[0].message.content or ""
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            last_error = f"Response was not valid JSON: {exc}"
            messages.append({"role": "assistant", "content": raw_content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON. "
                        f"Error: {last_error}. Respond again with corrected, strictly valid JSON only."
                    ),
                }
            )
            continue

        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            last_error = str(exc)
            if attempt == attempts - 1:
                break
            messages.append({"role": "assistant", "content": raw_content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous JSON response failed schema validation with the "
                        f"following error(s):\n{last_error}\n"
                        "Respond again with corrected JSON that strictly matches the required schema."
                    ),
                }
            )

    raise OpenAIServiceError(
        f"OpenAI failed to produce a valid structured response after {attempts} attempt(s): {last_error}"
    )
