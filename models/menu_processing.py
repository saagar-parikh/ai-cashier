from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv

load_dotenv()
# Define the output schema
response_schemas = [
    ResponseSchema(name="items", description="A list of dictionaries, each containing 'item', 'description', 'price', and 'allergens' for a menu item"),
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# Create a prompt template
prompt_template = PromptTemplate(
    template="""Extract menu information from the following raw text. Identify each menu item, its description, price, and allergens. Return the information as a list of dictionaries.

    {format_instructions}

    Raw menu text:
    {menu_text}

    Extracted menu information:""",
    input_variables=["menu_text"],
    partial_variables={"format_instructions": output_parser.get_format_instructions()}
)

# Initialize the language model
llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")

# Create the menu processing chain
menu_chain = LLMChain(llm=llm, prompt=prompt_template, output_parser=output_parser)

# Function to process the entire menu
def process_menu(menu_text):
    result = menu_chain.invoke(menu_text)
    menu_df = pd.DataFrame(result['text']['items'])
    menu_df.to_csv('menu.csv', index=False)
    return menu_df


def process_menu_text(file):
    if file.filename.endswith('.pdf'):
        menu_text = process_pdf(file)
    elif file.filename.endswith(('.png', '.jpg', '.jpeg')):
        menu_text = process_image(file)
    elif file.filename.endswith('.txt'):
        menu_text = process_text(file)
    else:
        return None, False
    return menu_text, True

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
    """Extract text from a .txt menu."""
    # Read the file directly without saving it
    text = file.read().decode('utf-8')
    return text