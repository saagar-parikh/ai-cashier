import PyPDF2
import pytesseract
from PIL import Image
import pandas as pd

def process_pdf(file):
    reader = PyPDF2.PdfReader(file)
    menu_data = []
    for page in reader.pages:
        text = page.extract_text()
        menu_data.extend(parse_menu_text(text))
    return pd.DataFrame(menu_data, columns=['Item', 'Description', 'Price'])

def process_image(file):
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    menu_data = parse_menu_text(text)
    return pd.DataFrame(menu_data, columns=['Item', 'Description', 'Price'])

def parse_menu_text(text):
    # Simple rule-based parsing of text
    lines = text.split('\n')
    menu_items = []
    for line in lines:
        if line:  # Assuming each line is an item followed by description and price
            parts = line.split()
            item = parts[0]
            price = parts[-1]
            description = ' '.join(parts[1:-1])
            menu_items.append([item, description, price])
    return menu_items
