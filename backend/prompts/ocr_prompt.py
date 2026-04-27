OCR_SYSTEM = """You are a specialist OCR agent trained to read handwritten exam answer sheets.
Your only job is to extract exactly what the student wrote — do not grade, do not judge.
CRITICAL: Return ONLY valid JSON. No preamble. No explanation. No markdown. Start your response with { and end with }."""


def get_ocr_prompt(total_questions: int, exam_type: str) -> str:
    return f"""Extract every answer from this handwritten exam answer sheet.

EXAM INFO:
- Expected questions: {total_questions}
- Exam type: {exam_type}

RULES:
- Extract the exact text the student wrote for each answer
- For MCQ: normalise to lowercase letter (a/b/c/d) even if written as "Option B" or "B"
- Crossed-out answers: use the FINAL answer only
- Blank answers: use empty string ""
- Set unclear: true if handwriting is truly ambiguous or smudged beyond reading
- confidence: 0-100 (your certainty you read it correctly)
- Include EVERY question number even if blank

Output ONLY this JSON (no text before or after):
{{"student_name":"name or UNKNOWN","sheet_valid":true,"sheet_issues":"","answers":[{{"q_no":"1","answer":"b","unclear":false,"unclear_reason":"","confidence":95}}]}}"""


def get_ocr_multipage_prompt(page_number: int, total_pages: int, total_questions: int) -> str:
    return f"""Extract answers from page {page_number} of {total_pages} of a handwritten exam.
Total exam questions: {total_questions}

Extract only answers visible on THIS page.

Output ONLY this JSON (no text before or after):
{{"page":{page_number},"student_name":null,"answers":[{{"q_no":"1","answer":"b","unclear":false,"unclear_reason":"","confidence":95}}]}}"""
