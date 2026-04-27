import json
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
from typing import List, Dict, Any, Optional
import concurrent.futures

from utils.validators import validate_file, validate_total_marks, validate_student_count
from services.pdf_processor import extract_text, pdf_to_images
from services.classifier import classify_and_extract_rubric, classify_from_images
from services.grader import process_single_student
from utils.csv_builder import build_csv, build_flagged_csv

router = APIRouter()

# In-memory job store (use Redis for production)
jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/grade/stream")
async def grade_stream(
    answer_key: UploadFile = File(...),
    student_sheets: List[UploadFile] = File(...),
    total_marks: int = Form(...),
    exam_title: str = Form(default="Exam")
) -> StreamingResponse:
    """
    Main grading endpoint — streams SSE events as each student is processed.
    Supports both typed and handwritten/photo answer keys.
    """
    # Validate inputs
    validate_total_marks(total_marks)
    validate_student_count(len(student_sheets))

    key_bytes: bytes = await validate_file(answer_key, "Answer Key")
    student_data: List[tuple[str, bytes]] = []
    for sheet in student_sheets:
        b: bytes = await validate_file(sheet, f"Student: {sheet.filename}")
        student_data.append((sheet.filename, b))

    # Try text extraction first (typed PDFs)
    key_text: Optional[str] = extract_text(key_bytes)

    rubric: Optional[Dict[str, Any]] = None
    if key_text and len(key_text.strip()) >= 20:
        # Typed/digital PDF — use text-based classifier
        rubric = classify_and_extract_rubric(key_text, total_marks)
    else:
        # Handwritten or photo-based PDF — OCR the images first
        print("[API] No text found in answer key — falling back to image OCR classifier.")
        key_images: Optional[List[str]] = pdf_to_images(key_bytes, dpi=200)
        if not key_images:
            raise HTTPException(status_code=400, detail="Could not render answer key PDF to images.")
        rubric = classify_from_images(key_images, total_marks)

    if not rubric:
        raise HTTPException(status_code=422, detail="Could not parse rubric from answer key. Ensure the answer key clearly lists question numbers and answers.")

    total_students: int = len(student_data)

    async def event_generator():
        results: List[Dict[str, Any]] = []

        # Emit rubric info first
        yield f"data: {json.dumps({'event': 'rubric', 'rubric': rubric, 'total_students': total_students})}\n\n"
        await asyncio.sleep(0)

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        for idx, (filename, pdf_bytes) in enumerate(student_data, start=1):
            # Emit start event
            yield f"data: {json.dumps({'event': 'start', 'student_index': idx, 'total_students': total_students, 'student_name': filename, 'message': f'Processing {filename}...'})}\n\n"
            await asyncio.sleep(0)

            try:
                images_b64: List[str] = await loop.run_in_executor(
                    executor, pdf_to_images, pdf_bytes, 200
                )

                result: Dict[str, Any] = await loop.run_in_executor(
                    executor,
                    process_single_student,
                    images_b64,
                    filename,
                    rubric,
                    idx
                )
                results.append(result)

                message: str = f"Graded: {result.get('total_score', 0)}/{result.get('max_score', 0)} ({result.get('percentage', 0):.1f}%)"
                yield f"data: {json.dumps({'event': 'progress', 'student_index': idx, 'total_students': total_students, 'student_name': result.get('student_name', filename), 'message': message, 'result': result})}\n\n"

            except Exception as e:
                err_result: Dict[str, Any] = {
                    "student_name": filename,
                    "filename": filename,
                    "total_score": 0,
                    "max_score": total_marks,
                    "percentage": 0,
                    "grade": "F",
                    "needs_review": True,
                    "review_reason": f"Processing error: {str(e)}",
                    "question_results": [],
                    "processing_time_seconds": 0,
                    "ocr_success": False,
                    "error": str(e)
                }
                results.append(err_result)
                yield f"data: {json.dumps({'event': 'error', 'student_index': idx, 'total_students': total_students, 'student_name': filename, 'message': f'Error: {str(e)}', 'result': err_result})}\n\n"

            await asyncio.sleep(0)

        # Build summary
        valid: List[Dict[str, Any]] = [r for r in results if r.get("ocr_success")]
        summary: Dict[str, Any] = {
            "total_students": total_students,
            "processed": len(valid),
            "failed": total_students - len(valid),
            "flagged": sum(1 for r in results if r.get("needs_review")),
            "class_average": round(sum(r["percentage"] for r in valid) / len(valid), 1) if valid else 0,
            "highest": round(max((r["percentage"] for r in valid), default=0), 1),
            "lowest": round(min((r["percentage"] for r in valid), default=0), 1),
            "exam_title": exam_title,
            "exam_type": rubric.get("exam_type", "MIXED"),
        }

        # Store results for CSV download
        job_id: str = f"{exam_title}_{total_students}"
        jobs[job_id] = {"results": results, "exam_title": exam_title, "rubric": rubric}

        yield f"data: {json.dumps({'event': 'done', 'summary': summary, 'job_id': job_id, 'results': results})}\n\n"
        executor.shutdown(wait=False)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/download/csv/{job_id}")
async def download_csv(job_id: str) -> Response:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found. Results may have expired.")

    job: Dict[str, Any] = jobs[job_id]
    csv_bytes: bytes = build_csv(job["results"], job["exam_title"])

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job["exam_title"]}_results.csv"'}
    )


@router.get("/download/flagged/{job_id}")
async def download_flagged_csv(job_id: str) -> Response:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job: Dict[str, Any] = jobs[job_id]
    csv_bytes: Optional[bytes] = build_flagged_csv(job["results"])

    if not csv_bytes:
        raise HTTPException(status_code=404, detail="No flagged students found.")

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job["exam_title"]}_flagged.csv"'}
    )