from cartesia import Cartesia
from pydub import AudioSegment
import io
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()
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