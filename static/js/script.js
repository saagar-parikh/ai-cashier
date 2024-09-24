// Voice interaction setup
const voiceBtn = document.getElementById('voice-btn');
const stopVoiceBtn = document.getElementById('stop-voice-btn'); // New stop button
const completeOrderBtn = document.getElementById('complete-order-btn'); // Complete order button
const voiceOutput = document.getElementById('voice-output');
const menuForm = document.getElementById('menu-form');
const canvas = document.getElementById('audio-visualizer');
const canvasCtx = canvas.getContext('2d');
let audioContext, analyser, microphone, dataArray, bufferLength, animationFrameId;
let recognition; // Declare recognition outside to manage it globally
let lastOrderData = []; // Store last order data for comparison

// Handle menu upload
menuForm.addEventListener('submit', (event) => {
    event.preventDefault();  // Prevent the default form submission

    const formData = new FormData(menuForm);
    fetch('/upload-menu', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Display success message
        voiceOutput.textContent = data.message; // Show the success message on the page
    })
    .catch(err => {
        console.error(err);
        voiceOutput.textContent = "Error uploading menu."; // Show error message on the page
    });
});

// Start voice interaction
voiceBtn.addEventListener('click', () => {
    recognition = new webkitSpeechRecognition();

    recognition.onstart = () => {
        startAudioVisualizer();  // Start visualizer when the microphone starts
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        voiceOutput.textContent = "You said: " + transcript;

        // Stop the visualizer after the result is returned
        stopAudioVisualizer();

        // Send voice input to server
        fetch('/voice-interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_input: transcript })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            voiceOutput.textContent = data.response;
            playAudio(data.audio_url); // Play the audio response
            if (data.response.includes("Order confirmed")) {
                updateOrderSummary(); // Update summary if order is confirmed
            }
        })
        .catch(err => console.error(err));
    };

    recognition.start();
});

// Stop voice interaction
stopVoiceBtn.addEventListener('click', () => {
    if (recognition) {
        recognition.stop(); // Stop speech recognition
    }
    stopAudioVisualizer(); // Stop audio visualizer
});

// Complete order
completeOrderBtn.addEventListener('click', () => {
    fetch('/place-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}) // Include any necessary data for placing the order
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        voiceOutput.textContent = "Order completed: " + data.message; // Display confirmation message
        updateOrderSummary(); // Update order summary after placing an order
    })
    .catch(err => console.error(err));
});

// Reset order summary
document.getElementById('reset-order-btn').addEventListener('click', () => {
    fetch('/reset-order-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        const tbody = document.querySelector('#order-summary-table tbody');
        tbody.innerHTML = ''; // Clear all rows
        lastOrderData = []; // Reset lastOrderData to prevent unnecessary updates
        voiceOutput.textContent = data.message; // Feedback message from the server
    })
    .catch(err => console.error('Error resetting order summary:', err));
});



// Function to update the order summary table
function updateOrderSummary() {
    fetch('/order-summary', { method: 'GET' })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Fetched order data:', data); // Log fetched order data
        if (JSON.stringify(data) !== JSON.stringify(lastOrderData)) {
            lastOrderData = data;
            const tbody = document.querySelector('#order-summary-table tbody');
            tbody.innerHTML = '';

            data.forEach(order => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${order.customer_name}</td>
                    <td>${order.items}</td>
                    <td>${order.customizations}</td>
                    <td>${order.price_per_item}</td>
                    <td>${order.order_total}</td>
                `;
                tbody.appendChild(row);
            });
        }
    })
    .catch(err => console.error('Error updating order summary:', err));
}


// Function to play audio from URL
function playAudio(url) {
    const audio = new Audio(url);
    audio.play().catch(err => console.error('Audio playback error:', err));
}

// Function to start visualizing microphone input
async function startAudioVisualizer() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);

    analyser.fftSize = 2048;
    bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);

    drawVisualizer();
}

// Function to stop the visualizer
function stopAudioVisualizer() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
    if (microphone) {
        microphone.disconnect();
    }
    if (audioContext) {
        audioContext.close();
    }

    // Clear the canvas
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
}

// Function to draw the sound waves on the canvas
function drawVisualizer() {
    animationFrameId = requestAnimationFrame(drawVisualizer);
    
    analyser.getByteTimeDomainData(dataArray);

    // Clear the canvas before drawing
    canvasCtx.fillStyle = '#222';
    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = '#00ff00';
    
    canvasCtx.beginPath();
    const sliceWidth = canvas.width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0; // Normalize the byte data
        const y = v * canvas.height / 2;

        if (i === 0) {
            canvasCtx.moveTo(x, y);
        } else {
            canvasCtx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    canvasCtx.lineTo(canvas.width, canvas.height / 2);
    canvasCtx.stroke();
}

// Periodically check for updates every 5 seconds
// setInterval(updateOrderSummary, 5000);
