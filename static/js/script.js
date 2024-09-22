// Voice interaction setup
const voiceBtn = document.getElementById('voice-btn');
const voiceOutput = document.getElementById('voice-output');

voiceBtn.addEventListener('click', () => {
    // Implement Web Speech API for microphone input (simplified)
    const recognition = new webkitSpeechRecognition();
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        voiceOutput.textContent = "You said: " + transcript;

        // Send voice input to server
        fetch('/voice-interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_input: transcript })
        })
        .then(response => response.json())
        .then(data => {
            voiceOutput.textContent = data.response;
            playAudio(data.audio_url); // Play the audio response
        })
        .catch(err => console.error(err));
    };

    recognition.start();
});

// Function to play audio from URL
function playAudio(url) {
    const audio = new Audio(url);
    audio.play().catch(err => console.error('Audio playback error:', err));
}
