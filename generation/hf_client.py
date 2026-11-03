"""HuggingFace Inference API client for text generation with structured JSON output."""

import json
import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models"
HF_SERVERLESS_URL = "https://api-inference.huggingface.co/v1/chat/completions"

# Recommended free models (serverless inference, no dedicated endpoint needed)
RECOMMENDED_MODELS: list[str] = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "microsoft/Phi-3.5-mini-instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
    "HuggingFaceH4/zephyr-7b-beta",
    "google/gemma-2-2b-it",
]

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
REQUEST_TIMEOUT_S = 60.0
MAX_RETRIES = 2


def _strip_json_block(raw: str) -> str:
    """Strip markdown code fences and extract raw JSON from LLM output."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _extract_json_from_text(text: str) -> str:
    """Try to extract JSON object from text that may have surrounding prose."""
    text = _strip_json_block(text)
    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def call_hf_chat_completion(
    system_prompt: str,
    user_message: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_new_tokens: int = 1200,
    json_mode: bool = True,
) -> str:
    """Call HuggingFace Inference API using the chat completions compatible endpoint.

    Returns the raw response text from the model.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_new_tokens,
        "temperature": temperature,
        "stream": False,
    }

    url = f"{HF_SERVERLESS_URL}"

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
                response = client.post(url, headers=headers, json=payload)

                if response.status_code == 503:
                    # Model loading — wait and retry
                    wait_time = 20 * (attempt + 1)
                    logger.warning(
                        "HF model loading (503). Waiting %ds before retry %d/%d...",
                        wait_time,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait_time)
                    continue

                if response.status_code == 429:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(
                        "HF rate limited (429). Waiting %ds before retry %d/%d...",
                        wait_time,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()

                # OpenAI-compatible response format
                if "choices" in data:
                    content = data["choices"][0]["message"]["content"]
                    return content if content else ""

                # Fallback: text generation format
                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "")

                return str(data)

        except httpx.HTTPStatusError as e:
            last_error = e
            logger.error("HF API HTTP error %d: %s", e.response.status_code, e.response.text[:300])
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning("HF API timeout on attempt %d/%d", attempt + 1, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                time.sleep(5)
        except Exception as e:
            last_error = e
            logger.error("Unexpected error calling HF API: %s", e)
            break

    raise RuntimeError(f"HF API call failed after {MAX_RETRIES + 1} attempts: {last_error}")


def generate_json_response(
    system_prompt: str,
    user_message: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
) -> dict:
    """Generate and parse a JSON response from HuggingFace model.

    Appends explicit JSON output instruction to the user message.
    """
    json_instruction = (
        "\n\nIMPORTANT: Your ENTIRE response must be a single valid JSON object. "
        "Do NOT include any explanation, prose, or markdown before or after the JSON. "
        "Start your response with { and end with }."
    )

    enhanced_user = user_message + json_instruction

    raw = call_hf_chat_completion(
        system_prompt=system_prompt,
        user_message=enhanced_user,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_new_tokens=1200,
        json_mode=True,
    )

    # Attempt to parse extracted JSON
    extracted = _extract_json_from_text(raw)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse HF JSON output: %s\nRaw: %s", e, raw[:500])
        return {}


def check_hf_connection(api_key: str, model: str = DEFAULT_MODEL) -> tuple[bool, str]:
    """Test HuggingFace API connectivity and return (success, message)."""
    try:
        result = call_hf_chat_completion(
            system_prompt="You are a helpful assistant.",
            user_message="Reply with exactly: OK",
            api_key=api_key,
            model=model,
            max_new_tokens=10,
            temperature=0.0,
        )
        return True, f"HF API connected. Model: {model}. Response: {result[:50]}"
    except Exception as e:
        return False, f"HF API error: {e}"
