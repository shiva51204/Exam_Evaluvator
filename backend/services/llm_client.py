import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
LLM_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def call_llm(messages: list, max_tokens: int = 4096, temperature: float = 0.1) -> str | None:
    """
    Call the LLM API with retry logic.
    Returns the response content string or None on failure.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                LLM_URL,
                headers=headers,
                json=payload,
                timeout=(10, 600)
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content

        except requests.exceptions.Timeout:
            print(f"[LLM] Timeout on attempt {attempt}/{MAX_RETRIES}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            print(f"[LLM] HTTP error {status} on attempt {attempt}/{MAX_RETRIES}: {e}")
            # Don't retry on 4xx client errors except 429 rate limit
            if e.response and e.response.status_code not in [429, 500, 502, 503]:
                return None
        except Exception as e:
            print(f"[LLM] Unexpected error on attempt {attempt}/{MAX_RETRIES}: {e}")

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY * attempt
            print(f"[LLM] Retrying in {wait}s...")
            time.sleep(wait)

    print(f"[LLM] All {MAX_RETRIES} attempts failed.")
    return None


def parse_llm_json(raw: str) -> dict | None:
    """Clean and parse JSON from LLM response."""
    if not raw:
        return None
    try:
        cleaned = raw.strip()
        # Strip markdown code fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON parse error: {e}. Raw: {raw[:300]}")
        return None


def call_llm_with_image(
    system_prompt: str,
    user_text: str,
    images_b64: list,
    mime_type: str = "image/jpeg",
    max_tokens: int = 4096
) -> str | None:
    """
    Call LLM with image(s) attached.
    images_b64: list of base64 encoded image strings
    """
    content = []

    # Add all images first for better attention
    for img in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{img}"
            }
        })

    # Add text prompt after images
    content.append({
        "type": "text",
        "text": user_text
    })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]

    return call_llm(messages, max_tokens=max_tokens)
