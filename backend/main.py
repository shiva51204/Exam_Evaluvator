from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import exam, health

app = FastAPI(
    title="Exam Corrector API",
    description="Automated handwritten exam grading using LLM + OCR",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(exam.router, prefix="/api", tags=["exam"])


@app.get("/")
async def root():
    return {"message": "Exam Corrector API is running", "docs": "/docs"}
