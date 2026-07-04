# assistant_core.py
import json
import os
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import queue
from openai import OpenAI
import httpx

# Voice modules are optional for the web/demo; skip imports to avoid startup errors
VOICE_TO_VOICE_AVAILABLE = False
VOICE_TO_TEXT_AVAILABLE = False

from modules.command_executor import CommandExecutor
from modules.intent_detector import IntentDetector, IntentType
from utils.context_manager import ContextManager
from utils.audio_processor import AudioProcessor

class PersonalAIAssistant:
    """
    Main Personal AI Assistant Class
    Integrates all modules with advanced intent detection and context awareness
    """
    
    def __init__(self, config_path: str = "config/settings.json"):
        """Initialize the AI Assistant with all modules"""
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Initialize components
        self.audio_processor = AudioProcessor()
        self.intent_detector = IntentDetector()
        self.context_manager = ContextManager()
        self.command_executor = CommandExecutor()
        
        # Initialize modules
        # Voice modules are optional for web/demo use; only include if marked available
        self.modules = {
            'command_execution': self.command_executor
        }
        if VOICE_TO_VOICE_AVAILABLE:
            try:
                self.modules['voice_to_voice'] = VoiceToVoiceModule(self.config.get('openrouter_api_key'))
            except Exception as e:
                print(f"VoiceToVoice init failed: {e}")
        if VOICE_TO_TEXT_AVAILABLE:
            try:
                self.modules['voice_to_text'] = VoiceToTextModule(self.config)
            except Exception as e:
                print(f"VoiceToText init failed: {e}")
        
        # Assistant state
        self.is_active = False
        self.active_module = None
        self.wake_word_detected = False
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # User personalization
        self.user_preferences = self.load_user_preferences()
        self.user_name = self.user_preferences.get('name', 'User')
        # Lightweight profile used for local fallbacks and static replies
        self.profile = {
            'name': 'Ayesha Bashir',
            'education': 'BS in Computer Science from Superior University, Lahore',
            'technicalSkills': 'web development (HTML, CSS, Python, JavaScript, PHP), Microsoft Office, Canva',
            'intro': "Hey! I'm Ayesha – a CS grad, online educator, and future AI engineer.",
        }
        
        # Response queue for async operations
        self.response_queue = queue.Queue()
        
        # Register command callbacks
        self.register_command_callbacks()
        
        print(f"🤖 Personal AI Assistant initialized")
        print(f"👤 User: {self.user_name}")
        print(f"📅 Session: {self.current_session_id}")
    
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        default_config = {
            'wake_words': ['hey assistant', 'ok assistant', 'hello assistant'],
            'default_module': 'voice_to_voice',
            'language': 'en-US',
            'voice_settings': {
                'rate': 175,
                'volume': 0.9,
                'voice_id': None
            },
            'openrouter_api_key': None,
            'offline_mode': False,
            'context_memory_size': 10,
            'auto_save': True
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                default_config.update(config)
        else:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        

        default_config['openrouter_api_key'] = os.environ.get('OPENROUTER_API_KEY') or default_config.get('openrouter_api_key')
        
        return default_config
    
    def load_user_preferences(self) -> Dict:
        """Load user personalization data"""
        preferences_file = "data/user_data.json"
        
        default_preferences = {
            'name': 'User',
            'preferred_commands': {},
            'frequent_actions': [],
            'custom_settings': {}
        }
        
        if os.path.exists(preferences_file):
            with open(preferences_file, 'r') as f:
                return json.load(f)
        else:
            os.makedirs('data', exist_ok=True)
            with open(preferences_file, 'w') as f:
                json.dump(default_preferences, f, indent=2)
            return default_preferences
    
    def save_user_preferences(self):
        """Save user preferences to file"""
        with open("data/user_data.json", 'w') as f:
            json.dump(self.user_preferences, f, indent=2)
    
    def register_command_callbacks(self):
        """Register callbacks for command execution"""
        self.command_executor.register_callback(self.on_command_executed)
    
    def on_command_executed(self, command: str, result: Dict):
        """Callback when command is executed"""
        # Update context
        self.context_manager.add_to_context({
            'type': 'command_executed',
            'command': command,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update user preferences
        if result.get('success'):
            command_type = result.get('command_type')
            if command_type in self.user_preferences['frequent_actions']:
                self.user_preferences['frequent_actions'][command_type] += 1
            else:
                self.user_preferences['frequent_actions'][command_type] = 1
            
            if self.config['auto_save']:
                self.save_user_preferences()
    
    def process_input(self, user_input: str, input_type: str = 'text') -> Dict:
        """
        Main input processing pipeline
        Determines intent and routes to appropriate handler
        """
        
        # Add to conversation history
        self.context_manager.add_to_history({
            'role': 'user',
            'content': user_input,
            'type': input_type,
            'timestamp': datetime.now().isoformat()
        })
        
        # Detect intent
        intent_result = self.intent_detector.detect_intent(
            user_input,
            self.context_manager.get_recent_context()
        )
        
        intent_type = intent_result['intent']
        confidence = intent_result['confidence']
        entities = intent_result.get('entities', {})
        
        print(f"🎯 Intent detected: {intent_type} (confidence: {confidence:.2f})")
        
        # Route based on intent
        response = {
            'success': True,
            'intent': intent_type,
            'confidence': confidence,
            'input': user_input,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if intent_type == IntentType.CONVERSATION:
                response.update(self.handle_conversation(user_input))
                
            elif intent_type == IntentType.COMMAND:
                response.update(self.handle_command(user_input, entities))
                
            elif intent_type == IntentType.INFORMATION:
                response.update(self.handle_information_request(user_input, entities))
                
            elif intent_type == IntentType.TRANSCRIPTION:
                response.update(self.handle_transcription_request(user_input))
                
            elif intent_type == IntentType.UNKNOWN:
                # If providers are configured, try AI before falling back to the generic unknown handler
                if self.config.get('openrouter_api_key'):
                    ai_try = self.get_ai_response(user_input)
                    if isinstance(ai_try, str) and ai_try.startswith('PROVIDER_ERROR'):
                        response.update(self.handle_unknown(user_input))
                    else:
                        response.update({'response': ai_try})
                else:
                    response.update(self.handle_unknown(user_input))
                
        except Exception as e:
            response.update({
                'success': False,
                'error': str(e),
                'response': "I'm sorry, I encountered an error processing your request."
            })
        
        # Add assistant response to history
        if 'response' in response:
            self.context_manager.add_to_history({
                'role': 'assistant',
                'content': response['response'],
                'timestamp': datetime.now().isoformat()
            })
        
        return response
    
    def handle_conversation(self, user_input: str) -> Dict:
        """Handle casual conversation"""
        # Get conversation context
        conversation_context = self.context_manager.get_conversation_context()
        
        # Generate response based on context
        if "how are you" in user_input.lower():
            response = f"I'm functioning well, thank you for asking! How can I help you today, {self.user_name}?"
        elif "what's your name" in user_input.lower() or "who are you" in user_input.lower():
            response = "I'm your personal AI assistant. I'm here to help you with tasks, answer questions, and have conversations."
        elif "thank" in user_input.lower():
            response = "You're welcome! Is there anything else I can help you with?"
        elif "goodbye" in user_input.lower() or "bye" in user_input.lower():
            response = f"Goodbye, {self.user_name}! Have a wonderful day. Say my wake word when you need me again."
            self.is_active = False
        else:
            # Use AI for natural conversation if available
            if self.config.get('openrouter_api_key'):
                response = self.get_ai_response(user_input, conversation_context)
            else:
                response = f"I understand you're saying: '{user_input}'. I'm here to help with commands, information, or just to chat. What would you like to do?"
        
        return {'response': response}
    
    def handle_command(self, user_input: str, entities: Dict) -> Dict:
        """Handle command execution"""
        # Extract command from input
        command = user_input
        
        # Check if it's a system control command
        command_result = self.command_executor.execute_command(command, entities)
        
        if command_result['success']:
            response = command_result.get('message', f"Command executed: {command}")
        else:
            response = f"I couldn't execute that command. {command_result.get('error', 'Please try again.')}"
        
        return {
            'response': response,
            'command_result': command_result
        }
    
    def handle_information_request(self, user_input: str, entities: Dict) -> Dict:
        """Handle information requests"""
        lower = user_input.lower()

        # Local profile answers for personal background questions
        if 'ayesha' in lower or 'your' in lower or 'you' in lower:
            if 'education' in lower:
                response = f"📚 Ayesha's education is: {self.profile['education']}."
                return {'response': response}
            if any(k in lower for k in ['skill', 'skills', 'technical', 'program', 'web development']):
                response = f"🛠️ Ayesha's main technical skills are: {self.profile['technicalSkills']}."
                return {'response': response}
            if any(k in lower for k in ['name', 'who are you', 'intro', 'about you']):
                response = self.profile['intro']
                return {'response': response}
            if any(k in lower for k in ['background', 'experience', 'bio']):
                response = f"{self.profile['intro']} She studied {self.profile['education']} and specializes in {self.profile['technicalSkills']}."
                return {'response': response}

        # Explicit skills handling (local profile) to avoid relying on external AI
        if any(k in lower for k in ['skill', 'skills', 'technical', 'program', 'web development']):
            response = f"🛠️ My main technical skills are: {self.profile['technicalSkills']}."
            return {'response': response}

        # Check if it's a time/date request
        if any(word in lower for word in ['time', 'date', 'day']):
            now = datetime.now()
            if 'time' in lower:
                response = f"The current time is {now.strftime('%I:%M %p')}"
            elif 'date' in lower:
                response = f"Today is {now.strftime('%B %d, %Y')}"
            else:
                response = f"Today is {now.strftime('%B %d, %Y')} and the time is {now.strftime('%I:%M %p')}"
            return {'response': response}

        # Weather request (placeholder - would need API)
        if 'weather' in lower:
            return {'response': "I can provide weather information. Please configure a weather API key in the settings."}

        # News request
        if 'news' in lower:
            return {'response': "I can fetch news for you. Please configure a news API key in the settings."}

        # General information - use AI if available, but handle provider errors gracefully
        if self.config.get('openrouter_api_key'):
            ai_resp = self.get_ai_response(user_input, context="information")
            if isinstance(ai_resp, str) and ai_resp.startswith('PROVIDER_ERROR'):
                provider_msg = ai_resp.split(':', 1)[1].strip()
                response = f"{provider_msg} Using local profile: {self.profile['education']}. Skills: {self.profile['technicalSkills']}"
            else:
                response = ai_resp
        else:
            response = f"I'll help you find information about: {user_input}. For better results, consider adding an API key for enhanced capabilities."

        return {'response': response}
    
    def handle_transcription_request(self, user_input: str) -> Dict:
        """Handle transcription requests"""
        response = f"I've transcribed: '{user_input}'. Would you like me to do anything with this text?"
        return {'response': response}
    
    def handle_unknown(self, user_input: str) -> Dict:
        """Handle unknown intent"""
        response = f"I'm not sure how to help with that, {self.user_name}. Could you please rephrase or tell me what you'd like to do?"
        return {'response': response}
    
    def get_ai_response(self, user_input: str, context: Any = None) -> str:
        """Get response from AI model (OpenAI or local)"""
        try:
            # If OpenRouter key is present, use OpenRouter exclusively and do not fall back to OpenAI
            if self.config.get('openrouter_api_key'):
                try:
                    headers = {
                        'Authorization': f"Bearer {self.config['openrouter_api_key']}",
                        'Content-Type': 'application/json',
                        'HTTP-Referer': 'http://localhost:8000',
                        'X-Title': 'Personal Chatbot'
                    }
                    payload = {
                        'model': 'gpt-3.5-turbo',
                        'messages': [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": user_input}
                        ],
                        'max_tokens': 250,
                        'temperature': 0.7,
                    }
                    or_resp = httpx.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=15)
                    if or_resp.status_code == 200:
                        jr = or_resp.json()
                        try:
                            return jr['choices'][0]['message']['content'].strip()
                        except Exception:
                            return jr['choices'][0].get('text', str(jr))
                    else:
                        or_err = f"OpenRouter error: {or_resp.status_code} - {or_resp.text}"
                        print(or_err)
                        return f"PROVIDER_ERROR: {or_err}"
                except Exception as or_err:
                    or_err = f"OpenRouter request failed: {or_err}"
                    print(or_err)
                    return f"PROVIDER_ERROR: {or_err}"

            # If no OpenRouter key is configured, fall back to the local profile reply
            return f"I understand you're asking about: {user_input}. I'm here to help!"

        except Exception as e:
            print(f"AI response error: {e}")
            return {
    "response": "🤖 I'm not fully sure I understood that. Can you rephrase it?",
    "success": False
}
    def activate_wake_word_listener(self):
        """Listen for wake word in background"""
        def listener():
            while True:
                try:
                    # Listen for wake word
                    wake_word_detected = self.audio_processor.detect_wake_word(
                        self.config['wake_words']
                    )
                    
                    if wake_word_detected:
                        self.wake_word_detected = True
                        self.activate()
                        
                except Exception as e:
                    print(f"Wake word listener error: {e}")
                
                time.sleep(0.1)
        
        listener_thread = threading.Thread(target=listener, daemon=True)
        listener_thread.start()
    
    def activate(self):
        """Activate the assistant"""
        if not self.is_active:
            self.is_active = True
            greeting = f"Hello {self.user_name}! I'm listening. How can I help you?"
            self.audio_processor.speak(greeting, self.config['voice_settings'])
            self.context_manager.clear_session_context()
    
    def deactivate(self):
        """Deactivate the assistant"""
        self.is_active = False
        self.wake_word_detected = False
    
    def run_text_mode(self):
        """Run assistant in text-only mode"""
        print("\n" + "="*50)
        print("🤖 Personal AI Assistant - Text Mode")
        print("="*50)
        print("Type your commands or conversation. Type 'exit' to quit.")
        print("-"*50)
        
        self.is_active = True
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'goodbye']:
                    print(f"Assistant: Goodbye, {self.user_name}!")
                    break
                
                if user_input:
                    response = self.process_input(user_input, 'text')
                    print(f"Assistant: {response['response']}")
                    
            except KeyboardInterrupt:
                print(f"\nAssistant: Goodbye, {self.user_name}!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def run_voice_mode(self, module: str = None):
        """Run assistant in voice mode"""
        module_name = module or self.config['default_module']
        if module_name == 'voice_to_voice':
            if 'voice_to_voice' not in self.modules:
                print("Voice-to-Voice module not available in this deployment.")
                return
            print("🎤 Starting Voice-to-Voice mode...")
            voice_module = self.modules['voice_to_voice']
            if hasattr(voice_module, 'run'):
                voice_module.run(self.process_input, self.config['voice_settings'])
            elif hasattr(voice_module, 'run_conversation'):
                voice_module.run_conversation()
            else:
                raise AttributeError('voice_to_voice module does not implement run() or run_conversation()')
        elif module_name == 'voice_to_text':
            if 'voice_to_text' not in self.modules:
                print("Voice-to-Text module not available in this deployment.")
                return
            print("📝 Starting Voice-to-Text mode...")
            self.modules['voice_to_text'].run(
                self.config['voice_settings']
            )
        else:
            print("🎯 Starting Command Execution mode...")
            self.activate_wake_word_listener()
            print(f"Wake word activated. Say: {', '.join(self.config['wake_words'])}")
            
            # Keep the main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nAssistant shutting down...")
    
    def show_menu(self):
        """Display interactive menu"""
        print("\n" + "="*50)
        print("🤖 PERSONAL AI ASSISTANT - MAIN MENU")
        print("="*50)
        print("1. Voice-to-Voice Mode (Full conversation)")
        print("2. Voice-to-Text Mode (Dictation)")
        print("3. Command Execution Mode (Voice commands)")
        print("4. Text Mode (Type your requests)")
        print("5. Configure Settings")
        print("6. View User Profile")
        print("7. Exit")
        print("="*50)
    
    def configure_settings(self):
        """Configure assistant settings"""
        print("\n⚙️ CONFIGURATION MENU")
        print("1. Change user name")
        print("2. Configure wake words")
        print("3. Set OpenRouter API key")
        print("4. Voice settings")
        print("5. Back to main menu")
        
        choice = input("Select option: ")
        
        if choice == '1':
            new_name = input("Enter your name: ")
            self.user_preferences['name'] = new_name
            self.user_name = new_name
            self.save_user_preferences()
            print(f"✅ Name updated to: {new_name}")
        
        elif choice == '2':
            print("Current wake words:", ', '.join(self.config['wake_words']))
            new_words = input("Enter new wake words (comma-separated): ")
            self.config['wake_words'] = [w.strip() for w in new_words.split(',')]
            self.save_config()
            print(f"✅ Wake words updated")
        
        elif choice == '3':
            api_key = input("Enter OpenRouter API key: ")
            self.config['openrouter_api_key'] = api_key
            self.save_config()
            print("✅ API key saved")
        
        elif choice == '4':
            print("Voice settings:")
            rate = input(f"Speech rate (current: {self.config['voice_settings']['rate']}): ")
            if rate:
                self.config['voice_settings']['rate'] = int(rate)
            volume = input(f"Volume (current: {self.config['voice_settings']['volume']}): ")
            if volume:
                self.config['voice_settings']['volume'] = float(volume)
            self.save_config()
            print("✅ Voice settings updated")
    
    def save_config(self):
        """Save configuration to file"""
        with open("config/settings.json", 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def show_user_profile(self):
        """Display user profile information"""
        print("\n👤 USER PROFILE")
        print(f"Name: {self.user_preferences.get('name', 'Not set')}")
        print(f"Session ID: {self.current_session_id}")
        print(f"Frequent actions:")
        for action, count in self.user_preferences.get('frequent_actions', {}).items():
            print(f"  - {action}: {count} times")
        print(f"Total interactions: {len(self.context_manager.history)}")
    
    def start(self):
        """Start the assistant with menu"""
        while True:
            self.show_menu()
            choice = input("\nSelect option: ")
            
            if choice == '7':
                print(f"Goodbye, {self.user_name}! Have a great day!")
                break
            elif choice == '1':
                self.run_voice_mode('voice_to_voice')
            elif choice == '2':
                self.run_voice_mode('voice_to_text')
            elif choice == '3':
                self.run_voice_mode('command')
            elif choice == '4':
                self.run_text_mode()
            elif choice == '5':
                self.configure_settings()
            elif choice == '6':
                self.show_user_profile()
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    assistant = PersonalAIAssistant()
    assistant.start()