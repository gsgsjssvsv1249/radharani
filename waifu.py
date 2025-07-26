import openai
import speech_recognition as sr
from gtts import gTTS
from elevenlabs.client import ElevenLabs
from elevenlabs import play, voices
import soundfile as sf
from dotenv import load_dotenv
from os import getenv, path
from json import load, dump, JSONDecodeError

class Waifu:
    def __init__(self) -> None:
        self.mic = None
        self.recogniser = None
        self.user_input_service = None
        self.stt_duration = None
        self.chatbot_service = None
        self.chatbot_model = None
        self.chatbot_temperature = None
        self.chatbot_personality_file = None
        self.message_history = []
        self.context = []
        self.tts_service = None
        self.tts_voice = None
        self.tts_model = None
        self.client = None

    def initialise(self, user_input_service=None, stt_duration=None, mic_index=None,
                   chatbot_service=None, chatbot_model=None, chatbot_temperature=None,
                   personality_file=None, tts_service=None, tts_voice=None, tts_model=None) -> None:
        load_dotenv()
        self.update_user_input(user_input_service=user_input_service, stt_duration=stt_duration)
        self.mic = sr.Microphone(device_index=mic_index)
        self.recogniser = sr.Recognizer()
        openai.api_key = getenv("OPENAI_API_KEY")
        self.update_chatbot(service=chatbot_service, model=chatbot_model,
                            temperature=chatbot_temperature, personality_file=personality_file)
        self.__load_chatbot_data()
        self.update_tts(service=tts_service, voice=tts_voice, model=tts_model)

    def update_user_input(self, user_input_service='whisper', stt_duration=0.5) -> None:
        self.user_input_service = user_input_service or 'whisper'
        self.stt_duration = stt_duration or 0.5

    def update_chatbot(self, service='openai', model='gpt-3.5-turbo',
                       temperature=0.5, personality_file='personality.txt') -> None:
        self.chatbot_service = service or 'openai'
        self.chatbot_model = model or 'gpt-3.5-turbo'
        self.chatbot_temperature = temperature or 0.5
        self.chatbot_personality_file = personality_file or 'personality.txt'

    def update_tts(self, service='google', voice=None, model=None) -> None:
        self.tts_service = service or 'google'
        self.tts_voice = voice or 'Elli'
        self.tts_model = model or 'eleven_monolingual_v1'
        if self.tts_service == 'elevenlabs':
            self.client = ElevenLabs(api_key=getenv("ELEVENLABS_API_KEY"))

    def get_user_input(self) -> str:
        if self.user_input_service == 'console':
            return input('\n\33[42m' + "User:" + '\33[0m' + " ")
        else:
            with self.mic as source:
                print('(Listening...)')
                self.recogniser.adjust_for_ambient_noise(source, duration=self.stt_duration)
                audio = self.recogniser.listen(source)
                print('(Done)')
            try:
                if self.user_input_service == 'google':
                    return self.recogniser.recognize_google(audio)
                elif self.user_input_service == 'whisper':
                    with open('speech.wav', 'wb') as f:
                        f.write(audio.get_wav_data())
                    audio_file = open('speech.wav', 'rb')
                    transcript = openai.Audio.transcribe(model="whisper-1", file=audio_file)
                    return transcript['text']
            except Exception as e:
                print(f"Error: {e}")
            return ""

    def get_chatbot_response(self, prompt) -> str:
        self.__add_message('user', prompt)
        messages = self.context + self.message_history
        response = openai.ChatCompletion.create(
            model=self.chatbot_model,
            messages=messages,
            temperature=self.chatbot_temperature,
        )
        reply = response.choices[0].message["content"]
        self.__add_message('assistant', reply)
        self.__update_message_history()
        return reply

    def tts_say(self, text) -> None:
        if self.tts_service == 'google':
            gTTS(text=text, lang='en', slow=False, lang_check=False).save('output.mp3')
        elif self.tts_service == 'elevenlabs':
            self.__elevenlabs_generate(text=text, voice=self.tts_voice, model=self.tts_model)
        elif self.tts_service == 'console':
            print('\n\33[7m' + "Waifu:" + '\33[0m' + f' {text}')
        else:
            raise ValueError(f"{self.tts_service} is not supported.")
        # Output.mp3 is ready to be served/downloaded

    def __elevenlabs_generate(self, text, voice, model, filename='output.mp3'):
        audio = self.client.generate(
            text=text,
            voice=voice,
            model=model
        )
        with open(filename, "wb") as f:
            f.write(audio)

    def conversation_cycle(self) -> dict:
        user_input = self.get_user_input()
        response = self.get_chatbot_response(user_input)
        self.tts_say(response)
        return dict(user=user_input, assistant=response)

    def __add_message(self, role, content) -> None:
        self.message_history.append({'role': role, 'content': content})

    def __load_chatbot_data(self, file_name=None) -> None:
        file_name = file_name or self.chatbot_personality_file
        with open(file_name, 'r') as f:
            personality = f.read()
        self.context = [{'role': 'system', 'content': personality}]
        if path.isfile('./message_history.txt'):
            with open('message_history.txt', 'r') as f:
                try:
                    self.message_history = load(f)
                except JSONDecodeError:
                    pass

    def __update_message_history(self) -> None:
        with open('message_history.txt', 'w') as f:
            dump(self.message_history, f)

def main():
    waifu = Waifu()
    waifu.initialise(user_input_service='console', chatbot_service='openai',
                     tts_service='google')
    waifu.conversation_cycle()

if __name__ == "__main__":
    main()
