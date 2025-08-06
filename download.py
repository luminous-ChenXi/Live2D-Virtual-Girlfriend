from sentence_transformers import SentenceTransformer
from speechbrain.inference import SpeakerRecognition

SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")