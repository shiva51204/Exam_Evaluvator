GRADER_SYSTEM = """You are a strict but fair exam grader. You grade based on the rubric provided.
Return ONLY valid JSON. No markdown. No explanation."""


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
- Ignore case and minor spelling variations (1-2 character difference)
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
    return f"""Grade these Short Answer responses.

ANSWER KEY AND RUBRIC:
{rubric}

STUDENT ANSWERS:
{student_answers}

Rules:
- Check if the student answer covers the key concepts (keywords list)
- Award marks proportionally based on keyword coverage
- Full marks: all keywords present + conceptually accurate
- Partial marks: some keywords present
- 0 marks: completely wrong or blank
- If unclear: needs_review: true

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
    return f"""Grade these Descriptive answers using the rubric.

ANSWER KEY AND RUBRIC:
{rubric}

STUDENT ANSWERS:
{student_answers}

Grading dimensions for each answer:
1. Content accuracy (40% weight): Are the facts correct?
2. Keyword coverage (30% weight): Are key concepts mentioned?
3. Completeness (20% weight): Is the answer adequately detailed?
4. Clarity (10% weight): Is the argument clear and structured?

Rules:
- Award marks on a sliding scale from 0 to marks_possible
- Be consistent — same quality answer always gets same marks
- If unclear handwriting: needs_review: true
- Write specific feedback mentioning what was good and what was missing

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
      "feedback": "Good explanation of X. Missing Y and Z. Argument lacks structure."
    }}
  ]
}}"""


def get_mixed_grader_prompt(rubric: dict, student_answers: list) -> str:
    return f"""Grade this mixed exam. Each question has its own type.

ANSWER KEY AND RUBRIC (includes type per question):
{rubric}

STUDENT ANSWERS:
{student_answers}

Per-question rules:
- MCQ: exact match only, full marks or 0
- FILL_IN_THE_BLANKS: accept alternatives, minor spelling ok
- SHORT_ANSWER: keyword coverage, proportional marks
- DESCRIPTIVE: rubric-based sliding scale, specific feedback

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
