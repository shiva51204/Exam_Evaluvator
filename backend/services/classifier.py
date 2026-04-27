from services.llm_client import call_llm, call_llm_with_image, parse_llm_json
from prompts.classifier_prompt import CLASSIFIER_SYSTEM, get_classifier_prompt


def classify_and_extract_rubric(key_text: str, total_marks: int) -> dict | None:
    """
    Send the answer key text to the LLM to classify exam type
    and extract a structured rubric.
    Returns rubric dict or None on failure.
    """
    if not key_text or len(key_text.strip()) < 10:
        print("[Classifier] Answer key text is too short or empty.")
        return None

    prompt = get_classifier_prompt(key_text, total_marks)
    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM},
        {"role": "user", "content": prompt}
    ]

    raw = call_llm(messages, max_tokens=3000)
    rubric = parse_llm_json(raw)

    return _validate_and_fill_rubric(rubric, total_marks)


def classify_from_images(images_b64: list, total_marks: int) -> dict | None:
    """
    Classify and extract rubric from a handwritten/photo answer key.
    Uses vision LLM to read the images directly.
    """
    if not images_b64:
        print("[Classifier] No images provided.")
        return None

    print(f"[Classifier] Running image-based OCR on {len(images_b64)} page(s) of answer key...")

    # Build a prompt asking the LLM to both read AND structure the answer key
    user_prompt = f"""This is a handwritten or photographed exam answer key.

TOTAL MARKS: {total_marks}

Read every question number and its correct answer from the image(s).
Then return a fully structured rubric JSON.

Return ONLY this JSON (no markdown, no explanation):
{{
  "exam_type": "MCQ",
  "total_questions": 30,
  "total_marks": {total_marks},
  "questions": [
    {{
      "q_no": "1",
      "type": "MCQ",
      "correct_answer": "b",
      "marks": 1,
      "acceptable_alternatives": [],
      "keywords": [],
      "partial_marks_allowed": false,
      "rubric": ""
    }}
  ]
}}

Rules:
- Normalize all MCQ answers to lowercase single letters (a/b/c/d)
- If a question number is crossed out and replaced, use the final answer
- If total marks per question are not shown, divide {total_marks} equally
- Detect exam type: if all answers are single letters → MCQ; if answers are words/phrases → FILL_IN_THE_BLANKS; if longer → SHORT_ANSWER or DESCRIPTIVE
"""

    raw = call_llm_with_image(
        system_prompt=CLASSIFIER_SYSTEM,
        user_text=user_prompt,
        images_b64=images_b64,
        max_tokens=3000
    )

    rubric = parse_llm_json(raw)
    return _validate_and_fill_rubric(rubric, total_marks)


def _validate_and_fill_rubric(rubric: dict | None, total_marks: int) -> dict | None:
    """Shared validation and gap-filling for rubrics from any source."""
    if not rubric:
        print("[Classifier] Failed to parse rubric JSON.")
        return None

    if "questions" not in rubric or not isinstance(rubric["questions"], list):
        print("[Classifier] Rubric missing questions array.")
        return None

    if len(rubric["questions"]) == 0:
        print("[Classifier] Rubric has empty questions array.")
        return None

    # Ensure total_marks is set
    if "total_marks" not in rubric or not rubric["total_marks"]:
        rubric["total_marks"] = total_marks

    # Fill in marks per question if missing
    num_q = len(rubric["questions"])
    marks_per_q = total_marks / num_q if num_q > 0 else 1

    for q in rubric["questions"]:
        if "marks" not in q or not q["marks"]:
            q["marks"] = round(marks_per_q, 2)
        if "keywords" not in q:
            q["keywords"] = []
        if "acceptable_alternatives" not in q:
            q["acceptable_alternatives"] = []
        if "partial_marks_allowed" not in q:
            q["partial_marks_allowed"] = q.get("type") in ["SHORT_ANSWER", "DESCRIPTIVE"]

    print(f"[Classifier] Detected type: {rubric.get('exam_type')} | Questions: {len(rubric['questions'])}")
    return rubric
