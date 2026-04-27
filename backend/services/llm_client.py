import requests
import json
import re
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

            # Check finish reason — warn if truncated
            finish_reason = data["choices"][0].get("finish_reason", "")
            if finish_reason == "length":
                print(f"[LLM] WARNING: Response was truncated (finish_reason=length). "
                      f"Consider increasing max_tokens (currently {max_tokens}).")

            content = data["choices"][0]["message"]["content"]
            return content

        except requests.exceptions.Timeout:
            print(f"[LLM] Timeout on attempt {attempt}/{MAX_RETRIES}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            print(f"[LLM] HTTP error {status} on attempt {attempt}/{MAX_RETRIES}: {e}")
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
    """
    Clean and parse JSON from LLM response.
    Handles:
    - Markdown code fences (```json ... ```)
    - Preamble text before the JSON object
    - Truncated JSON (attempts recovery by closing open structures)
    """
    if not raw:
        return None

    cleaned = raw.strip()

    # ── 1. Strip markdown code fences ──────────────────────────────────
    if "```" in cleaned:
        # Extract content between first ``` and last ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

    # ── 2. Find the first { or [ — skip any preamble text ──────────────
    first_brace = -1
    for i, ch in enumerate(cleaned):
        if ch in ('{', '['):
            first_brace = i
            break

    if first_brace == -1:
        print(f"[LLM] No JSON object found in response. Raw[:300]: {raw[:300]}")
        return None

    cleaned = cleaned[first_brace:]

    # ── 3. Try direct parse first ──────────────────────────────────────
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── 4. Truncation recovery — try to close open JSON structures ─────
    print(f"[LLM] JSON incomplete, attempting truncation recovery...")
    recovered = _recover_truncated_json(cleaned)
    if recovered:
        try:
            result = json.loads(recovered)
            print(f"[LLM] Truncation recovery succeeded.")
            return result
        except json.JSONDecodeError:
            pass

    print(f"[LLM] JSON parse failed even after recovery. Raw[:300]: {raw[:300]}")
    return None


def _recover_truncated_json(partial: str) -> str | None:
    """
    Attempt to close a truncated JSON string by tracking open braces/brackets/strings.
    Returns a potentially valid JSON string, or None if recovery is not possible.
    """
    # Remove the last incomplete object/array entry up to the last complete comma-separated item
    # Strategy: find the last complete item by looking for the last }, or ] or "value" before truncation

    stack = []       # track open { and [
    in_string = False
    escape_next = False
    last_safe_pos = 0  # position after the last complete top-level item

    i = 0
    while i < len(partial):
        ch = partial[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if ch == '\\' and in_string:
            escape_next = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            i += 1
            continue

        if in_string:
            i += 1
            continue

        if ch in ('{', '['):
            stack.append(ch)
        elif ch in ('}', ']'):
            if stack:
                stack.pop()
                # If stack is at depth 1 (inside top-level object/array), mark safe position
                if len(stack) == 1:
                    last_safe_pos = i + 1
        elif ch == ',' and len(stack) == 1:
            last_safe_pos = i + 1  # after comma is a safe truncation point

        i += 1

    if not stack:
        # Wasn't actually truncated
        return partial

    # Truncate to last safe position and close all open structures
    truncated = partial[:last_safe_pos].rstrip().rstrip(',')

    # Close all open structures in reverse order
    closers = {'{': '}', '[': ']'}
    closing = ''.join(closers[s] for s in reversed(stack))

    return truncated + closing


def call_llm_with_image(
    system_prompt: str,
    user_text: str,
    images_b64: list,
    mime_type: str = "image/jpeg",
    max_tokens: int = 6000   # Raised from 4096 — handwritten sheets produce long OCR JSON
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
