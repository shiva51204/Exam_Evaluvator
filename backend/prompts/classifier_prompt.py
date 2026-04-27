CLASSIFIER_SYSTEM = """You are an expert exam analyst. Analyze the provided answer key text and extract a complete structured rubric.

Your job:
1. Detect the overall exam type
2. For each question, detect the specific question type
3. Extract the correct answer and marking scheme

Return ONLY valid JSON, no markdown, no explanation."""

def get_classifier_prompt(key_text: str, total_marks: int) -> str:
    return f"""Analyze this exam answer key and return a structured rubric.

ANSWER KEY TEXT:
{key_text}

TOTAL MARKS: {total_marks}

Identify each question type from these options:
- MCQ: Multiple choice with single correct option (a/b/c/d)
- FILL_IN_THE_BLANKS: Complete the sentence or fill a word/phrase
- SHORT_ANSWER: 1-3 sentence answer expected
- DESCRIPTIVE: Long answer requiring explanation, min 4-5 sentences
- MIXED: If the overall exam has multiple types

Return ONLY this JSON:
{{
  "exam_type": "MCQ | DESCRIPTIVE | FILL_IN_THE_BLANKS | SHORT_ANSWER | MIXED",
  "total_questions": 10,
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
- For MCQ: correct_answer is the option letter (a/b/c/d), lowercase
- For FILL_IN_THE_BLANKS: list acceptable_alternatives for spelling variations
- For DESCRIPTIVE/SHORT_ANSWER: list keywords that must appear in student answer
- For DESCRIPTIVE: write a rubric string describing what earns full/partial marks
- If marks per question are not specified, divide total_marks equally"""
