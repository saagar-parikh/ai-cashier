from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

def process_pdf(file):
    """Extract text from a PDF menu."""
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def process_image(file):
    """Extract text from an image menu using OCR."""
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    return text

def process_text(file):
    """Extract text from a .txt menu file."""
    with open(file, 'r', encoding='utf-8') as f:
        text = f.read()
    return text