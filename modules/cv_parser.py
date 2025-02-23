import sys
import os

# Add the project root directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import os
import shutil
import sqlite3
import uuid
import json
from pathlib import Path

# Import functions from document_processor
from modules.document_processor import (
    identify_file_type,
    is_scanned_pdf,
    convert_pdf_to_images,
    preprocess_image,
    perform_ocr_on_images,
    extract_text_from_word,
    extract_text_from_pdf,
)

# Import LLM helper functions from llm_integration
from modules.llm_integration import construct_cv_prompt, retry_llm_response

# Define directories and database path
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / ".." / "data" / "sample_cvs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / ".." / "cv_data.db"


def save_uploaded_cv(file_obj, filename):
    """
    Save the uploaded CV file (PDF or Word) into data/sample_cvs,
    generating a unique filename.
    """
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    save_path = UPLOAD_DIR / unique_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)
    print(f"File saved to {save_path}")
    return str(save_path)


def extract_raw_text(file_path):
    """
    Extract raw text from a CV file.
    For PDFs, if the file is scanned (i.e. no extractable text),
    convert pages to images and perform OCR.
    For Word documents, extract text directly.
    """
    file_type = identify_file_type(file_path)
    if file_type == "pdf":
        if is_scanned_pdf(file_path):
            images = convert_pdf_to_images(file_path)
            if images:
                preprocessed_images = [preprocess_image(img) for img in images]
                ocr_texts = perform_ocr_on_images(preprocessed_images)
                return "\n".join(ocr_texts)
            else:
                return ""
        else:
            return extract_text_from_pdf(file_path)
    elif file_type == "word":
        return extract_text_from_word(file_path)
    else:
        raise ValueError("Unsupported file type.")


def init_db():
    """Initialize the SQLite database and create the cv_records table.
    For testing purposes, we drop the table if it exists so that the schema is fresh.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Drop table if it exists (for testing only)
    cursor.execute("DROP TABLE IF EXISTS cv_records")
    # Create the table with the expected columns.
    cursor.execute(
        """
        CREATE TABLE cv_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            personal_information TEXT,
            education_history TEXT,
            work_experience TEXT,
            skills TEXT,
            projects TEXT,
            certifications TEXT,
            raw_text TEXT
        )
    """
    )
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def save_cv_data(cv_data):
    """Save the extracted structured CV data into the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cv_records (
                file_path,
                personal_information,
                education_history,
                work_experience,
                skills,
                projects,
                certifications,
                raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cv_data.get("file_path"),
                cv_data.get("personal_information"),
                cv_data.get("education_history"),
                cv_data.get("work_experience"),
                cv_data.get("skills"),
                cv_data.get("projects"),
                cv_data.get("certifications"),
                cv_data.get("raw_text"),
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        print(f"CV record saved with id: {row_id}")
    except Exception as e:
        print("Error saving CV data:", e)
    finally:
        conn.close()


def get_all_cv_data():
    """Retrieve all CV records from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cv_records")
    rows = cursor.fetchall()
    conn.close()
    keys = [
        "id",
        "file_path",
        "personal_information",
        "education_history",
        "work_experience",
        "skills",
        "projects",
        "certifications",
        "raw_text",
    ]
    records = [dict(zip(keys, row)) for row in rows]
    return records


def process_and_save_cv(file_obj, filename):
    """
    Process an uploaded CV file by:
      1. Saving the file.
      2. Extracting raw text from the file.
      3. Building an LLM prompt using construct_cv_prompt.
      4. Calling the LLM (via retry_llm_response) to obtain structured CV data.
      5. Mapping the LLM output into our desired structure and saving it in the database.

    Returns the structured CV data as a dict.
    """
    # Step 1: Save the file
    saved_path = save_uploaded_cv(file_obj, filename)
    # Step 2: Extract raw text
    raw_text = extract_raw_text(saved_path)
    # Step 3: Build a prompt for the LLM
    prompt = construct_cv_prompt(raw_text)
    print("LLM Prompt constructed")
    # Step 4: Call the LLM to get structured data (with retry logic)
    structured_data = retry_llm_response(prompt)
    if not structured_data:
        raise Exception("LLM failed to return structured data after multiple attempts.")

    # Step 5: Map LLM response to our desired structure.
    name = structured_data.get("Name", "not mentioned")
    contact_info = structured_data.get("Contact Information", "not mentioned")
    if isinstance(contact_info, dict):
        contact_info = ", ".join([f"{k}: {v}" for k, v in contact_info.items()])
    prof_summary = structured_data.get("Professional Summary", "not mentioned")
    personal_info = f"{name}. {contact_info}. {prof_summary}"

    education_history = structured_data.get("Education", "not mentioned")
    if not isinstance(education_history, str):
        education_history = json.dumps(education_history)

    work_experience = structured_data.get("Experience", "not mentioned")
    if not isinstance(work_experience, str):
        work_experience = json.dumps(work_experience)

    skills = structured_data.get("Skills", "not mentioned")
    if not isinstance(skills, str):
        skills = json.dumps(skills)

    certifications = structured_data.get("Certifications", "not mentioned")
    if not isinstance(certifications, str):
        certifications = json.dumps(certifications)

    projects = structured_data.get("Projects", "not mentioned")
    if not isinstance(projects, str):
        projects = json.dumps(projects)

    cv_data = {
        "file_path": saved_path,
        "personal_information": personal_info,
        "education_history": education_history,
        "work_experience": work_experience,
        "skills": skills,
        "projects": projects,
        "certifications": certifications,
        "raw_text": raw_text,
    }

    # Step 6: Save the structured data in the database
    save_cv_data(cv_data)
    return cv_data
