import os
from pdf2image import convert_from_path
from PIL import Image, ImageFilter
import PyPDF2
from docx import Document
from dotenv import load_dotenv
import pytesseract
from PyPDF2 import PdfReader

load_dotenv()


def identify_file_type(file_path):
    """
    Identify the file type based on the file extension.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in [".doc", ".docx"]:
        return "word"
    else:
        return "unknown"


def is_scanned_pdf(file_path):
    """
    Heuristically determine if a PDF is scanned by trying to extract text.
    If the first page yields no text, assume it is scanned.
    """
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if reader.pages:
                first_page = reader.pages[0]
                text = first_page.extract_text() or ""
                return len(text.strip()) == 0
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return False


def convert_pdf_to_images(file_path, dpi=300):
    """
    Convert PDF pages to images using pdf2image.
    Optionally uses the POPPLER_PATH environment variable if set.
    """
    poppler_path = os.getenv("POPPLER_PATH")
    if not poppler_path:
        print(
            "Warning: POPPLER_PATH is not set. Ensure poppler is installed and in your PATH, or set POPPLER_PATH."
        )
    try:
        images = convert_from_path(file_path, dpi=dpi, poppler_path=poppler_path)
        return images
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []


def preprocess_image(image):
    """
    Preprocess an image: convert to grayscale and apply a median filter to reduce noise.
    """
    gray_image = image.convert("L")
    cleaned_image = gray_image.filter(ImageFilter.MedianFilter(size=3))
    return cleaned_image


def extract_text_from_word(file_path):
    """
    Extract text from a Word document.
    """
    try:
        doc = Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error reading Word document: {e}")
        return ""


def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def perform_ocr_on_image(image):
    """
    Perform OCR on a preprocessed image using pytesseract.
    """
    text = pytesseract.image_to_string(image)
    return text


def perform_ocr_on_images(images):
    """
    Perform OCR on a list of images.
    Returns a list of text strings, one for each image.
    """
    ocr_results = []
    for idx, image in enumerate(images):
        text = perform_ocr_on_image(image)
        ocr_results.append(text)
        print(f"OCR on page {idx+1} completed.")
    return ocr_results
