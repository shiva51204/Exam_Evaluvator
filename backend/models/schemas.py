from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ExamType(str, Enum):
    MCQ = "MCQ"
    DESCRIPTIVE = "DESCRIPTIVE"
    FILL_IN_THE_BLANKS = "FILL_IN_THE_BLANKS"
    SHORT_ANSWER = "SHORT_ANSWER"
    MIXED = "MIXED"


class QuestionResult(BaseModel):
    q_no: str
    question_type: str
    student_answer: str
    correct_answer: str
    marks_awarded: float
    marks_possible: float
    correct: bool
    needs_review: bool
    confidence: int  # 0-100
    feedback: str


class StudentResult(BaseModel):
    student_name: str
    filename: str
    total_score: float
    max_score: float
    percentage: float
    grade: str
    needs_review: bool
    review_reason: str
    question_results: list[QuestionResult]
    processing_time_seconds: float
    ocr_success: bool
    error: Optional[str] = None


class ProcessingUpdate(BaseModel):
    event: str          # "start" | "progress" | "done" | "error"
    student_index: int
    total_students: int
    student_name: str
    message: str
    result: Optional[dict] = None
