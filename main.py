import fitz  # PyMuPDF
import base64
import json
import csv
import io
import time
import requests
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from dotenv import load_dotenv

load_dotenv()  # Load API keys from .env file

app = FastAPI()

# --- CONFIGURATION ---
API_KEY = os.getenv("API_KEY")
LLM_URL = os.getenv("LLM_URL")
MODEL = os.getenv("MODEL")

def pdf_to_base64_images(pdf_bytes):
    """Converts PDF pages to Base64 JPEGs. DPI kept at 144 for balance."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
        img_data = pix.tobytes("jpg")
        images.append(base64.b64encode(img_data).decode('utf-8'))
    return images

def call_llm(messages):
    """Handles the API request with a high timeout to prevent stopping."""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    try:
        # 10s connection timeout, 600s (10 min) read timeout
        response = requests.post(LLM_URL, headers=headers, json=payload, timeout=(10, 600))
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None

@app.post("/process-exams")
async def process_exams(
    answer_key: UploadFile = File(...),
    student_sheets: list[UploadFile] = File(...),
    total_marks: int = Form(...)
):
    # STAGE 1: Extract Rubric from Key
    key_bytes = await answer_key.read()
    key_doc = fitz.open(stream=key_bytes, filetype="pdf")
    key_text = "".join([page.get_text() for page in key_doc])

    classifier_prompt = [
        {"role": "system", "content": "Analyze key. Classify as 'MCQ' or 'Descriptive'. Extract question list. Output JSON: {'type': 'MCQ', 'questions': ['Q1','Q2']}"},
        {"role": "user", "content": key_text}
    ]
    rubric_raw = call_llm(classifier_prompt)
    if not rubric_raw:
        raise HTTPException(status_code=500, detail="Failed to process Answer Key.")

    all_student_data = []

    # STAGE 2: Evaluate Students Loop
    for sheet in student_sheets:
        sheet_bytes = await sheet.read()
        images_b64 = pdf_to_base64_images(sheet_bytes)
        
        user_content = [{"type": "text", "text": f"Rubric: {rubric_raw}. Max marks: {total_marks}"}]
        for img in images_b64:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})

        grader_prompt = [
            {"role": "system", "content": "You are an examiner. Grade the handwritten paper. Provide a 'Correct/Incorrect/Partial' status for EACH question ID found in the rubric. Output JSON: {'student_name': '', 'total_score': 0, 'results': {'Q1': 'Correct', 'Q2': 'Incorrect'}, 'needs_review': false}"},
            {"role": "user", "content": user_content}
        ]
        
        grade_raw = call_llm(grader_prompt)
        if not grade_raw: continue # Skip if this specific student fails
        
        grade_data = json.loads(grade_raw)
        
        # Build CSV Row
        row = {
            "Student Name": grade_data.get("student_name", sheet.filename),
            "Final Score": grade_data.get("total_score", 0),
            "Manual Review": "Yes" if grade_data.get("needs_review") else "No"
        }
        # Inject dynamic question columns
        row.update(grade_data.get("results", {}))
        all_student_data.append(row)
        
        # Anti-Rate Limit: Short pause between students
        time.sleep(1)

    # STAGE 3: Dynamic CSV Generation
    if not all_student_data:
        raise HTTPException(status_code=500, detail="No students were processed successfully.")

    output = io.StringIO()
    # Get all unique headers (Name, Score, Review + all Q IDs)
    keys = set()
    for d in all_student_data: keys.update(d.keys())
    
    # Sort headers so questions appear in order
    fixed_headers = ["Student Name", "Final Score", "Manual Review"]
    q_headers = sorted([k for k in keys if k not in fixed_headers], key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    writer = csv.DictWriter(output, fieldnames=fixed_headers + q_headers)
    writer.writeheader()
    writer.writerows(all_student_data)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )

@app.get("/", response_class=HTMLResponse)
async def main_page():
    # Explicitly adding encoding="utf-8" solves the UnicodeDecodeError
    with open("index.html", "r", encoding="utf-8") as f: 
        return f.read()

if __name__ == "__main__":
    import uvicorn
    # Important: Setting timeout-keep-alive high for long-running vision tasks
    uvicorn.run(app, host="127.0.0.1", port=8000, timeout_keep_alive=600)