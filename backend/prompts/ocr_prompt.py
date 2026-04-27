OCR_SYSTEM = """You are a specialist OCR agent trained to read handwritten exam answer sheets.
Your only job is to extract exactly what the student wrote — do not grade, do not judge.
Return ONLY valid JSON."""

def get_ocr_prompt(total_questions: int, exam_type: str) -> str:
    return f"""This is a page from a student handwritten exam answer sheet.

EXAM INFO:
- Expected number of questions: {total_questions}
- Exam type: {exam_type}

TASK: Read and extract every answer written by the student. Be extremely careful with:
- Handwritten option letters (a/b/c/d) — look for circled, underlined, or written letters
- Crossed out answers — use the FINAL answer the student settled on
- Partially written words — transcribe exactly as written
- Blank answers — mark as empty string

Return ONLY this JSON:
{{
  "student_name": "name or roll number visible on sheet, else UNKNOWN",
  "sheet_valid": true,
  "sheet_issues": "",
  "answers": [
    {{
      "q_no": "1",
      "answer": "b",
      "unclear": false,
      "unclear_reason": "",
      "confidence": 95
    }}
  ]
}}

CRITICAL RULES:
- confidence is 0-100: how sure you are you read this correctly
- Set unclear: true if handwriting is ambiguous, smudged, or crossed out multiple times
- For MCQ answers written as full words like "option b" or "B" — normalize to lowercase letter
- Do NOT skip any question number even if blank — include it with empty answer
- sheet_valid: false only if the page is completely blank or unreadable
- List answers in question number order"""


def get_ocr_multipage_prompt(page_number: int, total_pages: int, total_questions: int) -> str:
    return f"""This is page {page_number} of {total_pages} from a student handwritten exam answer sheet.
Total questions in the full exam: {total_questions}

Extract only the answers visible on THIS page.

Return ONLY this JSON:
{{
  "page": {page_number},
  "student_name": "name if visible on this page, else null",
  "answers": [
    {{
      "q_no": "1",
      "answer": "b",
      "unclear": false,
      "unclear_reason": "",
      "confidence": 95
    }}
  ]
}}

Same rules apply: confidence 0-100, unclear if not readable, normalize MCQ to lowercase letter."""
