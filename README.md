# ExamGrade — Automated Handwritten Exam Evaluator

AI-powered grading of handwritten exam answer sheets using LLM OCR + Grader pipeline.

## Architecture

```
Frontend (HTML/CSS/JS)  ←→  FastAPI Backend  ←→  Groq LLM (Llama 4)
                                  ↕
                           PDF → Images → OCR → Grade → CSV
```

## Setup

### 1. Backend

```bash
cd backend
cp .env.example .env
# Edit .env — add your GROQ API key

pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend

Open `frontend/index.html` in a browser, or serve with any static server:

```bash
cd frontend
python -m http.server 3000
# Then visit http://localhost:3000
```

### 3. Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Groq API key | required |
| `LLM_URL` | LLM endpoint URL | Groq OpenAI-compatible URL |
| `MODEL` | Model name | `meta-llama/llama-4-scout-17b-16e-instruct` |

## Workflow

1. **Upload** answer key PDF (typed/printed) + student answer sheet PDFs (handwritten)
2. **Classify** — LLM reads the answer key and extracts a structured rubric (MCQ / Fill-in / Short Answer / Descriptive / Mixed)
3. **OCR** — Each student sheet is converted to images and read by the LLM
4. **Grade** — Student answers are compared against the rubric per question type
5. **Results** — Live streaming dashboard shows scores, grades, and flags
6. **Export** — Download full CSV or flagged-students-only CSV

## Supported Exam Types

| Type | Description |
|------|-------------|
| MCQ | Multiple choice — exact letter match |
| Fill in the Blanks | Accepts alternatives and minor spelling variations |
| Short Answer | Keyword coverage scoring |
| Descriptive | Rubric-based sliding scale with detailed feedback |
| Mixed | Automatic per-question type detection |

## File Limits

- Answer key: 1 PDF, max 20MB, max 50 pages
- Student sheets: up to 100 PDFs per batch, max 20MB each
- Multi-page sheets are supported and merged automatically

## Project Structure

```
exam-corrector/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/
│   │   ├── exam.py              # /grade/stream, /download/* endpoints
│   │   └── health.py            # /health endpoint
│   ├── services/
│   │   ├── pdf_processor.py     # PDF → text / images
│   │   ├── llm_client.py        # LLM API calls with retry
│   │   ├── grader.py            # OCR + grading pipeline
│   │   └── classifier.py        # Answer key rubric extraction
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── utils/
│   │   ├── validators.py        # File/input validation
│   │   └── csv_builder.py       # CSV export
│   ├── prompts/
│   │   ├── ocr_prompt.py
│   │   ├── classifier_prompt.py
│   │   └── grader_prompts.py
│   └── .env
├── frontend/
│   ├── index.html               # Upload page
│   ├── results.html             # Results dashboard
│   ├── css/style.css
│   └── js/
│       ├── upload.js            # File handling & form submit
│       ├── progress.js          # SSE stream + live progress
│       └── results.js           # Results filtering/sorting/drawer
└── requirements.txt
```

## Notes

- Results are stored in memory per server session. For production, use Redis or a database.
- The grading pipeline is sequential per student. For faster processing on large batches, consider async workers.
- Low-confidence OCR answers (< 80%) are automatically flagged for manual review.
