const statusIndicator = document.querySelector('.status-indicator');
const statusDot = document.querySelector('.status-dot');
const statusText = statusIndicator.querySelector('span');
const videoOverlay = document.querySelector('.video-overlay');
const video = document.getElementById('video');

let isConnected = false;
let isCameraActive = false;

function updateConnectionStatus(connected) {
    isConnected = connected;
}

function updateCameraStatus(active) {
    isCameraActive = active;
    videoOverlay.textContent = active ? 'Càmera activada' : 'Càmera desactivada';
    video.style.opacity = active ? 1 : 0.5; // Feedback visual adicional
}

async function initializeCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        updateCameraStatus(true);
        updateConnectionStatus(true);
        
        stream.getVideoTracks()[0].addEventListener('ended', () => {
            updateCameraStatus(false);
            updateConnectionStatus(false);
        });
    } catch (error) {
        updateCameraStatus(false);
        updateConnectionStatus(false);
        console.error('Error al acceder a la cámara:', error);
    }
}

initializeCamera();

setTimeout(() => {
    updateConnectionStatus(false);
}, 5000);
