# modules/intent_detector.py
from enum import Enum
from typing import Dict, List, Any, Optional
import re

class IntentType(Enum):
    CONVERSATION = "conversation"
    COMMAND = "command"
    INFORMATION = "information"
    TRANSCRIPTION = "transcription"
    UNKNOWN = "unknown"

class IntentDetector:
    """
    Advanced intent detection using pattern matching and ML classification
    """
    
    def __init__(self):
        # Command patterns
        self.command_patterns = {
            'system_control': [
                r'open\s+(\w+)',
                r'close\s+(\w+)',
                r'launch\s+(\w+)',
                r'shutdown',
                r'restart',
                r'lock\s+(?:computer|system)',
                r'volume\s+(up|down|mute)',
                r'quit\s+(\w+)',
                r'exit\s+(\w+)'
            ],
            'web_action': [
                r'search\s+(?:for\s+)?(.+)',
                r'go\s+to\s+(\w+\.\w+)',
                r'open\s+website\s+(.+)',
                r'play\s+(?:video|music|song)\s+(.+)',
                r'check\s+weather',
                r'get\s+news',
                r'youtube\s+(.+)'
            ],
            'file_management': [
                r'create\s+folder\s+(.+)',
                r'delete\s+file\s+(.+)',
                r'open\s+file\s+(.+)',
                r'search\s+document\s+(.+)',
                r'find\s+file\s+(.+)'
            ],
            'productivity': [
                r'create\s+note\s+(.+)',
                r'take\s+note\s+(.+)',
                r'set\s+reminder\s+(.+)',
                r'remind\s+me\s+(.+)',
                r'add\s+task\s+(.+)',
                r'schedule\s+(.+)',
                r'make\s+appointment\s+(.+)'
            ]
        }
        
        # Information request patterns
        self.information_patterns = [
            r'what(?:\'s| is)\s+(.+)',
            r'tell\s+me\s+about\s+(.+)',
            r'explain\s+(.+)',
            r'how\s+(?:to|do|does)\s+(.+)',
            r'when\s+(?:is|was|will)\s+(.+)',
            r'where\s+(?:is|are)\s+(.+)',
            r'who\s+(?:is|are)\s+(.+)',
            # common possessive / direct forms: "what is ayesha's education" or "what's ayesha education"
            r'what(?:\'s| is)\s+(?:[\w\-]+\'s|[\w\-]+)\s+(education|skills|experience|hobbies|goal|projects)'
        ]
        
        # Conversation patterns
        self.conversation_patterns = [
            r'how\s+are\s+you',
            r'what(?:\'s| is)\s+your\s+name',
            r'who\s+are\s+you',
            r'hello|hi|hey',
            r'thank\s+you|thanks',
            r'good\s+(morning|afternoon|evening)',
            r'nice\s+to\s+meet\s+you'
        ]
        
        # Initialize ML classifier (placeholder)
        self.ml_classifier = None  # Would load a trained model
    
    def detect_intent(self, text: str, context: Optional[List[Dict]] = None) -> Dict:
        """
        Detect intent from user input with context awareness
        """
        text_lower = text.lower()
        
        # Check for conversation patterns first (highest priority for social interactions)
        if self.match_patterns(text_lower, self.conversation_patterns):
            return {
                'intent': IntentType.CONVERSATION,
                'confidence': 0.95,
                'entities': {}
            }
        
        # Check for commands
        command_result = self.detect_command(text_lower)
        if command_result['is_command']:
            return {
                'intent': IntentType.COMMAND,
                'confidence': command_result['confidence'],
                'entities': command_result.get('entities', {}),
                'command_type': command_result['command_type']
            }
        
        # Check for information requests
        info_result = self.detect_information_request(text_lower)
        if info_result['is_information']:
            return {
                'intent': IntentType.INFORMATION,
                'confidence': info_result['confidence'],
                'entities': info_result.get('entities', {})
            }
        
        # Check for transcription mode
        if any(word in text_lower for word in ['transcribe', 'dictate', 'write down']):
            return {
                'intent': IntentType.TRANSCRIPTION,
                'confidence': 0.85,
                'entities': {}
            }
        
        # Use ML classifier if available
        if self.ml_classifier:
            ml_intent = self.classify_with_ml(text)
            if ml_intent['confidence'] > 0.7:
                return ml_intent

        # Heuristic: map common personal-info keywords to INFORMATION
        personal_info_keywords = [
            'education', 'skill', 'skills', 'experience', 'projects', 'hobby', 'hobbies',
            'goal', 'certification', 'freelance', 'background', 'teach', 'teaching', 'degree'
        ]
        for keyword in personal_info_keywords:
            if keyword in text_lower:
                return {
                    'intent': IntentType.INFORMATION,
                    'confidence': 0.8,
                    'entities': {'topic': keyword}
                }
        
        # Default to unknown
        return {
            'intent': IntentType.UNKNOWN,
            'confidence': 0.5,
            'entities': {}
        }
    
    def detect_command(self, text: str) -> Dict:
        """
        Detect and classify commands
        """
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities = {}
                    if match.groups():
                        entities['target'] = match.group(1)
                    
                    return {
                        'is_command': True,
                        'command_type': command_type,
                        'confidence': 0.9,
                        'entities': entities
                    }
        
        # Check for simple commands without specific patterns
        simple_commands = ['open', 'close', 'launch', 'run', 'start', 'stop']
        words = text.split()
        if words and words[0] in simple_commands:
            return {
                'is_command': True,
                'command_type': 'system_control',
                'confidence': 0.7,
                'entities': {'action': words[0], 'target': ' '.join(words[1:]) if len(words) > 1 else ''}
            }
        
        return {'is_command': False, 'confidence': 0}
    
    def detect_information_request(self, text: str) -> Dict:
        """
        Detect information requests
        """
        for pattern in self.information_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'is_information': True,
                    'confidence': 0.85,
                    'entities': {'query': match.group(1) if match.groups() else text}
                }
        
        # Check for specific information keywords
        info_keywords = ['time', 'date', 'weather', 'news', 'fact']
        for keyword in info_keywords:
            if keyword in text:
                return {
                    'is_information': True,
                    'confidence': 0.75,
                    'entities': {'topic': keyword}
                }
        
        return {'is_information': False, 'confidence': 0}
    
    def match_patterns(self, text: str, patterns: List[str]) -> bool:
        """
        Check if text matches any pattern
        """
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def classify_with_ml(self, text: str) -> Dict:
        """
        Classify intent using machine learning
        Placeholder for actual ML model integration
        """
        # This would call a trained model
        # For now, return low confidence
        return {
            'intent': IntentType.UNKNOWN,
            'confidence': 0.5,
            'entities': {}
        }
    
    def extract_entities(self, text: str, intent_type: IntentType) -> Dict:
        """
        Extract entities based on intent type
        """
        entities = {}
        
        if intent_type == IntentType.COMMAND:
            # Extract command targets
            words = text.split()
            if len(words) > 1:
                entities['target'] = ' '.join(words[1:])
        
        elif intent_type == IntentType.INFORMATION:
            # Extract information topic
            info_markers = ['about', 'for', 'on']
            for marker in info_markers:
                if marker in text:
                    parts = text.split(marker, 1)
                    if len(parts) > 1:
                        entities['topic'] = parts[1].strip()
        
        return entities