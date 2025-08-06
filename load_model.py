import re
import os
import torch
import torchaudio
from init import Global
from graph_rag import GraphRAGMemory
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from concurrent.futures import ThreadPoolExecutor
from speechbrain.inference import SpeakerRecognition

device = Global.device

class SpeakerVerification:
    def __init__(self):
        self.verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": device}
        )
        
        self._warmup()
    
    def _warmup(self):
        dummy_signal = torch.randn(1, 16000).to(device)
        self.verification.encode_batch(dummy_signal)
    
    def verify_speaker(self, audio_file1, audio_file2):
        signal1, _ = torchaudio.load(audio_file1)
        signal2, _ = torchaudio.load(audio_file2)
        
        if device == "cuda":
            signal1 = signal1.to(device)
            signal2 = signal2.to(device)
        
        score, _ = self.verification.verify_batch(signal1, signal2)
        
        return score.item()

class SenseVoice:
    def __init__(self):
        self.model = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/SenseVoiceSmall',
            model_revision="master",
            device=device
        )

        self._warmup()
    
    def _warmup(self):
        if os.path.exists('voice.wav'):
            self.infer()

    def infer(self, voice_path='voice.wav'):
        result = self.model(voice_path)
        pattern = r"<\|(.+?)\|><\|(.+?)\|><\|(.+?)\|><\|(.+?)\|>(.+)"
        match = re.match(pattern, result[0]['text'])
        if match:
            language, emotion, audio_type, itn, text = match.groups()
            text = f"<{emotion}>{text}"
        else:
            text = ''
        return text

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [
        executor.submit(lambda: setattr(Global, 'sense_voice', SenseVoice())),
        executor.submit(lambda: setattr(Global, 'speaker_verifier', SpeakerVerification())),
        executor.submit(lambda: setattr(Global, 'memory', GraphRAGMemory()))
    ]
    
    for future in futures:
        future.result()