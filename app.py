from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import hashlib
from werkzeug.utils import secure_filename
import base64
from datetime import datetime
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload
socketio = SocketIO(app)

# Ensure upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/audio', exist_ok=True)

# Store online users and their status
online_users = {}
user_status = {}  # 'online', 'offline', 'typing'

# HTML Templates
CALL_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chamada com {{ contact }} - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #0f1419;
            color: #fff;
            line-height: 1.6;
            height: 100vh;
        }
        
        .call-container {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        
        .call-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background-color: rgba(0, 0, 0, 0.4);
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            z-index: 10;
        }
        
        .call-info {
            display: flex;
            align-items: center;
        }
        
        .call-type {
            margin-right: 10px;
            font-size: 18px;
        }
        
        .call-duration {
            font-size: 16px;
            color: #ccc;
        }
        
        .call-back-button a {
            color: #fff;
            font-size: 24px;
            text-decoration: none;
        }
        
        .video-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
            background-color: #0f1419;
        }
        
        .remote-video-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
        }
        
        #remote-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .local-video-container {
            position: absolute;
            bottom: 100px;
            right: 20px;
            width: 150px;
            height: 200px;
            border-radius: 8px;
            overflow: hidden;
            z-index: 5;
            border: 2px solid #fff;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }
        
        #local-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transform: scaleX(-1); /* Mirror effect */
        }
        
        .audio-only-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: relative;
            z-index: 2;
        }
        
        .contact-profile {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .contact-pic {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            overflow: hidden;
            margin-bottom: 20px;
            border: 3px solid #128C7E;
        }
        
        .contact-pic img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .contact-name {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .audio-wave {
            width: 200px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .audio-bar {
            width: 6px;
            height: 20px;
            background-color: #128C7E;
            margin: 0 3px;
            border-radius: 3px;
            animation: audio-wave 1.2s infinite ease-in-out;
        }
        
        .audio-bar:nth-child(2) {
            animation-delay: 0.1s;
            height: 30px;
        }
        
        .audio-bar:nth-child(3) {
            animation-delay: 0.2s;
            height: 40px;
        }
        
        .audio-bar:nth-child(4) {
            animation-delay: 0.3s;
            height: 50px;
        }
        
        .audio-bar:nth-child(5) {
            animation-delay: 0.4s;
            height: 40px;
        }
        
        .audio-bar:nth-child(6) {
            animation-delay: 0.5s;
            height: 30px;
        }
        
        .audio-bar:nth-child(7) {
            animation-delay: 0.6s;
            height: 20px;
        }
        
        @keyframes audio-wave {
            0%, 100% {
                transform: scaleY(0.5);
            }
            50% {
                transform: scaleY(1);
            }
        }
        
        .call-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background-color: rgba(0, 0, 0, 0.5);
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 10;
        }
        
        .call-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: none;
            margin: 0 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .call-btn:hover {
            transform: scale(1.1);
        }
        
        .mute-btn {
            background-color: #555;
            color: #fff;
        }
        
        .mute-btn.active {
            background-color: #f39c12;
        }
        
        .video-btn {
            background-color: #555;
            color: #fff;
        }
        
        .video-btn.active {
            background-color: #f39c12;
        }
        
        .flip-btn {
            background-color: #555;
            color: #fff;
        }
        
        .end-call-btn {
            background-color: #e74c3c;
            color: #fff;
        }
        
        .connecting-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 20;
        }
        
        .connecting-text {
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        .connecting-spinner {
            width: 60px;
            height: 60px;
            border: 5px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #128C7E;
            animation: spin 1s infinite linear;
        }
        
        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }
        
        .hidden {
            display: none;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div class="call-container">
        <div class="call-header">
            <div class="call-info">
                <div class="call-type">{{ call_type|capitalize }} Call</div>
                <div class="call-duration" id="call-duration">00:00</div>
            </div>
            <div class="call-back-button">
                <a href="{{ url_for('contacts') }}" id="back-button">&times;</a>
            </div>
        </div>
        
        <div class="video-container" id="video-container">
            <div class="remote-video-container">
                <video id="remote-video" autoplay playsinline></video>
            </div>
            <div class="local-video-container">
                <video id="local-video" autoplay playsinline muted></video>
            </div>
        </div>
        
        <div class="audio-only-container hidden" id="audio-container">
            <div class="contact-profile">
                <div class="contact-pic">
                    <img src="/static/profile_pics/{{ contact_pic }}" alt="{{ contact }}">
                </div>
                <div class="contact-name">{{ contact }}</div>
            </div>
            <div class="audio-wave">
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
                <div class="audio-bar"></div>
            </div>
        </div>
        
        <div class="call-controls">
            <button class="call-btn mute-btn" id="mute-btn" title="Mute/Unmute">🎤</button>
            <button class="call-btn video-btn {{ 'hidden' if call_type == 'audio' }}" id="video-btn" title="Video On/Off">📹</button>
            <button class="call-btn flip-btn {{ 'hidden' if call_type == 'audio' }}" id="flip-btn" title="Flip Camera">🔄</button>
            <button class="call-btn end-call-btn" id="end-call-btn" title="End Call">📵</button>
        </div>
        
        <div class="connecting-overlay" id="connecting-overlay">
            <div class="connecting-text">Connecting...</div>
            <div class="connecting-spinner"></div>
        </div>
    </div>

    <script>
        // Variables
        const socket = io();
        const username = "{{ username }}";
        const contact = "{{ contact }}";
        const callType = "{{ call_type }}";
        const isInitiator = {{ 'true' if is_initiator else 'false' }};
        
        let localStream = null;
        let remoteStream = null;
        let peerConnection = null;
        let callStartTime = null;
        let callDurationInterval = null;
        let videoEnabled = callType === 'video';
        let audioEnabled = true;
        let isFrontCamera = true;
        
        // DOM Elements
        const localVideo = document.getElementById('local-video');
        const remoteVideo = document.getElementById('remote-video');
        const videoContainer = document.getElementById('video-container');
        const audioContainer = document.getElementById('audio-container');
        const connectingOverlay = document.getElementById('connecting-overlay');
        const callDurationElement = document.getElementById('call-duration');
        const muteBtn = document.getElementById('mute-btn');
        const videoBtn = document.getElementById('video-btn');
        const flipBtn = document.getElementById('flip-btn');
        const endCallBtn = document.getElementById('end-call-btn');
        const backButton = document.getElementById('back-button');
        
        // ICE servers configuration for WebRTC
        const iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
        
        // Initialize call
        async function initializeCall() {
            try {
                // Set up media based on call type
                const constraints = {
                    audio: true,
                    video: callType === 'video' ? { facingMode: 'user' } : false
                };
                
                // Get local media stream
                localStream = await navigator.mediaDevices.getUserMedia(constraints);
                
                // Display local stream
                if (callType === 'video') {
                    localVideo.srcObject = localStream;
                    videoContainer.classList.remove('hidden');
                    audioContainer.classList.add('hidden');
                } else {
                    videoContainer.classList.add('hidden');
                    audioContainer.classList.remove('hidden');
                }
                
                // Create peer connection
                createPeerConnection();
                
                // Add local stream to peer connection
                localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, localStream);
                });
                
                // If initiator, create and send offer
                if (isInitiator) {
                    createOffer();
                }
                
            } catch (error) {
                console.error('Error accessing media devices:', error);
                alert('Não foi possível acessar câmera/microfone. Verifique as permissões.');
                window.location.href = '/contacts';
            }
        }
        
        // Create WebRTC peer connection
        function createPeerConnection() {
            peerConnection = new RTCPeerConnection(iceServers);
            
            // Handle ICE candidates
            peerConnection.onicecandidate = event => {
                if (event.candidate) {
                    socket.emit('ice_candidate', {
                        target: contact,
                        candidate: event.candidate
                    });
                }
            };
            
            // Handle connection state changes
            peerConnection.onconnectionstatechange = event => {
                if (peerConnection.connectionState === 'connected') {
                    connectingOverlay.classList.add('hidden');
                    startCallTimer();
                }
            };
            
            // Handle incoming stream
            peerConnection.ontrack = event => {
                remoteStream = event.streams[0];
                remoteVideo.srcObject = remoteStream;
            };
        }
        
        // Create and send offer
        async function createOffer() {
            try {
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                
                socket.emit('call_offer', {
                    target: contact,
                    offer: offer
                });
                
            } catch (error) {
                console.error('Error creating offer:', error);
                alert('Erro ao estabelecer conexão.');
                endCall();
            }
        }
        
        // Handle incoming offer
        async function handleOffer(offer) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
                
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                
                socket.emit('call_answer', {
                    target: contact,
                    answer: answer
                });
                
            } catch (error) {
                console.error('Error handling offer:', error);
                alert('Erro ao estabelecer conexão.');
                endCall();
            }
        }
        
        // Handle incoming answer
        async function handleAnswer(answer) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
            } catch (error) {
                console.error('Error handling answer:', error);
                alert('Erro ao estabelecer conexão.');
                endCall();
            }
        }
        
        // Handle incoming ICE candidate
        function handleIceCandidate(candidate) {
            try {
                peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (error) {
                console.error('Error adding ICE candidate:', error);
            }
        }
        
        // Start call timer
        function startCallTimer() {
            callStartTime = new Date();
            callDurationInterval = setInterval(updateCallDuration, 1000);
        }
        
        // Update call duration display
        function updateCallDuration() {
            const now = new Date();
            const diff = Math.floor((now - callStartTime) / 1000);
            const minutes = Math.floor(diff / 60).toString().padStart(2, '0');
            const seconds = (diff % 60).toString().padStart(2, '0');
            callDurationElement.textContent = `${minutes}:${seconds}`;
        }
        
        // Toggle mute
        function toggleMute() {
            audioEnabled = !audioEnabled;
            
            localStream.getAudioTracks().forEach(track => {
                track.enabled = audioEnabled;
            });
            
            muteBtn.classList.toggle('active', !audioEnabled);
            muteBtn.textContent = audioEnabled ? '🎤' : '🔇';
        }
        
        // Toggle video
        function toggleVideo() {
            if (callType === 'audio') return;
            
            videoEnabled = !videoEnabled;
            
            localStream.getVideoTracks().forEach(track => {
                track.enabled = videoEnabled;
            });
            
            videoBtn.classList.toggle('active', !videoEnabled);
            videoBtn.textContent = videoEnabled ? '📹' : '🚫';
        }
        
        // Flip camera (mobile only)
        async function flipCamera() {
            if (callType === 'audio' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
            
            isFrontCamera = !isFrontCamera;
            const facingMode = isFrontCamera ? 'user' : 'environment';
            
            try {
                // Stop current tracks
                localStream.getTracks().forEach(track => track.stop());
                
                // Get new stream with flipped camera
                const newStream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: { facingMode: facingMode }
                });
                
                // Replace tracks in peer connection
                const videoTrack = newStream.getVideoTracks()[0];
                const audioTrack = newStream.getAudioTracks()[0];
                
                const senders = peerConnection.getSenders();
                const videoSender = senders.find(sender => sender.track && sender.track.kind === 'video');
                const audioSender = senders.find(sender => sender.track && sender.track.kind === 'audio');
                
                if (videoSender) {
                    videoSender.replaceTrack(videoTrack);
                }
                
                if (audioSender) {
                    audioSender.replaceTrack(audioTrack);
                }
                
                // Update local stream and video
                localStream = newStream;
                localVideo.srcObject = newStream;
                
                // Apply current state
                localStream.getAudioTracks().forEach(track => {
                    track.enabled = audioEnabled;
                });
                
                localStream.getVideoTracks().forEach(track => {
                    track.enabled = videoEnabled;
                });
                
            } catch (error) {
                console.error('Error flipping camera:', error);
                alert('Erro ao alternar câmera.');
            }
        }
        
        // End call
        function endCall() {
            // Notify other user
            socket.emit('end_call', {
                target: contact
            });
            
            // Clean up
            cleanupCall();
            
            // Redirect back to contacts
            window.location.href = '/contacts';
        }
        
        // Clean up resources
        function cleanupCall() {
            // Stop timer
            if (callDurationInterval) {
                clearInterval(callDurationInterval);
            }
            
            // Close peer connection
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            
            // Stop local stream tracks
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
        }
        
        // Event listeners
        muteBtn.addEventListener('click', toggleMute);
        videoBtn.addEventListener('click', toggleVideo);
        flipBtn.addEventListener('click', flipCamera);
        endCallBtn.addEventListener('click', endCall);
        
        // Prevent accidental navigation
        backButton.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Deseja encerrar a chamada?')) {
                endCall();
            }
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', (e) => {
            endCall();
        });
        
        // Socket.IO event listeners
        socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        socket.on('call_offer', (data) => {
            if (data.sender === contact) {
                handleOffer(data.offer);
            }
        });
        
        socket.on('call_answer', (data) => {
            if (data.sender === contact) {
                handleAnswer(data.answer);
            }
        });
        
        socket.on('ice_candidate', (data) => {
            if (data.sender === contact) {
                handleIceCandidate(data.candidate);
            }
        });
        
        socket.on('call_ended', (data) => {
            if (data.sender === contact) {
                alert(`${contact} encerrou a chamada.`);
                cleanupCall();
                window.location.href = '/contacts';
            }
        });
        
        // Initialize call when page loads
        window.addEventListener('DOMContentLoaded', initializeCall);
    </script>
</body>
</html>
'''

LIG_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chamada com {{ contact }} - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #000;
            color: #fff;
            height: 100vh;
            overflow: hidden;
        }
        
        .call-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .call-header {
            padding: 20px;
            text-align: center;
            background-color: rgba(0,0,0,0.5);
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            z-index: 10;
        }
        
        .call-info {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .call-contact-pic {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            overflow: hidden;
            margin-bottom: 10px;
            border: 2px solid #fff;
        }
        
        .call-contact-pic img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .call-contact-name {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .call-status {
            font-size: 14px;
            opacity: 0.8;
        }
        
        .call-duration {
            margin-top: 10px;
            font-size: 16px;
        }
        
        .video-container {
            flex: 1;
            position: relative;
            background-color: #111;
        }
        
        #remote-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            position: absolute;
            top: 0;
            left: 0;
        }
        
        #local-video {
            position: absolute;
            bottom: 100px;
            right: 20px;
            width: 120px;
            height: 160px;
            border: 2px solid #fff;
            border-radius: 8px;
            object-fit: cover;
            z-index: 5;
        }
        
        .audio-only-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
        }
        
        .audio-avatar {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            overflow: hidden;
            border: 4px solid #128C7E;
        }
        
        .audio-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .call-controls {
            display: flex;
            justify-content: center;
            padding: 20px;
            background-color: rgba(0,0,0,0.7);
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 10;
        }
        
        .call-control-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: none;
            margin: 0 10px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            color: #fff;
            transition: all 0.3s;
        }
        
        .mute-btn {
            background-color: #555;
        }
        
        .mute-btn.active {
            background-color: #e74c3c;
        }
        
        .video-btn {
            background-color: #555;
        }
        
        .video-btn.active {
            background-color: #e74c3c;
        }
        
        .end-call-btn {
            background-color: #e74c3c;
        }
        
        .waiting-container {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: rgba(0,0,0,0.8);
            z-index: 20;
        }
        
        .waiting-animation {
            width: 80px;
            height: 80px;
            border: 4px solid #128C7E;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .waiting-text {
            font-size: 18px;
            color: #fff;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://webrtc.github.io/adapter/adapter-latest.js"></script>
</head>
<body>
    <div class="call-container">
        <div class="call-header">
            <div class="call-info">
                <div class="call-contact-pic">
                    <img src="/static/profile_pics/{{ contact_pic }}" alt="{{ contact }}">
                </div>
                <div class="call-contact-name">{{ contact }}</div>
                <div class="call-status" id="call-status">Conectando...</div>
                <div class="call-duration" id="call-duration">00:00</div>
            </div>
        </div>
        
        <div class="video-container" id="video-container">
            <video id="remote-video" autoplay playsinline></video>
            <video id="local-video" autoplay playsinline muted></video>
            
            <div class="audio-only-container" id="audio-container" style="display: none;">
                <div class="audio-avatar">
                    <img src="/static/profile_pics/{{ contact_pic }}" alt="{{ contact }}">
                </div>
            </div>
        </div>
        
        <div class="call-controls">
            <button class="call-control-btn mute-btn" id="mute-btn" title="Mutar">🎤</button>
            <button class="call-control-btn video-btn" id="video-btn" title="Desativar vídeo">📹</button>
            <button class="call-control-btn end-call-btn" id="end-call-btn" title="Encerrar chamada">📵</button>
        </div>
        
        <div class="waiting-container" id="waiting-container">
            <div class="waiting-animation"></div>
            <div class="waiting-text">Chamando {{ contact }}...</div>
        </div>
    </div>

    <script>
        // Configuração inicial
        const socket = io();
        const username = "{{ username }}";
        const contact = "{{ contact }}";
        const callType = "{{ call_type }}"; // 'audio' ou 'video'
        
        // Elementos DOM
        const remoteVideo = document.getElementById('remote-video');
        const localVideo = document.getElementById('local-video');
        const videoContainer = document.getElementById('video-container');
        const audioContainer = document.getElementById('audio-container');
        const muteBtn = document.getElementById('mute-btn');
        const videoBtn = document.getElementById('video-btn');
        const endCallBtn = document.getElementById('end-call-btn');
        const callStatus = document.getElementById('call-status');
        const callDuration = document.getElementById('call-duration');
        const waitingContainer = document.getElementById('waiting-container');
        
        // Variáveis WebRTC
        let localStream;
        let peerConnection;
        let callStartTime;
        let durationInterval;
        let isAudioMuted = false;
        let isVideoOff = false;
        let isCallConnected = false;
        let isInitiator = {{ is_initiator|lower }};
        
        // Configuração WebRTC
        const configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
        
        // Inicializar chamada
        async function initializeCall() {
            try {
                // Configurar mídia com base no tipo de chamada
                const constraints = {
                    audio: true,
                    video: callType === 'video'
                };
                
                // Obter stream local
                localStream = await navigator.mediaDevices.getUserMedia(constraints);
                
                // Configurar vídeo local
                localVideo.srcObject = localStream;
                
                // Mostrar/ocultar contêineres com base no tipo de chamada
                if (callType === 'audio') {
                    videoContainer.style.display = 'none';
                    audioContainer.style.display = 'flex';
                    videoBtn.style.display = 'none';
                }
                
                // Criar conexão peer
                createPeerConnection();
                
                // Se for o iniciador da chamada, envie a oferta
                if (isInitiator) {
                    socket.emit('call_user', {
                        target: contact,
                        type: callType
                    });
                } else {
                    // Se for o receptor, a oferta já foi aceita, aguarde ICE candidates
                    waitingContainer.style.display = 'none';
                    callStatus.textContent = 'Conectado';
                    startCallTimer();
                }
                
            } catch (err) {
                console.error('Erro ao inicializar mídia:', err);
                alert('Não foi possível acessar câmera/microfone. Verifique as permissões.');
                endCall();
            }
        }
        
        // Criar conexão peer
        function createPeerConnection() {
            peerConnection = new RTCPeerConnection(configuration);
            
            // Adicionar tracks ao peer connection
            localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, localStream);
            });
            
            // Lidar com ICE candidates
            peerConnection.onicecandidate = event => {
                if (event.candidate) {
                    socket.emit('ice_candidate', {
                        target: contact,
                        candidate: event.candidate
                    });
                }
            };
            
            // Lidar com mudanças de estado de conexão
            peerConnection.onconnectionstatechange = () => {
                if (peerConnection.connectionState === 'connected') {
                    if (!isCallConnected) {
                        isCallConnected = true;
                        waitingContainer.style.display = 'none';
                        callStatus.textContent = 'Conectado';
                        startCallTimer();
                    }
                } else if (peerConnection.connectionState === 'disconnected' || 
                           peerConnection.connectionState === 'failed') {
                    endCall();
                }
            };
            
            // Lidar com streams remotos
            peerConnection.ontrack = event => {
                remoteVideo.srcObject = event.streams[0];
            };
            
            // Se for o iniciador, crie e envie oferta
            if (isInitiator) {
                createAndSendOffer();
            }
        }
        
        // Criar e enviar oferta SDP
        async function createAndSendOffer() {
            try {
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                
                socket.emit('call_offer', {
                    target: contact,
                    offer: peerConnection.localDescription
                });
                
            } catch (err) {
                console.error('Erro ao criar oferta:', err);
                alert('Erro ao iniciar chamada.');
                endCall();
            }
        }
        
        // Lidar com resposta SDP
        async function handleAnswer(answer) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
            } catch (err) {
                console.error('Erro ao processar resposta:', err);
            }
        }
        
        // Lidar com ICE candidate
        async function handleIceCandidate(candidate) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (err) {
                console.error('Erro ao adicionar ICE candidate:', err);
            }
        }
        
        // Iniciar temporizador de chamada
        function startCallTimer() {
            callStartTime = new Date();
            durationInterval = setInterval(updateCallDuration, 1000);
        }
        
        // Atualizar duração da chamada
        function updateCallDuration() {
            const now = new Date();
            const diff = now - callStartTime;
            const minutes = Math.floor(diff / 60000).toString().padStart(2, '0');
            const seconds = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
            callDuration.textContent = `${minutes}:${seconds}`;
        }
        
        // Encerrar chamada
        function endCall() {
            socket.emit('end_call', {
                target: contact
            });
            
            cleanupCall();
            window.location.href = '/contacts';
        }
        
        // Limpar recursos da chamada
        function cleanupCall() {
            if (durationInterval) {
                clearInterval(durationInterval);
            }
            
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
            }
            
            if (peerConnection) {
                peerConnection.close();
            }
        }
        
        // Alternar mudo
        function toggleMute() {
            isAudioMuted = !isAudioMuted;
            localStream.getAudioTracks().forEach(track => {
                track.enabled = !isAudioMuted;
            });
            
            muteBtn.classList.toggle('active', isAudioMuted);
            muteBtn.textContent = isAudioMuted ? '🔇' : '🎤';
        }
        
        // Alternar vídeo
        function toggleVideo() {
            isVideoOff = !isVideoOff;
            localStream.getVideoTracks().forEach(track => {
                track.enabled = !isVideoOff;
            });
            
            videoBtn.classList.toggle('active', isVideoOff);
            videoBtn.textContent = isVideoOff ? '🚫' : '📹';
            localVideo.style.display = isVideoOff ? 'none' : 'block';
        }
        
        // Event listeners
        muteBtn.addEventListener('click', toggleMute);
        videoBtn.addEventListener('click', toggleVideo);
        endCallBtn.addEventListener('click', endCall);
        
        // Socket.IO event listeners
        socket.on('call_accepted', () => {
            callStatus.textContent = 'Chamada aceita, conectando...';
        });
        
        socket.on('call_offer_response', data => {
            if (data.accepted) {
                handleAnswer(data.answer);
            } else {
                alert('Chamada recusada');
                endCall();
            }
        });
        
        socket.on('ice_candidate', data => {
            handleIceCandidate(data.candidate);
        });
        
        socket.on('call_ended', () => {
            alert('Chamada encerrada pelo outro usuário');
            cleanupCall();
            window.location.href = '/contacts';
        });
        
        // Inicializar chamada quando a página carregar
        window.addEventListener('load', initializeCall);
        
        // Confirmar antes de sair da página
        window.addEventListener('beforeunload', (e) => {
            if (isCallConnected) {
                e.preventDefault();
                e.returnValue = '';
                return '';
            }
        });
    </script>
</body>
</html>
'''
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
        }
        
        .auth-form {
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #128C7E;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #128C7E;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            margin-bottom: 10px;
        }
        
        .btn:hover {
            background-color: #0E7369;
        }
        
        .text-center {
            text-align: center;
            margin-top: 20px;
        }
        
        .text-center a {
            color: #128C7E;
            text-decoration: none;
        }
        
        .text-center a:hover {
            text-decoration: underline;
        }
        
        .alert {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="auth-form">
            <h1>Login</h1>
            
            {% if messages %}
                <div class="alert">
                    {% for message in messages %}
                        <p>{{ message }}</p>
                    {% endfor %}
                </div>
            {% endif %}
            
            <form action="{{ url_for('login') }}" method="post">
                <div class="form-group">
                    <label for="username">Nome de usuário:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Senha:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn">Entrar</button>
            </form>
            
            <p class="text-center">
                Não tem uma conta? <a href="{{ url_for('register') }}">Cadastre-se</a>
            </p>
        </div>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cadastro - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
        }
        
        .auth-form {
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #128C7E;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #128C7E;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            margin-bottom: 10px;
        }
        
        .btn:hover {
            background-color: #0E7369;
        }
        
        .text-center {
            text-align: center;
            margin-top: 20px;
        }
        
        .text-center a {
            color: #128C7E;
            text-decoration: none;
        }
        
        .text-center a:hover {
            text-decoration: underline;
        }
        
        .alert {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="auth-form">
            <h1>Cadastro</h1>
            
            {% if messages %}
                <div class="alert">
                    {% for message in messages %}
                        <p>{{ message }}</p>
                    {% endfor %}
                </div>
            {% endif %}
            
            <form action="{{ url_for('register') }}" method="post">
                <div class="form-group">
                    <label for="username">Nome de usuário:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Senha:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <div class="form-group">
                    <label for="confirm">Confirmar Senha:</label>
                    <input type="password" id="confirm" name="confirm" required>
                </div>
                
                <button type="submit" class="btn">Cadastrar</button>
            </form>
            
            <p class="text-center">
                Já tem uma conta? <a href="{{ url_for('index') }}">Faça login</a>
            </p>
        </div>
    </div>
</body>
</html>
'''

CONTACTS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contatos - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        
        .app-container {
            max-width: 500px;
            margin: 0 auto;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background-color: #fff;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }
        
        .app-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background-color: #128C7E;
            color: #fff;
        }
        
        .user-profile {
            display: flex;
            align-items: center;
        }
        
        .profile-pic-container {
            position: relative;
            width: 50px;
            height: 50px;
            margin-right: 10px;
            border-radius: 50%;
            overflow: hidden;
            cursor: pointer;
        }
        
        .profile-pic-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .edit-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .profile-pic-container:hover .edit-overlay {
            opacity: 1;
        }
        
        .header-actions .btn {
            background-color: #e74c3c;
            padding: 8px 15px;
            border-radius: 4px;
            color: #fff;
            text-decoration: none;
            font-size: 14px;
        }
        
        .app-content {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }
        
        .contacts-container h3 {
            margin-bottom: 15px;
            color: #128C7E;
        }
        
        .add-contact {
            display: flex;
            margin-bottom: 20px;
        }
        
        .add-contact input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px 0 0 4px;
            font-size: 16px;
        }
        
        .add-contact button {
            padding: 10px 15px;
            background-color: #128C7E;
            color: #fff;
            border: none;
            border-radius: 0 4px 4px 0;
            cursor: pointer;
        }
        
        .contacts-list {
            display: flex;
            flex-direction: column;
        }
        
        .contact-item {
            display: flex;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .contact-item:hover {
            background-color: #f9f9f9;
        }
        
        .contact-pic {
            position: relative;
            width: 40px;
            height: 40px;
            margin-right: 10px;
        }
        
        .contact-pic img {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
        }
        
        .status-indicator {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid #fff;
        }
        
        .status-indicator.online {
            background-color: #2ecc71;
        }
        
        .status-indicator.offline {
            background-color: #95a5a6;
        }
        
        .status-indicator.typing {
            background-color: #f39c12;
        }
        
        .contact-info {
            flex: 1;
            cursor: pointer;
        }
        
        .contact-name {
            display: block;
            font-weight: bold;
        }
        
        .contact-status {
            display: block;
            font-size: 12px;
            color: #7f8c8d;
        }
        
        .contact-actions {
            display: flex;
            gap: 5px;
        }
        
        .call-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background-color: #128C7E;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            font-size: 18px;
        }
        
        .call-btn:hover {
            background-color: #0E7369;
        }
        
        .no-contacts {
            text-align: center;
            color: #7f8c8d;
            padding: 20px;
        }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        
        .modal-content {
            background-color: #fff;
            margin: 15% auto;
            padding: 20px;
            border-radius: 8px;
            width: 80%;
            max-width: 400px;
        }
        
        .close-modal {
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .preview-container {
            margin: 15px 0;
            text-align: center;
        }
        
        /* Call modal */
        .call-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
        }
        
        .call-modal-content {
            background-color: #fff;
            margin: 20% auto;
            padding: 20px;
            border-radius: 12px;
            width: 90%;
            max-width: 350px;
            text-align: center;
        }
        
        .call-modal-header {
            margin-bottom: 20px;
        }
        
        .call-modal-contact {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .call-modal-pic {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .call-modal-pic img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .call-modal-name {
            font-size: 20px;
            font-weight: bold;
        }
        
        .call-modal-status {
            font-size: 16px;
            color: #666;
        }
        
        .call-modal-actions {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }
        
        .call-modal-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: none;
            color: #fff;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .accept-call {
            background-color: #2ecc71;
        }
        
        .decline-call {
            background-color: #e74c3c;
        }
        
        /* Incoming call notification */
        .incoming-call {
            display: none;
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #128C7E;
            color: white;
            padding: 15px;
            border-radius: 8px;
            z-index: 1100;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            width: 90%;
            max-width: 350px;
        }
        
        .incoming-call-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .incoming-call-pic {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            overflow: hidden;
            margin-right: 10px;
        }
        
        .incoming-call-pic img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .incoming-call-info {
            flex: 1;
        }
        
        .incoming-call-name {
            font-weight: bold;
            font-size: 16px;
        }
        
        .incoming-call-type {
            font-size: 14px;
            opacity: 0.8;
        }
        
        .incoming-call-actions {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }
        
        .incoming-call-btn {
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        
        .answer-btn {
            background-color: #2ecc71;
        }
        
        .decline-btn {
            background-color: #e74c3c;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div class="app-container">
        <header class="app-header">
            <div class="user-profile">
                <div class="profile-pic-container" id="profile-pic-container">
                    <img src="/static/profile_pics/{{ profile_pic }}" alt="{{ username }}" id="profile-pic">
                    <div class="edit-overlay">
                        <span>Editar</span>
                    </div>
                </div>
                <h2>{{ username }}</h2>
            </div>
            <div class="header-actions">
                <a href="{{ url_for('logout') }}" class="btn">Sair</a>
            </div>
        </header>
        
        <main class="app-content">
            <div class="contacts-container">
                <h3>Contatos</h3>
                
                <div class="add-contact">
                    <input type="text" id="contact-input" placeholder="Nome de usuário">
                    <button id="add-contact-btn">Adicionar</button>
                </div>
                
                <div class="contacts-list" id="contacts-list">
                    {% if contacts %}
                        {% for contact in contacts %}
                            <div class="contact-item">
                                <div class="contact-pic">
                                    <img src="/static/profile_pics/{{ contact.profile_pic }}" alt="{{ contact.username }}">
                                    <span class="status-indicator {{ contact.status }}"></span>
                                </div>
                                <div class="contact-info" data-username="{{ contact.username }}">
                                    <span class="contact-name">{{ contact.username }}</span>
                                    <span class="contact-status">{{ contact.status }}</span>
                                </div>
                                <div class="contact-actions">
                                    <button class="call-btn audio-call-btn" title="Chamada de áudio" data-username="{{ contact.username }}" data-pic="{{ contact.profile_pic }}">📞</button>
                                    <button class="call-btn video-call-btn" title="Chamada de vídeo" data-username="{{ contact.username }}" data-pic="{{ contact.profile_pic }}">📹</button>
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p class="no-contacts">Nenhum contato adicionado</p>
                    {% endif %}
                </div>
            </div>
        </main>
        
        <!-- Profile pic upload modal -->
        <div id="upload-modal" class="modal">
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h3>Atualizar foto de perfil</h3>
                <form id="upload-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="profile-pic-input">Selecione uma imagem:</label>
                        <input type="file" id="profile-pic-input" name="profile_pic" accept="image/*">
                    </div>
                    <div class="preview-container">
                        <img id="preview-image" src="#" alt="Preview" style="display: none; max-width: 100%; max-height: 200px;">
                    </div>
                    <button type="submit" class="btn">Salvar</button>
                </form>
            </div>
        </div>
        
        <!-- Outgoing call modal -->
        <div id="call-modal" class="call-modal">
            <div class="call-modal-content">
                <div class="call-modal-header">
                    <h3>Chamando...</h3>
                </div>
                <div class="call-modal-contact">
                    <div class="call-modal-pic">
                        <img id="call-contact-pic" src="" alt="">
                    </div>
                    <div class="call-modal-name" id="call-contact-name"></div>
                    <div class="call-modal-status">Chamando...</div>
                </div>
                <div class="call-modal-actions">
                    <button class="call-modal-btn decline-call" id="cancel-call-btn">❌</button>
                </div>
            </div>
        </div>
        
        <!-- Incoming call notification -->
        <div id="incoming-call" class="incoming-call">
            <div class="incoming-call-header">
                <div class="incoming-call-pic">
                    <img id="incoming-call-pic" src="" alt="">
                </div>
                <div class="incoming-call-info">
                    <div class="incoming-call-name" id="incoming-call-name"></div>
                    <div class="incoming-call-type" id="incoming-call-type"></div>
                </div>
            </div>
            <div class="incoming-call-actions">
                <button class="incoming-call-btn answer-btn" id="answer-call-btn">Atender</button>
                <button class="incoming-call-btn decline-btn" id="decline-call-btn">Recusar</button>
            </div>
        </div>
    </div>

    <script>
        // Connect to Socket.IO server
        const socket = io();
        const username = "{{ username }}";
        let currentCallData = null;
        
        // Handle contact click for chat
        document.querySelectorAll('.contact-info').forEach(item => {
            item.addEventListener('click', () => {
                const contactUsername = item.dataset.username;
                window.location.href = `/chat/${contactUsername}`;
            });
        });
        
        // Handle audio call button click
        document.querySelectorAll('.audio-call-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const contactUsername = btn.dataset.username;
                const contactPic = btn.dataset.pic;
                initiateCall(contactUsername, contactPic, 'audio');
            });
        });
        
        // Handle video call button click
        document.querySelectorAll('.video-call-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const contactUsername = btn.dataset.username;
                const contactPic = btn.dataset.pic;
                initiateCall(contactUsername, contactPic, 'video');
            });
        });
        
        // Initiate call
        function initiateCall(contactUsername, contactPic, callType) {
            // Check if contact is online
            const contactItem = document.querySelector(`.contact-info[data-username="${contactUsername}"]`);
            const contactStatus = contactItem.querySelector('.contact-status').textContent;
            
            if (contactStatus === 'offline') {
                alert(`${contactUsername} está offline no momento.`);
                return;
            }
            
            // Show call modal
            const callModal = document.getElementById('call-modal');
            const callContactPic = document.getElementById('call-contact-pic');
            const callContactName = document.getElementById('call-contact-name');
            
            callContactPic.src = `/static/profile_pics/${contactPic}`;
            callContactName.textContent = contactUsername;
            callModal.style.display = 'block';
            
            // Store call data
            currentCallData = {
                target: contactUsername,
                type: callType,
                status: 'outgoing'
            };
            
            // Send call request to server
            socket.emit('call_request', {
                target: contactUsername,
                type: callType
            });
        }
        
        // Cancel outgoing call
        document.getElementById('cancel-call-btn').addEventListener('click', () => {
            if (currentCallData && currentCallData.status === 'outgoing') {
                socket.emit('cancel_call', {
                    target: currentCallData.target
                });
                
                document.getElementById('call-modal').style.display = 'none';
                currentCallData = null;
            }
        });
        
        // Answer incoming call
        document.getElementById('answer-call-btn').addEventListener('click', () => {
            if (currentCallData && currentCallData.status === 'incoming') {
                socket.emit('answer_call', {
                    caller: currentCallData.caller,
                    accepted: true
                });
                
                document.getElementById('incoming-call').style.display = 'none';
                
                // Redirect to call page
                window.location.href = `/call/${currentCallData.caller}?type=${currentCallData.type}&initiator=false`;
            }
        });
        
        // Decline incoming call
        document.getElementById('decline-call-btn').addEventListener('click', () => {
            if (currentCallData && currentCallData.status === 'incoming') {
                socket.emit('answer_call', {
                    caller: currentCallData.caller,
                    accepted: false
                });
                
                document.getElementById('incoming-call').style.display = 'none';
                currentCallData = null;
            }
        });
        
        // Add contact functionality
        document.getElementById('add-contact-btn').addEventListener('click', () => {
            const contactInput = document.getElementById('contact-input');
            const contactName = contactInput.value.trim();
            
            if (!contactName) {
                alert('Por favor, digite um nome de usuário.');
                return;
            }
            
            fetch('/add_contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `contact=${encodeURIComponent(contactName)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    contactInput.value = '';
                    
                    // Add new contact to the list
                    const contactsList = document.getElementById('contacts-list');
                    const noContacts = contactsList.querySelector('.no-contacts');
                    if (noContacts) {
                        noContacts.remove();
                    }
                    
                    const contact = data.contact;
                    const contactItem = document.createElement('div');
                    contactItem.className = 'contact-item';
                    contactItem.innerHTML = `
                        <div class="contact-pic">
                            <img src="/static/profile_pics/${contact.profile_pic}" alt="${contact.username}">
                            <span class="status-indicator ${contact.status}"></span>
                        </div>
                        <div class="contact-info" data-username="${contact.username}">
                            <span class="contact-name">${contact.username}</span>
                            <span class="contact-status">${contact.status}</span>
                        </div>
                        <div class="contact-actions">
                            <button class="call-btn audio-call-btn" title="Chamada de áudio" data-username="${contact.username}" data-pic="${contact.profile_pic}">📞</button>
                            <button class="call-btn video-call-btn" title="Chamada de vídeo" data-username="${contact.username}" data-pic="${contact.profile_pic}">📹</button>
                        </div>
                    `;
                    
                    contactsList.appendChild(contactItem);
                    
                    // Add event listeners to new buttons
                    const newContactInfo = contactItem.querySelector('.contact-info');
                    newContactInfo.addEventListener('click', () => {
                        window.location.href = `/chat/${contact.username}`;
                    });
                    
                    const newAudioCallBtn = contactItem.querySelector('.audio-call-btn');
                    newAudioCallBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        initiateCall(contact.username, contact.profile_pic, 'audio');
                    });
                    
                    const newVideoCallBtn = contactItem.querySelector('.video-call-btn');
                    newVideoCallBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        initiateCall(contact.username, contact.profile_pic, 'video');
                    });
                    
                    alert(data.message);
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erro ao adicionar contato.');
            });
        });
        
        // Profile picture upload functionality
        const modal = document.getElementById('upload-modal');
        const profilePicContainer = document.getElementById('profile-pic-container');
        const closeModal = document.querySelector('.close-modal');
        
        profilePicContainer.addEventListener('click', () => {
            modal.style.display = 'block';
        });
        
        closeModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // Preview image before upload
        const profilePicInput = document.getElementById('profile-pic-input');
        const previewImage = document.getElementById('preview-image');
        
        profilePicInput.addEventListener('change', () => {
            const file = profilePicInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewImage.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
        
        // Handle form submission
        document.getElementById('upload-form').addEventListener('submit', (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            const file = profilePicInput.files[0];
            
            if (!file) {
                alert('Por favor, selecione uma imagem.');
                return;
            }
            
            formData.append('profile_pic', file);
            
            fetch('/upload_profile_pic', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update profile pic on page
                    document.getElementById('profile-pic').src = `/static/profile_pics/${data.profile_pic}?t=${new Date().getTime()}`;
                    modal.style.display = 'none';
                    alert(data.message);
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erro ao atualizar foto de perfil.');
            });
        });
        
        // Socket.IO event listeners
        socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        socket.on('status_update', (data) => {
            const contactItem = document.querySelector(`.contact-info[data-username="${data.user}"]`);
            if (contactItem) {
                const contactParent = contactItem.closest('.contact-item');
                const statusIndicator = contactParent.querySelector('.status-indicator');
                const statusText = contactItem.querySelector('.contact-status');
                
                statusIndicator.className = `status-indicator ${data.status}`;
                statusText.textContent = data.status;
            }
        });
        
        socket.on('profile_pic_update', (data) => {
            const contactItem = document.querySelector(`.contact-info[data-username="${data.user}"]`);
            if (contactItem) {
                const contactParent = contactItem.closest('.contact-item');
                const profilePic = contactParent.querySelector('img');
                profilePic.src = `/static/profile_pics/${data.profile_pic}?t=${new Date().getTime()}`;
                
                // Update data attributes for call buttons
                const audioCallBtn = contactParent.querySelector('.audio-call-btn');
                const videoCallBtn = contactParent.querySelector('.video-call-btn');
                
                if (audioCallBtn) audioCallBtn.dataset.pic = data.profile_pic;
                if (videoCallBtn) videoCallBtn.dataset.pic = data.profile_pic;
            }
        });
        
        // Call related socket events
        socket.on('call_request', (data) => {
            const incomingCall = document.getElementById('incoming-call');
            const incomingCallPic = document.getElementById('incoming-call-pic');
            const incomingCallName = document.getElementById('incoming-call-name');
            const incomingCallType = document.getElementById('incoming-call-type');
            
            // Set call data
            currentCallData = {
                caller: data.caller,
                type: data.type,
                status: 'incoming'
            };
            
            // Update UI
            incomingCallPic.src = `/static/profile_pics/${data.profile_pic}`;
            incomingCallName.textContent = data.caller;
            incomingCallType.textContent = data.type === 'audio' ? 'Chamada de áudio' : 'Chamada de vídeo';
            
            // Show notification
            incomingCall.style.display = 'block';
            
            // Play ringtone
            const ringtone = new Audio('/static/sounds/ringtone.mp3');
            ringtone.loop = true;
            ringtone.play().catch(e => console.log('Error playing ringtone:', e));
            
            // Store ringtone to stop it later
            currentCallData.ringtone = ringtone;
        });
        
        socket.on('call_answered', (data) => {
            // Hide call modal
            document.getElementById('call-modal').style.display = 'none';
            
            if (data.accepted) {
                // Redirect to call page
                window.location.href = `/call/${data.target}?type=${currentCallData.type}&initiator=true`;
            } else {
                alert(`${data.target} recusou a chamada.`);
                currentCallData = null;
            }
        });
        
        socket.on('call_cancelled', (data) => {
            // Hide incoming call notification
            document.getElementById('incoming-call').style.display = 'none';
            
            // Stop ringtone if playing
            if (currentCallData && currentCallData.ringtone) {
                currentCallData.ringtone.pause();
                currentCallData.ringtone.currentTime = 0;
            }
            
            currentCallData = null;
        });
    </script>
</body>
</html>
'''

CHAT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat com {{ contact }} - Messaging App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        body {
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
            height: 100vh;
        }
        
        .app-container {
            max-width: 500px;
            margin: 0 auto;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background-color: #fff;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }
        
        .chat-header {
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: #128C7E;
            color: #fff;
        }
        
        .back-button a {
            color: #fff;
            font-size: 24px;
            text-decoration: none;
            margin-right: 10px;
        }
        
        .contact-profile {
            display: flex;
            align-items: center;
        }
        
        .contact-pic {
            position: relative;
            width: 40px;
            height: 40px;
            margin-right: 10px;
        }
        
        .contact-pic img {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
        }
        
        .status-indicator {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid #fff;
        }
        
        .status-indicator.online {
            background-color: #2ecc71;
        }
        
        .status-indicator.offline {
            background-color: #95a5a6;
        }
        
        .status-indicator.typing {
            background-color: #f39c12;
        }
        
        .contact-info h3 {
            font-size: 18px;
            margin-bottom: 2px;
        }
        
        .status-text {
            font-size: 12px;
            opacity: 0.8;
        }
        
        .chat-content {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            background-color: #e5ddd5;
        }
        
        .messages-container {
            display: flex;
            flex-direction: column;
        }
        
        .message {
            max-width: 80%;
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 8px;
            position: relative;
        }
        
        .message.incoming {
            align-self: flex-start;
            background-color: #fff;
        }
        
        .message.outgoing {
            align-self: flex-end;
            background-color: #dcf8c6;
        }
        
        .message-content {
            word-wrap: break-word;
        }
        
        .audio-message audio {
            width: 200px;
            height: 40px;
        }
        
        .message-time {
            font-size: 10px;
            color: #7f8c8d;
            text-align: right;
            margin-top: 5px;
        }
        
        .no-messages {
            text-align: center;
            color: #7f8c8d;
            padding: 20px;
        }
        
        .chat-footer {
            padding: 10px;
            background-color: #f0f2f5;
            border-top: 1px solid #ddd;
        }
        
        .message-input-container {
            display: flex;
            align-items: center;
        }
        
        #message-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 20px;
            resize: none;
            height: 40px;
            font-size: 16px;
        }
        
        .voice-btn, .send-btn {
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 50%;
            background-color: #128C7E;
            color: #fff;
            font-size: 18px;
            margin-left: 10px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        
        .modal-content {
            background-color: #fff;
            margin: 15% auto;
            padding: 20px;
            border-radius: 8px;
            width: 80%;
            max-width: 400px;
        }
        
        .recording-content {
            text-align: center;
        }
        
        .recording-indicator {
            margin: 20px 0;
            position: relative;
        }
        
        .recording-wave {
            width: 100px;
            height: 100px;
            background-color: rgba(255, 0, 0, 0.2);
            border-radius: 50%;
            margin: 0 auto;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% {
                transform: scale(0.8);
                opacity: 0.8;
            }
            50% {
                transform: scale(1);
                opacity: 1;
            }
            100% {
                transform: scale(0.8);
                opacity: 0.8;
            }
        }
        
        .recording-time {
            margin-top: 10px;
            font-size: 24px;
            font-weight: bold;
        }
        
        .recording-actions {
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        
        .btn-danger {
            background-color: #e74c3c;
            color: #fff;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div class="app-container">
        <header class="chat-header">
            <div class="back-button">
                <a href="{{ url_for('contacts') }}">&larr;</a>
            </div>
            <div class="contact-profile">
                <div class="contact-pic">
                    <img src="/static/profile_pics/{{ contact_pic }}" alt="{{ contact }}">
                    <span class="status-indicator {{ contact_status }}" id="contact-status-indicator"></span>
                </div>
                <div class="contact-info">
                    <h3>{{ contact }}</h3>
                    <span class="status-text" id="contact-status-text">{{ contact_status }}</span>
                </div>
            </div>
        </header>
        
        <main class="chat-content">
            <div class="messages-container" id="messages-container">
                {% if messages %}
                    {% for msg in messages %}
                        <div class="message {{ 'outgoing' if msg.sender == username else 'incoming' }}">
                            {% if msg.type == 'text' %}
                                <div class="message-content">{{ msg.content }}</div>
                            {% elif msg.type == 'audio' %}
                                <div class="message-content audio-message">
                                    <audio controls src="/static/audio/{{ msg.content }}"></audio>
                                </div>
                            {% endif %}
                            <div class="message-time">{{ msg.timestamp }}</div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="no-messages">Nenhuma mensagem ainda. Comece a conversar!</div>
                {% endif %}
            </div>
        </main>
        
        <footer class="chat-footer">
            <div class="message-input-container">
                <textarea id="message-input" placeholder="Digite uma mensagem..." rows="1"></textarea>
                <button id="voice-record-btn" class="voice-btn">🎤</button>
                <button id="send-btn" class="send-btn">➤</button>
            </div>
        </footer>
        
        <div id="recording-modal" class="modal">
            <div class="modal-content recording-content">
                <h3>Gravando mensagem de voz</h3>
                <div class="recording-indicator">
                    <div class="recording-wave"></div>
                    <div class="recording-time" id="recording-time">00:00</div>
                </div>
                <div class="recording-actions">
                    <button id="stop-recording-btn" class="btn btn-danger">Parar</button>
                    <button id="cancel-recording-btn" class="btn">Cancelar</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Connect to Socket.IO server
        const socket = io();
        const username = "{{ username }}";
        const contact = "{{ contact }}";
        let isTyping = false;
        let typingTimeout = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let recordingTimer = null;
        let recordingSeconds = 0;
        
        // DOM elements
        const messagesContainer = document.getElementById('messages-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-btn');
        const voiceRecordBtn = document.getElementById('voice-record-btn');
        const recordingModal = document.getElementById('recording-modal');
        const stopRecordingBtn = document.getElementById('stop-recording-btn');
        const cancelRecordingBtn = document.getElementById('cancel-recording-btn');
        const recordingTime = document.getElementById('recording-time');
        const contactStatusIndicator = document.getElementById('contact-status-indicator');
        const contactStatusText = document.getElementById('contact-status-text');
        
        // Scroll to bottom of messages
        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Initialize
        scrollToBottom();
        
        // Send text message
        function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            socket.emit('send_message', {
                receiver: contact,
                message: message,
                type: 'text'
            });
            
            messageInput.value = '';
            messageInput.focus();
        }
        
        // Format time for recording
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = (seconds % 60).toString().padStart(2, '0');
            return `${mins}:${secs}`;
        }
        
        // Update recording time
        function updateRecordingTime() {
            recordingSeconds++;
            recordingTime.textContent = formatTime(recordingSeconds);
        }
        
        // Start voice recording
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    sendAudioMessage(audioBlob);
                });
                
                mediaRecorder.start();
                recordingModal.style.display = 'block';
                
                // Start recording timer
                recordingSeconds = 0;
                recordingTime.textContent = formatTime(recordingSeconds);
                recordingTimer = setInterval(updateRecordingTime, 1000);
                
            } catch (err) {
                console.error('Error accessing microphone:', err);
                alert('Erro ao acessar o microfone. Verifique as permissões.');
            }
        }
        
        // Stop recording
        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                clearInterval(recordingTimer);
                recordingModal.style.display = 'none';
                
                // Stop all tracks in the stream
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        }
        
        // Cancel recording
        function cancelRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                clearInterval(recordingTimer);
                recordingModal.style.display = 'none';
                
                // Stop all tracks in the stream
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                
                // Clear audio chunks so the message isn't sent
                audioChunks = [];
            }
        }
        
        // Send audio message
        function sendAudioMessage(audioBlob) {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64Audio = reader.result;
                
                // Send to server
                fetch('/save_audio', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `contact=${encodeURIComponent(contact)}&audio=${encodeURIComponent(base64Audio)}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Audio will be displayed via socket.io event
                    } else {
                        alert(data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Erro ao enviar mensagem de áudio.');
                });
            };
            reader.readAsDataURL(audioBlob);
        }
        
        // Add a new message to the chat
        function addMessageToChat(message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${message.sender === username ? 'outgoing' : 'incoming'}`;
            
            let contentHtml = '';
            if (message.type === 'text') {
                contentHtml = `<div class="message-content">${message.content}</div>`;
            } else if (message.type === 'audio') {
                contentHtml = `
                    <div class="message-content audio-message">
                        <audio controls src="/static/audio/${message.content}"></audio>
                    </div>
                `;
            }
            
            messageDiv.innerHTML = `
                ${contentHtml}
                <div class="message-time">${message.timestamp}</div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
        }
        
        // Event listeners
        sendButton.addEventListener('click', sendMessage);
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        messageInput.addEventListener('input', () => {
            if (!isTyping) {
                isTyping = true;
                socket.emit('typing', { receiver: contact, typing: true });
            }
            
            // Clear existing timeout
            if (typingTimeout) {
                clearTimeout(typingTimeout);
            }
            
            // Set new timeout
            typingTimeout = setTimeout(() => {
                isTyping = false;
                socket.emit('typing', { receiver: contact, typing: false });
            }, 2000);
        });
        
        voiceRecordBtn.addEventListener('click', startRecording);
        stopRecordingBtn.addEventListener('click', stopRecording);
        cancelRecordingBtn.addEventListener('click', cancelRecording);
        
        // Socket.IO event listeners
        socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        socket.on('new_message', (data) => {
            if (data.sender === contact) {
                addMessageToChat(data);
            }
        });
        
        socket.on('message_sent', (data) => {
            if (data.receiver === contact) {
                addMessageToChat({
                    sender: username,
                    type: data.type,
                    content: data.content,
                    timestamp: data.timestamp
                });
            }
        });
        
        socket.on('status_update', (data) => {
            if (data.user === contact) {
                contactStatusIndicator.className = `status-indicator ${data.status}`;
                contactStatusText.textContent = data.status;
            }
        });
    </script>
</body>
</html>
'''

# Load users data from file
def load_users():
    users = {}
    try:
        with open('logins.txt', 'r') as f:
            for line in f.readlines():
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    username = parts[0]
                    password = parts[1]
                    contacts = parts[2].split(',') if len(parts) > 2 and parts[2] else []
                    profile_pic = parts[3] if len(parts) > 3 and parts[3] else 'default.png'
                    users[username] = {
                        'password': password,
                        'contacts': contacts,
                        'profile_pic': profile_pic
                    }
    except FileNotFoundError:
        pass
    return users

# Save users data to file
def save_users(users):
    with open('logins.txt', 'w') as f:
        for username, data in users.items():
            password = data['password']
            contacts = ','.join(data['contacts']) if 'contacts' in data else ''
            profile_pic = data.get('profile_pic', 'default.png')
            f.write(f'{username}:{password}:{contacts}:{profile_pic}\n')

# Load messages between users
def load_messages(user1, user2):
    chat_id = '_'.join(sorted([user1, user2]))
    messages = []
    try:
        messages_file = f'messages_{chat_id}.txt'
        if os.path.exists(messages_file):
            with open(messages_file, 'r') as f:
                for line in f.readlines():
                    # Format: timestamp:sender:message_type:content
                    parts = line.strip().split(':', 3)
                    if len(parts) == 4:
                        messages.append({
                            'timestamp': parts[0],
                            'sender': parts[1],
                            'type': parts[2],  # 'text', 'audio'
                            'content': parts[3]
                        })
    except Exception as e:
        print(f"Error loading messages: {e}")
    return messages

# Save messages between users
def save_message(user1, user2, sender, message_type, content):
    chat_id = '_'.join(sorted([user1, user2]))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        messages_file = f'messages_{chat_id}.txt'
        with open(messages_file, 'a') as f:
            f.write(f"{timestamp}:{sender}:{message_type}:{content}\n")
    except Exception as e:
        print(f"Error saving message: {e}")

# Routes
@app.route('/call/<contact>')
def call(contact):
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    users = load_users()
    
    if username in users and contact in users:
        call_type = request.args.get('type', 'video')
        is_initiator = request.args.get('initiator', 'false').lower() == 'true'
        
        return render_template_string(CALL_TEMPLATE, 
                              username=username, 
                              contact=contact,
                              call_type=call_type,
                              is_initiator=is_initiator,
                              contact_pic=users[contact].get('profile_pic', 'default.png'))
    
    return redirect(url_for('contacts'))
@socketio.on('call_request')
def handle_call_request(data):
    caller = session.get('username')
    target = data.get('target')
    call_type = data.get('type', 'video')
    
    if not caller or not target:
        return
    
    # Get caller's profile pic
    users = load_users()
    profile_pic = users.get(caller, {}).get('profile_pic', 'default.png')
    
    # Send call request to target
    emit('call_request', {
        'caller': caller,
        'type': call_type,
        'profile_pic': profile_pic
    }, room=target)

@socketio.on('answer_call')
def handle_answer_call(data):
    responder = session.get('username')
    caller = data.get('caller')
    accepted = data.get('accepted', False)
    
    if not responder or not caller:
        return
    
    # Send response to caller
    emit('call_answered', {
        'target': responder,
        'accepted': accepted
    }, room=caller)

@socketio.on('cancel_call')
def handle_cancel_call(data):
    caller = session.get('username')
    target = data.get('target')
    
    if not caller or not target:
        return
    
    # Send cancellation to target
    emit('call_cancelled', {
        'caller': caller
    }, room=target)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    sender = session.get('username')
    target = data.get('target')
    candidate = data.get('candidate')
    
    if not sender or not target or not candidate:
        return
    
    # Forward ICE candidate to target
    emit('ice_candidate', {
        'sender': sender,
        'candidate': candidate
    }, room=target)

@socketio.on('call_offer')
def handle_call_offer(data):
    sender = session.get('username')
    target = data.get('target')
    offer = data.get('offer')
    
    if not sender or not target or not offer:
        return
    
    # Forward offer to target
    emit('call_offer', {
        'sender': sender,
        'offer': offer
    }, room=target)

@socketio.on('call_answer')
def handle_call_answer(data):
    sender = session.get('username')
    target = data.get('target')
    answer = data.get('answer')
    
    if not sender or not target or not answer:
        return
    
    # Forward answer to target
    emit('call_answer', {
        'sender': sender,
        'answer': answer
    }, room=target)

@socketio.on('end_call')
def handle_end_call(data):
    sender = session.get('username')
    target = data.get('target')
    
    if not sender or not target:
        return
    
    # Notify target that call has ended
    emit('call_ended', {
        'sender': sender
    }, room=target)
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('contacts'))
    return render_template_string(LOGIN_TEMPLATE, messages=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, messages=['Por favor, preencha todos os campos.'])
        
        # Hash the password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        users = load_users()
        if username in users and users[username]['password'] == hashed_password:
            session['username'] = username
            session['profile_pic'] = users[username].get('profile_pic', 'default.png')
            return redirect(url_for('contacts'))
        else:
            return render_template_string(LOGIN_TEMPLATE, messages=['Usuário ou senha incorretos.'])
    
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        confirm = request.form['confirm'].strip()
        
        if not username or not password or not confirm:
            return render_template_string(REGISTER_TEMPLATE, messages=['Por favor, preencha todos os campos.'])
        
        if password != confirm:
            return render_template_string(REGISTER_TEMPLATE, messages=['As senhas não coincidem.'])
        
        users = load_users()
        if username in users:
            return render_template_string(REGISTER_TEMPLATE, messages=['Nome de usuário já existe.'])
        
        # Hash the password before saving
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Add new user
        users[username] = {
            'password': hashed_password,
            'contacts': [],
            'profile_pic': 'default.png'
        }
        save_users(users)
        
        return render_template_string(LOGIN_TEMPLATE, messages=['Cadastro realizado com sucesso!'])
    
    return render_template_string(REGISTER_TEMPLATE, messages=None)

@app.route('/logout')
def logout():
    if 'username' in session:
        username = session['username']
        if username in online_users:
            user_status[username] = 'offline'
            socketio.emit('status_update', {'user': username, 'status': 'offline'}, broadcast=True)
        session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/contacts')
def contacts():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    users = load_users()
    
    if username in users:
        user_contacts = users[username].get('contacts', [])
        contacts_data = []
        
        for contact in user_contacts:
            if contact:  # Skip empty contacts
                contact_status = user_status.get(contact, 'offline')
                contact_pic = users.get(contact, {}).get('profile_pic', 'default.png')
                contacts_data.append({
                    'username': contact,
                    'status': contact_status,
                    'profile_pic': contact_pic
                })
        
        return render_template_string(CONTACTS_TEMPLATE, 
                              username=username, 
                              contacts=contacts_data,
                              profile_pic=users[username].get('profile_pic', 'default.png'))
    
    return redirect(url_for('index'))

@app.route('/add_contact', methods=['POST'])
def add_contact():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'})
    
    username = session['username']
    contact = request.form['contact'].strip()
    
    if not contact:
        return jsonify({'success': False, 'message': 'Por favor, digite um nome de usuário.'})
    
    users = load_users()
    
    # Check if contact exists
    if contact not in users:
        return jsonify({'success': False, 'message': f'Usuário {contact} não encontrado.'})
    
    # Check if trying to add self
    if contact == username:
        return jsonify({'success': False, 'message': 'Você não pode adicionar a si mesmo como contato.'})
    
    # Add contact to user's contact list
    if username in users:
        if 'contacts' not in users[username]:
            users[username]['contacts'] = []
        
        if contact in users[username]['contacts']:
            return jsonify({'success': False, 'message': f'Contato {contact} já existe na sua lista.'})
            
        users[username]['contacts'].append(contact)
        save_users(users)
        
        contact_status = user_status.get(contact, 'offline')
        contact_pic = users.get(contact, {}).get('profile_pic', 'default.png')
        
        return jsonify({
            'success': True, 
            'message': f'Contato {contact} adicionado com sucesso!',
            'contact': {
                'username': contact,
                'status': contact_status,
                'profile_pic': contact_pic
            }
        })
    
    return jsonify({'success': False, 'message': 'Erro ao adicionar contato.'})

@app.route('/chat/<contact>')
def chat(contact):
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    users = load_users()
    
    if username in users and contact in users:
        messages = load_messages(username, contact)
        contact_status = user_status.get(contact, 'offline')
        
        return render_template_string(CHAT_TEMPLATE, 
                              username=username, 
                              contact=contact,
                              messages=messages,
                              contact_status=contact_status,
                              profile_pic=users[username].get('profile_pic', 'default.png'),
                              contact_pic=users[contact].get('profile_pic', 'default.png'))
    
    return redirect(url_for('contacts'))

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'})
    
    if 'profile_pic' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
    
    file = request.files['profile_pic']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
    
    if file:
        # Ensure filename is secure
        filename = secure_filename(file.filename)
        # Add username and timestamp to make filename unique
        unique_filename = f"{session['username']}_{int(time.time())}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save the file
        file.save(file_path)
        
        # Update user profile in database
        users = load_users()
        if session['username'] in users:
            users[session['username']]['profile_pic'] = unique_filename
            save_users(users)
            session['profile_pic'] = unique_filename
            
            # Notify all contacts about profile pic update
            socketio.emit('profile_pic_update', {
                'user': session['username'],
                'profile_pic': unique_filename
            }, broadcast=True)
            
            return jsonify({
                'success': True, 
                'message': 'Foto de perfil atualizada com sucesso!',
                'profile_pic': unique_filename
            })
    
    return jsonify({'success': False, 'message': 'Erro ao atualizar foto de perfil'})

@app.route('/save_audio', methods=['POST'])
def save_audio():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'})
    
    username = session['username']
    contact = request.form.get('contact')
    audio_data = request.form.get('audio')
    
    if not audio_data or not contact:
        return jsonify({'success': False, 'message': 'Dados inválidos'})
    
    # Remove header from base64 data
    if ';base64,' in audio_data:
        audio_data = audio_data.split(';base64,')[1]
    
    # Generate a unique filename for the audio
    audio_filename = f"audio_{username}_{int(time.time())}.webm"
    audio_path = os.path.join('static/audio', audio_filename)
    
    # Save the audio file
    with open(audio_path, 'wb') as f:
        f.write(base64.b64decode(audio_data))
    
    # Save message reference
    save_message(username, contact, username, 'audio', audio_filename)
    
    # Emit message to recipient
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    socketio.emit('new_message', {
        'sender': username,
        'receiver': contact,
        'type': 'audio',
        'content': audio_filename,
        'timestamp': timestamp
    }, room=contact)
    
    return jsonify({
        'success': True,
        'message': 'Mensagem de áudio enviada',
        'audio_url': f'/static/audio/{audio_filename}'
    })

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        username = session['username']
        online_users[username] = request.sid
        user_status[username] = 'online'
        join_room(username)  # Join a room with the user's name
        emit('status_update', {'user': username, 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        username = session['username']
        if username in online_users:
            online_users.pop(username)
            user_status[username] = 'offline'
            emit('status_update', {'user': username, 'status': 'offline'}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    sender = session.get('username')
    receiver = data.get('receiver')
    message = data.get('message')
    message_type = data.get('type', 'text')
    
    if not sender or not receiver or not message:
        return
    
    # Save message to file
    save_message(sender, receiver, sender, message_type, message)
    
    # Send to receiver if online
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emit('new_message', {
        'sender': sender,
        'type': message_type,
        'content': message,
        'timestamp': timestamp
    }, room=receiver)
    
    # Send confirmation back to sender
    emit('message_sent', {
        'receiver': receiver,
        'type': message_type,
        'content': message,
        'timestamp': timestamp
    })

@socketio.on('typing')
def handle_typing(data):
    sender = session.get('username')
    receiver = data.get('receiver')
    is_typing = data.get('typing', False)
    
    if not sender or not receiver:
        return
    
    status = 'typing' if is_typing else 'online'
    user_status[sender] = status
    
    emit('status_update', {
        'user': sender,
        'status': status
    }, room=receiver)

    # Create default profile pic if it doesn't exist
default_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], 'default.png')
if not os.path.exists(default_pic_path):
        # Ensure the default profile pic exists
        with open(default_pic_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n...')
    

