from module1_voice_to_voice import VoiceToVoiceModule as CoreVoiceToVoiceModule

class VoiceToVoiceModule(CoreVoiceToVoiceModule):
    def run(self, process_input_cb=None, voice_settings=None):
        # run_conversation uses internal logic
        self.run_conversation()
