GRADER_SYSTEM = """You are a fair and experienced exam grader. You grade based on the rubric provided.
You understand that students may make minor spelling mistakes, use informal phrasing, or write in broken sentences — this is normal in handwritten exams.
Return ONLY valid JSON. No markdown. No explanation outside the JSON."""


def get_mcq_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade these MCQ answers.

ANSWER KEY:
{rubric}

STUDENT ANSWERS:
{student_answers}

Rules:
- Compare each answer to correct_answer, case-insensitive
- Full marks if match, 0 if no match
- If student answer is unclear (unclear: true): award 0, needs_review: true
- If student left blank: award 0, needs_review: false

Return ONLY this JSON:
{{
  "question_scores": [
    {{
      "q_no": "1",
      "student_answer": "b",
      "correct_answer": "b",
      "marks_awarded": 1,
      "marks_possible": 1,
      "correct": true,
      "needs_review": false,
      "feedback": "Correct"
    }}
  ]
}}"""


def get_fill_blank_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade these Fill in the Blanks answers.

ANSWER KEY:
{rubric}

STUDENT ANSWERS:
{student_answers}

Rules:
- Accept exact matches AND acceptable_alternatives listed in the rubric
- Ignore case differences completely
- Accept minor spelling mistakes (1-3 character edits, e.g. "mimic" vs "minic", "intelligence" vs "inteligence")
- Accept common OCR/handwriting artefacts: missing letters, swapped letters, extra spaces
- Accept answers that convey the same meaning even if worded differently
- If unclear: needs_review: true, award 0
- Partial credit NOT allowed unless partial_marks_allowed is true

Return ONLY this JSON:
{{
  "question_scores": [
    {{
      "q_no": "1",
      "student_answer": "photosynthesis",
      "correct_answer": "photosynthesis",
      "marks_awarded": 1,
      "marks_possible": 1,
      "correct": true,
      "needs_review": false,
      "feedback": "Correct"
    }}
  ]
}}"""


def get_short_answer_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade these Short Answer responses. Students wrote by hand — expect spelling mistakes, abbreviations, and informal phrasing.

ANSWER KEY AND RUBRIC:
{rubric}

STUDENT ANSWERS:
{student_answers}

Spelling and language rules (IMPORTANT):
- Ignore all spelling mistakes. "minic" = "mimic", "inteligence" = "intelligence", "compter" = "computer"
- Ignore capitalisation differences
- Ignore extra/missing spaces and punctuation
- Ignore grammar issues — focus on whether the concept is correct
- Accept synonyms and paraphrases that convey the same meaning
- Accept abbreviations if unambiguous (e.g. "ML" = "Machine Learning", "AI" = "Artificial Intelligence")
- DO NOT penalise for poor handwriting artefacts (OCR may have introduced errors)

Grading rules:
- Check if the student answer covers the key concepts (keywords list)
- Award marks proportionally based on concept coverage
- Full marks: all key concepts present (even if worded differently or with spelling errors)
- Partial marks: some concepts covered
- 0 marks: completely wrong, off-topic, or blank
- If the answer is ambiguous due to illegible handwriting: needs_review: true

Return ONLY this JSON:
{{
  "question_scores": [
    {{
      "q_no": "1",
      "student_answer": "the student wrote...",
      "correct_answer": "expected answer summary",
      "marks_awarded": 2,
      "marks_possible": 3,
      "correct": false,
      "needs_review": false,
      "feedback": "Covered 2 of 3 key concepts. Missing: Newton's third law."
    }}
  ]
}}"""


def get_descriptive_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade these Descriptive answers. Students wrote by hand — expect spelling mistakes, abbreviations, and informal phrasing.

ANSWER KEY AND RUBRIC:
{rubric}

STUDENT ANSWERS:
{student_answers}

Spelling and language rules (IMPORTANT):
- Ignore ALL spelling mistakes — grade on ideas, not spelling
- "machene lerning" still means "machine learning" — award concept credit
- Ignore capitalisation, punctuation, grammar issues
- Accept synonyms and paraphrases freely
- Accept abbreviations (ML, AI, NLP, etc.)
- DO NOT deduct marks for poor spelling or grammar
- Only flag needs_review: true if the meaning is truly unreadable

Grading dimensions for each answer:
1. Content accuracy (40% weight): Are the core facts/concepts correct?
2. Keyword coverage (30% weight): Are key ideas present (even if misspelled)?
3. Completeness (20% weight): Is the answer adequately detailed?
4. Clarity (10% weight): Can you understand what they mean?

Rules:
- Award marks on a sliding scale from 0 to marks_possible
- Be generous with spelling/language — a student who knows the concept but can't spell gets full concept credit
- Write feedback that mentions what was correct and what specific concept was missing

Return ONLY this JSON:
{{
  "question_scores": [
    {{
      "q_no": "1",
      "student_answer": "the student wrote...",
      "correct_answer": "rubric summary",
      "marks_awarded": 6,
      "marks_possible": 10,
      "correct": false,
      "needs_review": false,
      "feedback": "Good explanation of X. Missing Y and Z. Spelling errors present but concept is clear."
    }}
  ]
}}"""


def get_mixed_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade this mixed exam. Each question has its own type. Students wrote by hand — expect spelling mistakes and informal phrasing.

ANSWER KEY AND RUBRIC (includes type per question):
{rubric}

STUDENT ANSWERS:
{student_answers}

Global spelling rules (apply to ALL question types):
- Ignore spelling mistakes — grade on concepts and meaning
- Ignore capitalisation and punctuation
- Accept synonyms, paraphrases, and common abbreviations (ML, AI, NLP, etc.)
- DO NOT penalise for OCR artefacts or poor handwriting

Per-question type rules:
- MCQ: exact letter match only (a/b/c/d), full marks or 0
- FILL_IN_THE_BLANKS: accept alternatives, ignore spelling variations up to 3 character edits
- SHORT_ANSWER: keyword/concept coverage with proportional marks, spelling ignored
- DESCRIPTIVE: rubric-based sliding scale, grade on ideas not language quality

Return ONLY this JSON:
{{
  "question_scores": [
    {{
      "q_no": "1",
      "question_type": "MCQ",
      "student_answer": "b",
      "correct_answer": "b",
      "marks_awarded": 1,
      "marks_possible": 1,
      "correct": true,
      "needs_review": false,
      "feedback": "Correct"
    }}
  ]
}}"""
