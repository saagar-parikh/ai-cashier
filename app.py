from flask import Flask, render_template, request, jsonify, url_for
import os
import pandas as pd
from models.menu_processing import process_pdf, process_image, process_text
from models.dialogue_model import DialogueModel, OrderEntry
from gtts import gTTS
from dotenv import load_dotenv
import time
import re

app = Flask(__name__)
app.config['DEBUG'] = False

# Initialize dialogue model
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
dialogue_model = DialogueModel(api_key=api_key)

# Order summary dashboard 
orders_df = pd.DataFrame(columns=["customer_name", "items", "customizations", "price_per_item", "order_total"])


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-menu', methods=['POST'])
def upload_menu():
    file = request.files['menu']
    if file.filename.endswith('.pdf'):
        menu_text = process_pdf(file)
    elif file.filename.endswith(('.png', '.jpg', '.jpeg')):
        menu_text = process_image(file)
    elif file.filename.endswith('.txt'):
        menu_text = process_text(file)
    else:
        return "Unsupported file format", 400

    # Pass the extracted menu text to the dialogue model
    dialogue_model.set_menu_text(menu_text)
    
    return jsonify({"message": "Menu uploaded successfully!"})

def check_order_completion(user_input):
    completion_pattern = r"(for\s?here|dine\s?in|stay\s?here|to\s?go|to-go|take\s?away|take\s?out|carry\s?out|for-here|to-go)"
    
    return bool(re.search(completion_pattern, user_input, re.IGNORECASE))

@app.route('/voice-interaction', methods=['POST'])
def voice_interaction():
    user_input = request.json.get("user_input")
    if check_order_completion(user_input):
        place_order()
        response = "Order confirmed."
    else:
        response = dialogue_model.get_response(user_input)

    # Convert the response text to speech using gTTS
    tts = gTTS(response, lang="en", tld="us")
    audio_filename = 'response.mp3'
    audio_path = os.path.join('static', audio_filename)
    tts.save(audio_path)

    timestamp = int(time.time())
    audio_url = url_for('static', filename=audio_filename) + f'?t={timestamp}'
    
    return jsonify({"response": response, "audio_url": audio_url})

@app.route('/place-order', methods=['POST'])
def place_order():
    global orders_df
    order_response = dialogue_model.place_order()  # Call your order processing method    
    new_order_df = pd.DataFrame([{
        'customer_name': order_response.customer_name,
        'items': order_response.items,
        'customizations': order_response.customizations,
        'price_per_item': order_response.price_per_item,
        'order_total': order_response.order_total
    }])

    orders_df = pd.concat([orders_df, new_order_df], ignore_index=True)
    orders_df.to_csv('uploads/orders.csv', index=False)

    return jsonify({"message": "Order confirmed."})

@app.route('/order-summary', methods=['GET'])
def order_summary():
    try:
        orders_df = pd.read_csv('uploads/orders.csv')
        return orders_df.to_dict(orient='records')
    except FileNotFoundError:
        print("No orders found")
        return jsonify([])  # Return an empty list if no orders found

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
