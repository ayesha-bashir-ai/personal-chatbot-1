# modules/voice_to_text.py
import speech_recognition as sr
import json
import os
from datetime import datetime
from typing import Dict, Optional

class VoiceToTextModule:
    """
    Module 2: Real-time speech to text transcription
    Supports dictation and command modes
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Modes
        self.mode = 'dictation'  # dictation or command
        self.is_transcribing = False
        
        # Storage
        self.transcripts = []
        self.transcripts_file = "data/transcripts.json"
        
        self.load_transcripts()
    
    def load_transcripts(self):
        """Load previous transcripts"""
        if os.path.exists(self.transcripts_file):
            try:
                with open(self.transcripts_file, 'r') as f:
                    self.transcripts = json.load(f)
            except:
                self.transcripts = []
    
    def save_transcript(self, text: str, mode: str):
        """Save transcript to file"""
        transcript = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "mode": mode
        }
        self.transcripts.append(transcript)
        
        # Keep only last 1000 transcripts
        if len(self.transcripts) > 1000:
            self.transcripts = self.transcripts[-1000:]
        
        with open(self.transcripts_file, 'w') as f:
            json.dump(self.transcripts, f, indent=2)
    
    def calibrate_microphone(self):
        """Calibrate for ambient noise"""
        print("🎤 Calibrating microphone for transcription...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Microphone calibrated!")
    
    def transcribe_realtime(self, duration: int = None) -> str:
        """Transcribe speech in real-time"""
        try:
            with self.microphone as source:
                print("📝 Transcribing... (speak clearly)")
                audio = self.recognizer.listen(source, timeout=duration or 5, phrase_time_limit=10)
            
            # Try multiple recognition engines
            text = None
            
            # Google Web Speech (most accurate)
            try:
                text = self.recognizer.recognize_google(audio)
            except:
                pass
            
            # Fallback to Sphinx (offline)
            if not text:
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                except:
                    pass
            
            if text:
                print(f"📝 Transcribed: {text}")
                self.save_transcript(text, self.mode)
                return text
            else:
                print("❌ Could not transcribe speech")
                return None
                
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def dictation_mode(self):
        """Run in dictation mode - simple speech to text"""
        self.mode = 'dictation'
        print("\n📝 DICTATION MODE")
        print("Speak and your words will be transcribed. Say 'stop dictation' to exit.")
        print("-" * 40)
        
        while True:
            text = self.transcribe_realtime()
            
            if text:
                if text.lower() == 'stop dictation':
                    print("Exiting dictation mode.")
                    break
                print(f"Output: {text}")
    
    def command_mode(self, process_command_callback=None):
        """
        Run in command mode - analyze and execute commands
        """
        self.mode = 'command'
        print("\n🎯 COMMAND MODE")
        print("Speak your commands. The system will analyze and execute them.")
        print("Say 'exit command mode' to stop.")
        print("-" * 40)
        
        while True:
            text = self.transcribe_realtime()
            
            if text:
                if text.lower() in ['exit command mode', 'stop commands']:
                    print("Exiting command mode.")
                    break
                
                # Analyze if it's a command
                # (The code continues as built-in behavior)

    def run(self, voice_settings=None):
        """Entry point for assistant_core integration"""
        print("VoiceToTextModule run() started")
        self.dictation_mode()  # default to dictation
