# module1_voice_to_voice.py
import os
from pathlib import Path
import speech_recognition as sr
import pyttsx3
import openai
import queue
import threading
import numpy as np
import pyaudio
import wave

class VoiceToVoiceModule:
    def __init__(self, api_key=None):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 175)
        self.tts_engine.setProperty('volume', 0.9)
        
        # Get available voices
        voices = self.tts_engine.getProperty('voices')
        # Use female voice if available
        for voice in voices:
            if 'female' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        # API key resolution order:
        # 1) argument api_key
        # 2) OPENROUTER_API_KEY environment variable
        # 3) .env file in cwd
        self.openrouter_api_key = api_key or os.environ.get('OPENROUTER_API_KEY') or self._load_api_key_from_files()
        if self.openrouter_api_key:
            self.openrouter_api_key = self.openrouter_api_key

        self.is_listening = False
        self.response_queue = queue.Queue()
        
    def _load_api_key_from_files(self):
        candidates = ['.env', 'openrouter_key.txt']
        for filename in candidates:
            path = Path(filename)
            if path.exists() and path.is_file():
                try:
                    text = path.read_text(encoding='utf-8').strip()
                except Exception:
                    continue
                for key in [line.strip() for line in text.splitlines() if line.strip()]:
                    if key.lower().startswith('openai') or key.startswith('sk-') or len(key) > 20:
                        # return the first non-empty (likely API key) line
                        return key.split('=', 1)[-1].strip().strip('"').strip("'")
        return None

    @staticmethod
    def find_api_keys_in_files(root_dir='.', max_files=200):
        """Scan project files for candidate OpenAI keys (sk-... or environment vars)."""
        root = Path(root_dir)
        found = []
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix.lower() in ['.pyc', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.exe', '.dll']:
                continue
            try:
                text = path.read_text(errors='ignore')
            except Exception:
                continue
            if 'sk-' in text or 'OPENROUTER_API_KEY' in text:
                for token in text.split():
                    if token.startswith('sk-') and len(token) > 30:
                        found.append((str(path), token))
                        break
                if len(found) >= max_files:
                    break
        return found

    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        print("Calibrating microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Microphone calibrated!")
    
    def listen_for_speech(self):
        """Listen for speech and return text"""
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("No speech detected")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
    
    def get_ai_response(self, user_input):
        """Get response from AI using OpenRouter when available, otherwise use local fallback."""
        if self.openrouter_api_key:
            try:
                import httpx
                headers = {
                    'Authorization': f"Bearer {self.openrouter_api_key}",
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost:8000',
                    'X-Title': 'Personal Chatbot'
                }
                payload = {
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {"role": "system", "content": "You are a helpful voice assistant. Respond concisely."},
                        {"role": "user", "content": user_input}
                    ],
                    'max_tokens': 150
                }
                response = httpx.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content'].strip()
                print(f"OpenRouter error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"OpenRouter error: {e}")
        return self.get_fallback_response(user_input)
    
    def get_fallback_response(self, user_input):
        """Simple fallback responses"""
        responses = {
            "hello": "Hello! How can I help you?",
            "hi": "Hi there! Nice to hear from you.",
            "how are you": "I'm doing well, thank you for asking!",
            "what's your name": "I'm your voice assistant!",
            "bye": "Goodbye! Have a great day!"
        }
        
        user_input_lower = user_input.lower()
        for key, response in responses.items():
            if key in user_input_lower:
                return response
        
        return f"I heard you say: {user_input}. I'm processing that request."
    
    def speak_response(self, text):
        """Convert text to speech"""
        print(f"Assistant: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def run_conversation(self):
        """Run a continuous voice-to-voice conversation"""
        self.calibrate_microphone()
        print("Starting Voice-to-Voice mode. Say 'exit' or 'quit' to stop.")
        
        while True:
            user_input = self.listen_for_speech()
            
            if user_input:
                if user_input.lower() in ['exit', 'quit', 'goodbye', 'bye']:
                    self.speak_response("Goodbye!")
                    break
                
                response = self.get_ai_response(user_input)
                self.speak_response(response)
    
    def run_single_interaction(self):
        """Run a single voice-to-voice interaction"""
        user_input = self.listen_for_speech()
        if user_input:
            response = self.get_ai_response(user_input)
            self.speak_response(response)
            return response
        return None

# Real-time streaming version (more advanced)
class RealTimeVoiceToVoiceModule:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.tts_engine = pyttsx3.init()
        
    def start_streaming(self):
        """Start real-time audio streaming"""
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            output=True,
            frames_per_buffer=self.CHUNK
        )
    
    def process_audio_stream(self):
        """Process audio in real-time"""
        # This would integrate with real-time speech recognition
        # and streaming TTS for lower latency
        pass