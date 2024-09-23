# AI Cashier

AI Cashier is a Flask application that uses OpenAI's GPT-3 model to process voice orders from customers. It also provides a real-time order summary dashboard.

App deployed __[HERE](https://ai-cashier-sdp-8348acf0354e.herokuapp.com/)__

## Setup

1. Install the required Python packages:

```sh
pip install -r requirements.txt
```
2. Set your OpenAI API key in the `.env` file:

```sh
OPENAI_API_KEY="your-api-key"
```

3. Run the application

```sh
python app.py
```

## Usage
- Upload a menu file (PDF or image) via the "Upload Menu" section.
- Start speaking your order via the "Order via Voice" section.
- View the order summary in the "Order Summary" section.

## Files

- `app.py`: The main Flask application file.
- `models/dialogue_model.py`: Contains the DialogueModel class for processing voice orders with OpenAI API calls.
- `models/menu_processing.py`: Contains functions for processing menu files.
- `static/js/script.js`: Contains JavaScript functions for the front-end.
- `templates/index.html`: The main HTML template for the application.
