import csv
import io
from datetime import datetime


def build_csv(results: list, exam_title: str = "Exam") -> bytes:
    """Build a CSV file from grading results."""

    if not results:
        return b""

    output = io.StringIO()

    # Determine all question numbers present
    all_q_nos = []
    seen = set()
    for r in results:
        for qr in r.get("question_results", []):
            q = qr["q_no"]
            if q not in seen:
                seen.add(q)
                all_q_nos.append(q)

    # Sort question numbers numerically where possible
    def sort_key(q):
        try:
            return (0, int(q))
        except ValueError:
            return (1, q)

    all_q_nos.sort(key=sort_key)

    # Fixed headers
    fixed = [
        "Student Name",
        "Filename",
        "Total Score",
        "Max Score",
        "Percentage",
        "Grade",
        "Needs Review",
        "Review Reason",
        "Processing Time (s)",
        "OCR Success"
    ]

    # Per-question headers: "Q1 (1m)" etc
    q_score_headers = []
    q_feedback_headers = []
    for q in all_q_nos:
        # Find marks_possible for this question from first result that has it
        marks = ""
        for r in results:
            for qr in r.get("question_results", []):
                if qr["q_no"] == q:
                    marks = qr.get("marks_possible", "")
                    break
            if marks != "":
                break
        q_score_headers.append(f"Q{q} Score ({marks}m)")
        q_feedback_headers.append(f"Q{q} Feedback")

    all_headers = fixed + q_score_headers + q_feedback_headers

    writer = csv.DictWriter(output, fieldnames=all_headers, extrasaction="ignore")

    # Write exam info header
    output.write(f"# {exam_title} Results\n")
    output.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write(f"# Total Students: {len(results)}\n")

    # Calculate summary stats
    valid = [r for r in results if r.get("ocr_success")]
    if valid:
        scores = [r["percentage"] for r in valid]
        avg = sum(scores) / len(scores)
        output.write(f"# Class Average: {avg:.1f}%\n")
        output.write(f"# Highest: {max(scores):.1f}%\n")
        output.write(f"# Lowest: {min(scores):.1f}%\n")
        flagged = sum(1 for r in results if r.get("needs_review"))
        output.write(f"# Flagged for Review: {flagged}\n")

    output.write("\n")
    writer.writeheader()

    for r in results:
        row = {
            "Student Name": r.get("student_name", ""),
            "Filename": r.get("filename", ""),
            "Total Score": r.get("total_score", ""),
            "Max Score": r.get("max_score", ""),
            "Percentage": f"{r.get('percentage', 0):.1f}%" if r.get("ocr_success") else "N/A",
            "Grade": r.get("grade", "N/A"),
            "Needs Review": "YES" if r.get("needs_review") else "NO",
            "Review Reason": r.get("review_reason", ""),
            "Processing Time (s)": f"{r.get('processing_time_seconds', 0):.1f}",
            "OCR Success": "YES" if r.get("ocr_success") else "NO"
        }

        # Build quick lookup for question results
        q_lookup = {qr["q_no"]: qr for qr in r.get("question_results", [])}

        for q in all_q_nos:
            qr = q_lookup.get(q, {})
            row[f"Q{q} Score ({qr.get('marks_possible', '')}m)"] = qr.get("marks_awarded", "")
            row[f"Q{q} Feedback"] = qr.get("feedback", "")

        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def build_flagged_csv(results: list) -> bytes:
    """Build a separate CSV for only flagged students."""
    flagged = [r for r in results if r.get("needs_review")]
    if not flagged:
        return b""

    output = io.StringIO()
    output.write("# Flagged Students - Require Manual Review\n\n")

    headers = ["Student Name", "Filename", "Total Score", "Max Score", "Percentage", "Review Reason", "Flagged Questions"]
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    for r in flagged:
        flagged_qs = [
            f"Q{qr['q_no']}"
            for qr in r.get("question_results", [])
            if qr.get("needs_review")
        ]
        writer.writerow({
            "Student Name": r.get("student_name", ""),
            "Filename": r.get("filename", ""),
            "Total Score": r.get("total_score", ""),
            "Max Score": r.get("max_score", ""),
            "Percentage": f"{r.get('percentage', 0):.1f}%",
            "Review Reason": r.get("review_reason", ""),
            "Flagged Questions": ", ".join(flagged_qs)
        })

    return output.getvalue().encode("utf-8")
