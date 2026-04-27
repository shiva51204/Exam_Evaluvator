import json
import time
from services.llm_client import call_llm_with_image, call_llm, parse_llm_json
from prompts.ocr_prompt import OCR_SYSTEM, get_ocr_prompt, get_ocr_multipage_prompt
from prompts.grader_prompts import (
    GRADER_SYSTEM,
    get_mcq_grader_prompt,
    get_fill_blank_grader_prompt,
    get_short_answer_grader_prompt,
    get_descriptive_grader_prompt,
    get_mixed_grader_prompt
)


def ocr_student_sheet(images_b64: list, total_questions: int, exam_type: str) -> dict | None:
    """
    Run OCR on student answer sheet images.
    Handles multi-page sheets by merging answers from all pages.
    """
    if len(images_b64) == 1:
        # Single page — standard OCR
        prompt = get_ocr_prompt(total_questions, exam_type)
        raw = call_llm_with_image(
            system_prompt=OCR_SYSTEM,
            user_text=prompt,
            images_b64=images_b64,
            max_tokens=3000
        )
        return parse_llm_json(raw)

    else:
        # Multi-page — OCR each page separately then merge
        all_answers = {}
        student_name = "UNKNOWN"

        for i, img in enumerate(images_b64):
            prompt = get_ocr_multipage_prompt(i + 1, len(images_b64), total_questions)
            raw = call_llm_with_image(
                system_prompt=OCR_SYSTEM,
                user_text=prompt,
                images_b64=[img],
                max_tokens=2000
            )
            page_result = parse_llm_json(raw)
            if not page_result:
                continue

            # Extract student name from first page that has it
            if student_name == "UNKNOWN" and page_result.get("student_name"):
                student_name = page_result["student_name"]

            # Merge answers — later pages overwrite earlier if same q_no
            for ans in page_result.get("answers", []):
                all_answers[ans["q_no"]] = ans

        if not all_answers:
            return None

        return {
            "student_name": student_name,
            "sheet_valid": True,
            "sheet_issues": "",
            "answers": list(all_answers.values())
        }


def grade_student(rubric: dict, ocr_result: dict) -> dict | None:
    """
    Grade a student's OCR result against the rubric.
    Picks the right grader based on exam type.
    """
    exam_type = rubric.get("exam_type", "MIXED")
    student_answers = ocr_result.get("answers", [])

    # Select prompt based on exam type
    if exam_type == "MCQ":
        prompt = get_mcq_grader_prompt(rubric, student_answers)
    elif exam_type == "FILL_IN_THE_BLANKS":
        prompt = get_fill_blank_grader_prompt(rubric, student_answers)
    elif exam_type == "SHORT_ANSWER":
        prompt = get_short_answer_grader_prompt(rubric, student_answers)
    elif exam_type == "DESCRIPTIVE":
        prompt = get_descriptive_grader_prompt(rubric, student_answers)
    else:
        # MIXED or unknown — use mixed grader
        prompt = get_mixed_grader_prompt(rubric, student_answers)

    messages = [
        {"role": "system", "content": GRADER_SYSTEM},
        {"role": "user", "content": prompt}
    ]

    raw = call_llm(messages, max_tokens=3000)
    return parse_llm_json(raw)


def compute_final_score(rubric: dict, grade_result: dict, ocr_result: dict) -> dict:
    """
    Compute total score, percentage, grade and flags from grading result.
    Returns the complete student result dict.
    """
    question_scores = grade_result.get("question_scores", [])
    total_score = sum(qs.get("marks_awarded", 0) for qs in question_scores)
    max_score = rubric.get("total_marks", sum(qs.get("marks_possible", 0) for qs in question_scores))
    percentage = (total_score / max_score * 100) if max_score > 0 else 0

    # Assign grade
    if percentage >= 90:
        grade = "A"
    elif percentage >= 75:
        grade = "B"
    elif percentage >= 60:
        grade = "C"
    elif percentage >= 45:
        grade = "D"
    else:
        grade = "F"

    # Check review flags
    needs_review = any(qs.get("needs_review") for qs in question_scores)
    if not ocr_result.get("sheet_valid", True):
        needs_review = True

    review_reasons = []
    if not ocr_result.get("sheet_valid", True):
        review_reasons.append("Sheet could not be read properly")
    flagged_qs = [
        f"Q{qs['q_no']}"
        for qs in question_scores
        if qs.get("needs_review")
    ]
    if flagged_qs:
        review_reasons.append(f"Unclear answers: {', '.join(flagged_qs)}")

    # Build question results
    question_results = []
    for qs in question_scores:
        # Find corresponding rubric question for type info
        rq = next((q for q in rubric.get("questions", []) if q["q_no"] == qs.get("q_no")), {})
        question_results.append({
            "q_no": qs.get("q_no", "?"),
            "question_type": qs.get("question_type", rq.get("type", rubric.get("exam_type", "UNKNOWN"))),
            "student_answer": qs.get("student_answer", ""),
            "correct_answer": qs.get("correct_answer", rq.get("correct_answer", "")),
            "marks_awarded": qs.get("marks_awarded", 0),
            "marks_possible": qs.get("marks_possible", rq.get("marks", 0)),
            "correct": qs.get("correct", False),
            "needs_review": qs.get("needs_review", False),
            "confidence": next(
                (a.get("confidence", 100) for a in ocr_result.get("answers", []) if a["q_no"] == qs.get("q_no")),
                100
            ),
            "feedback": qs.get("feedback", "")
        })

    return {
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": round(percentage, 2),
        "grade": grade,
        "needs_review": needs_review,
        "review_reason": "; ".join(review_reasons),
        "question_results": question_results
    }


def process_single_student(
    images_b64: list,
    filename: str,
    rubric: dict,
    student_index: int
) -> dict:
    """
    Full pipeline for one student: OCR → Grade → Score.
    Returns a complete student result dict.
    """
    start_time = time.time()
    total_questions = len(rubric.get("questions", []))
    exam_type = rubric.get("exam_type", "MIXED")

    # Step 1: OCR
    print(f"[Grader] Student {student_index}: Running OCR on {len(images_b64)} page(s)...")
    ocr_result = ocr_student_sheet(images_b64, total_questions, exam_type)

    if not ocr_result:
        elapsed = time.time() - start_time
        return {
            "student_name": f"Student_{student_index}",
            "filename": filename,
            "total_score": 0,
            "max_score": rubric.get("total_marks", 0),
            "percentage": 0,
            "grade": "F",
            "needs_review": True,
            "review_reason": "OCR failed — could not read answer sheet",
            "question_results": [],
            "processing_time_seconds": round(elapsed, 2),
            "ocr_success": False,
            "error": "OCR returned no result"
        }

    student_name = ocr_result.get("student_name", f"Student_{student_index}")
    if not student_name or student_name == "UNKNOWN":
        student_name = filename.replace(".pdf", "")

    print(f"[Grader] Student {student_index}: OCR complete. Name: {student_name}. Grading...")

    # Step 2: Grade
    grade_result = grade_student(rubric, ocr_result)

    if not grade_result:
        elapsed = time.time() - start_time
        return {
            "student_name": student_name,
            "filename": filename,
            "total_score": 0,
            "max_score": rubric.get("total_marks", 0),
            "percentage": 0,
            "grade": "F",
            "needs_review": True,
            "review_reason": "Grading failed — LLM could not produce a valid score",
            "question_results": [],
            "processing_time_seconds": round(elapsed, 2),
            "ocr_success": True,
            "error": "Grading returned no result"
        }

    # Step 3: Compute scores
    scores = compute_final_score(rubric, grade_result, ocr_result)
    elapsed = time.time() - start_time

    print(f"[Grader] Student {student_index}: Done. Score: {scores['total_score']}/{scores['max_score']} ({scores['percentage']:.1f}%)")

    return {
        "student_name": student_name,
        "filename": filename,
        "processing_time_seconds": round(elapsed, 2),
        "ocr_success": True,
        "error": None,
        **scores
    }
