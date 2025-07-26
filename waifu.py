import openai
import speech_recognition as sr
from gtts import gTTS
from elevenlabs.client import ElevenLabs
from elevenlabs import play, voices
import sounddevice as sd
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
                   personality_file=None, tts_service=None, output_device=None,
                   tts_voice=None, tts_model=None) -> None:
        load_dotenv()
        self.update_user_input(user_input_service=user_input_service, stt_duration=stt_duration)
        self.mic = sr.Microphone(device_index=mic_index)
        self.recogniser = sr.Recognizer()
        openai.api_key = getenv("OPENAI_API_KEY")
        self.update_chatbot(service=chatbot_service, model=chatbot_model,
                            temperature=chatbot_temperature, personality_file=personality_file)
        self.__load_chatbot_data()
        print("This is the output device:", output_device)
        output_device = 4
        self.update_tts(service=tts_service, output_device=output_device,
                        voice=tts_voice, model=tts_model)

    def update_user_input(self, user_input_service='whisper', stt_duration=0.5) -> None:
        self.user_input_service = user_input_service or self.user_input_service or 'whisper'
        self.stt_duration = stt_duration or self.stt_duration or 0.5

    def update_chatbot(self, service='openai', model='gpt-3.5-turbo',
                       temperature=0.5, personality_file='personality.txt') -> None:
        self.chatbot_service = service or self.chatbot_service or 'openai'
        self.chatbot_model = model or self.chatbot_model or 'gpt-3.5-turbo'
        self.chatbot_temperature = temperature or self.chatbot_temperature or 0.5
        self.chatbot_personality_file = personality_file or self.chatbot_personality_file or 'personality.txt'

    def update_tts(self, service='google', output_device=None, voice=None, model=None) -> None:
        self.tts_service = service or self.tts_service or 'google'
        self.tts_voice = voice or self.tts_voice or 'Elli'
        self.tts_model = model or self.tts_model or 'eleven_monolingual_v1'
        if self.tts_service == 'elevenlabs':
            self.client = ElevenLabs(api_key=getenv("ELEVENLABS_API_KEY"))
        if output_device is not None:
            sd.check_output_settings(output_device)
            sd.default.samplerate = 44100
            sd.default.device = output_device

    def get_audio_devices(self):
        return sd.query_devices()

    def get_user_input(self, service=None, stt_duration=None) -> str:
        service = service or self.user_input_service
        stt_duration = stt_duration or self.stt_duration
        if service in ['whisper', 'google']:
            return self.__recognise_speech(service, duration=stt_duration)
        elif service == 'console':
            return self.__get_text_input(service)
        else:
            raise ValueError(f"{service} service isn't supported.")

    def get_chatbot_response(self, prompt, service=None, model=None, temperature=None) -> str:
        service = service or self.chatbot_service
        model = model or self.chatbot_model
        temperature = temperature or self.chatbot_temperature
        if service == 'openai':
            return self.__get_openai_response(prompt, model=model, temperature=temperature)
        elif service == 'test':
            return "This is a test answer from Waifu. Nya kawaii, senpai!"
        else:
            raise ValueError(f"{service} service isn't supported.")

    def tts_say(self, text, service=None, voice=None, model=None) -> None:
        service = service or self.tts_service
        voice = voice or self.tts_voice
        model = model or self.tts_model
        if service == 'google':
            gTTS(text=text, lang='en', slow=False, lang_check=False).save('output.mp3')
        elif service == 'elevenlabs':
            self.__elevenlabs_generate(text=text, voice=voice, model=model)
        elif service == 'console':
            print('\n\33[7m' + "Waifu:" + '\33[0m' + f' {text}')
            return
        else:
            raise ValueError(f"{service} service isn't supported.")
        data, fs = sf.read('output.mp3')
        sd.play(data, fs)
        sd.wait()

    def conversation_cycle(self) -> dict:
        user_input = self.get_user_input()
        response = self.get_chatbot_response(user_input)
        self.tts_say(response)
        return dict(user=user_input, assistant=response)

    def __get_openai_response(self, prompt, model, temperature) -> str:
        self.__add_message('user', prompt)
        messages = self.context + self.message_history
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        reply = response.choices[0].message["content"]
        self.__add_message('assistant', reply)
        self.__update_message_history()
        return reply

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

    def __get_text_input(self, service) -> str:
        if service == 'console':
            return input('\n\33[42m' + "User:" + '\33[0m' + " ")
        return ""

    def __elevenlabs_generate(self, text, voice, model, filename='output.mp3'):
        audio = self.client.generate(
            text=text,
            voice=voice,
            model=model
        )
        with open(filename, "wb") as f:
            f.write(audio)
        play(audio)

    def __recognise_speech(self, service, duration) -> str:
        with self.mic as source:
            print('(Start listening)')
            self.recogniser.adjust_for_ambient_noise(source, duration=duration)
            audio = self.recogniser.listen(source)
            print('(Stop listening)')
        try:
            if service == 'whisper':
                return self.__whisper_sr(audio)
            elif service == 'google':
                return self.recogniser.recognize_google(audio)
        except Exception as e:
            print(f"Exception: {e}")
        return ""

    def __whisper_sr(self, audio) -> str:
        with open('speech.wav', 'wb') as f:
            f.write(audio.get_wav_data())
        audio_file = open('speech.wav', 'rb')
        transcript = openai.Audio.transcribe(model="whisper-1", file=audio_file)
        return transcript['text']

def main():
    w = Waifu()
    w.initialise(user_input_service='console', chatbot_service='openai',
                 tts_service='google', output_device=8)
    w.conversation_cycle()

if __name__ == "__main__":
    main()
