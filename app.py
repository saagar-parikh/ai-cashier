from flask import Flask, render_template, request, jsonify, url_for
import os
import pandas as pd
from models.menu_processing import process_pdf, process_image, process_text
from models.dialogue_model import DialogueModel, OrderEntry
from cartesia import Cartesia
from pydub import AudioSegment
import io
import numpy as np
from dotenv import load_dotenv
import time
import re

os.makedirs('uploads', exist_ok=True)

app = Flask(__name__)
app.config['DEBUG'] = False
load_dotenv()

# Initialize dialogue model
dialogue_model = DialogueModel(api_key=os.getenv("OPENAI_API_KEY"))

# Order summary dashboard 
orders_df = pd.DataFrame(columns=["customer_name", "items", "customizations", "price_per_item", "order_total"])

# Cartesia setup
cartesia_client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))
voice_name = "Sarah"
voice_id = "694f9389-aac1-45b6-b726-9d9369183238"
voice = cartesia_client.voices.get(id=voice_id)
model_id = "sonic-english"
output_format = {
    "container": "raw",
    "encoding": "pcm_f32le",  # 32-bit floating-point PCM
    "sample_rate": 44100,
}

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

def text_to_speech(text):
    audio_buffer = io.BytesIO()

    # Generate and stream audio
    for output in cartesia_client.tts.sse(
        model_id=model_id,
        transcript=text,
        voice_embedding=voice["embedding"],
        stream=True,
        output_format=output_format,
    ):
        buffer = output["audio"]
        audio_buffer.write(buffer)

    audio_buffer.seek(0)

    # Read raw PCM data from buffer (32-bit float)
    raw_audio_data = np.frombuffer(audio_buffer.read(), dtype=np.float32)

    # Convert 32-bit float PCM to 16-bit integer PCM
    int_audio_data = np.int16(raw_audio_data * 32767)  # Scale float32 to int16 range

    # Create a new BytesIO buffer to store the 16-bit PCM data
    pcm_16bit_buffer = io.BytesIO()
    pcm_16bit_buffer.write(int_audio_data.tobytes())
    pcm_16bit_buffer.seek(0)

    # Convert the 16-bit PCM data to a pydub AudioSegment
    audio_segment = AudioSegment.from_raw(
        pcm_16bit_buffer,
        frame_rate=44100,
        sample_width=2,  # 16-bit PCM (2 bytes per sample)
        channels=1,      # Mono
    )

    # Define the output MP3 path
    audio_filename = 'response.mp3'
    audio_path = os.path.join('static', audio_filename)

    # Export to MP3 format
    audio_segment.export(audio_path, format="mp3")

    return audio_filename

@app.route('/voice-interaction', methods=['POST'])
def voice_interaction():
    user_input = request.json.get("user_input")
    if check_order_completion(user_input):
        place_order()
        response = "Order confirmed."
    else:
        response = dialogue_model.get_response(user_input)

    # Convert the response text to speech using gTTS
    audio_filename = text_to_speech(response)

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
        global orders_df
        # orders_df = pd.read_csv('uploads/orders.csv')
        return orders_df.to_dict(orient='records')
    except FileNotFoundError:
        print("No orders found")
        return jsonify([])  # Return an empty list if no orders found
    
@app.route('/reset-order-summary', methods=['POST'])
def reset_order_summary():
    global orders_df
    orders_df = pd.DataFrame(columns=["customer_name", "items", "customizations", "price_per_item", "order_total"])
    return jsonify({"message": "Order summary has been reset."}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
