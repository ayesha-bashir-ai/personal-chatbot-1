class AudioProcessor:
    def __init__(self):
        pass

    def speak(self, text, voice_settings=None):
        print(f"[tts] {text}")

    def detect_wake_word(self, wake_words):
        # Placeholder always false in stub
        return False
