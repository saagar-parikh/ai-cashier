from flask import Flask, render_template, request, jsonify, url_for
import os
import pandas as pd
from models.menu_processing import process_pdf, process_image
from models.dialogue_model import DialogueModel
from gtts import gTTS  # Import gTTS for text-to-speech

app = Flask(__name__)

# Initialize dialogue model (you can plug in GPT, Rasa, or a rule-based system)
dialogue_model = DialogueModel()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-menu', methods=['POST'])
def upload_menu():
    if request.method == 'POST':
        file = request.files['menu']
        if file.filename.endswith('.pdf'):
            menu = process_pdf(file)
        elif file.filename.endswith(('.png', '.jpg', '.jpeg')):
            menu = process_image(file)
        else:
            return "Unsupported file format", 400

        # Save the menu data for future use
        menu.to_csv('uploads/menu.csv')
        return jsonify({"message": "Menu uploaded successfully!", "menu": menu.to_dict()})

@app.route('/voice-interaction', methods=['POST'])
def voice_interaction():
    user_input = request.json.get("user_input")
    response = dialogue_model.get_response(user_input)

    # Convert the response text to speech using gTTS
    tts = gTTS(response)
    
    # Save the audio to a file in the static directory
    audio_filename = 'response.mp3'
    audio_path = os.path.join('static', audio_filename)
    tts.save(audio_path)
    
    # Return the response text and audio URL to the client
    audio_url = url_for('static', filename=audio_filename)
    return jsonify({"response": response, "audio_url": audio_url})


@app.route('/order-summary', methods=['GET'])
def order_summary():
    # Load order summary from a CSV or in-memory structure
    orders_df = pd.read_csv('uploads/orders.csv')
    return orders_df.to_dict(orient='records')

if __name__ == '__main__':
    app.run(debug=True)
