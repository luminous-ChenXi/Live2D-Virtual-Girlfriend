import re
import io
import wave
import time
import base64
import ctypes
import pyaudio
import pyautogui
import soundfile as sf
import threading
import numpy as np
import webrtcvad
import collections
from collections import deque
from init import Global

class RealTimeVAD:
    def __init__(self, aggressiveness=3, sample_rate=16000):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration = 30  # ms
        self.frame_length = int(sample_rate * self.frame_duration / 1000)
        self.is_speaking = False
        self.speech_buffer = collections.deque(maxlen=10)
        
    def is_speech_frame(self, frame_data):
        if len(frame_data) == self.frame_length * 2:  # 16bit
            return self.vad.is_speech(frame_data, self.sample_rate)
        return False
    
    def process_frame(self, frame_data):
        is_speech = self.is_speech_frame(frame_data)
        self.speech_buffer.append(is_speech)
        
        speech_ratio = sum(self.speech_buffer) / len(self.speech_buffer)
        
        if not self.is_speaking and speech_ratio > 0.5:
            self.is_speaking = True
            return "speech_start"
        elif self.is_speaking and speech_ratio < 0.3:
            self.is_speaking = False
            return "speech_end"
        elif self.is_speaking:
            return "speech_continue"
        else:
            return "silence"

def read_record_sound(path):
    data, rate = sf.read(path, dtype='float32')
    channels = data.shape[1] if len(data.shape) > 1 else 1
    width = 2

    if data.dtype != np.int16:
        data_int16 = (data * 32767).clip(-32768, 32767).astype(np.int16)
        byte_data = data_int16.tobytes()
    else:
        byte_data = data.tobytes()

    record_params = {
        'rate': rate,
        'channels': channels,
        'width': width,
        'data': byte_data
    }

    return record_params

def play_record_sound(record_params):
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=p.get_format_from_width(record_params['width']),
            channels=record_params['channels'],
            rate=record_params['rate'],
            output=True
        )
        stream.write(record_params['data'])
        stream.stop_stream()
        stream.close()
    finally:
        p.terminate()

def terminate_thread(thread):
    if not thread.is_alive():
        return
    
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)

def capture_screen():
    screenshot = pyautogui.screenshot()
    buffered = io.BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def speech_recognition(send_audio_text):
    CHUNK = int(16000 * 0.03) # 30ms
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    PRE_BUFFER_SECONDS = 0.5
    PRE_BUFFER_SIZE = int(RATE / CHUNK * PRE_BUFFER_SECONDS)
    vad_processor = RealTimeVAD(aggressiveness=Global.aggressiveness)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                   channels=CHANNELS,
                   rate=RATE,
                   input=True,
                   frames_per_buffer=CHUNK)
    
    thread= None
    while True:
        frames = []
        has_speech = False
        pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)

        while True:
            data = stream.read(CHUNK)
            vad_result = vad_processor.process_frame(data)

            if vad_result == "speech_start" or vad_result == "speech_continue":
                if not has_speech:
                    print("检测到语音开始")
                    frames.extend(pre_buffer)
                print(".", end="", flush=True)
                has_speech = True
                frames.append(data)
            
            elif has_speech and vad_result == "silence":
                break

            pre_buffer.append(data)
            
        if has_speech:
            wf = wave.open('voice.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            if Global.your_voice:
                print("\n语音结束")
                t = time.time()
                score = Global.speaker_verifier.verify_speaker(Global.your_voice, 'voice.wav')
                print(f'语音相似度(耗时: {time.time()-t:.2f}s):', score)
            else:
                score = 1

            t = time.time()
            if score > Global.verifier_threshold:
                result = Global.sense_voice.infer()
                if result:
                    print(f"识别结果(耗时: {time.time()-t:.2f}s): {result}")
                    text = re.sub(r'<(.*?)>', '', result, flags=re.DOTALL)
                    if len(text) > 1 and text != 'ok':
                        for hot_word, words in Global.hot_word.items():
                            for word in words:
                                text = text.replace(word, hot_word)

                        if Global.appearance_animator.flag == 1:
                            if Global.exist:
                                for i in Global.character['end_word']:
                                    if i in text:
                                        Global.sign1 = True
                                        break
                            else:
                                for i in Global.character['wake_word']:
                                    if i in text:
                                        Global.appearance_animator.reset(1)
                                        break
                        
                            if Global.exist:
                                if Global.func_queue1.t:
                                    for t0 in Global.func_queue1.t:
                                        terminate_thread(t0)
                                    Global.func_queue1.__init__()
                                if Global.audio_queue.q:
                                    Global.audio_queue.q = {}
                                if thread:
                                    terminate_thread(thread)
                                    thread = None
                                
                                img = None
                                for i in Global.shot_word:
                                    if i in text:
                                        img = capture_screen()
                                        break
                                thread = threading.Thread(target=send_audio_text, args=(result, img))
                                thread.start()
                else:
                    print(f"识别失败(耗时: {time.time()-t:.2f}s)")