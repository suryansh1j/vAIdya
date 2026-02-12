from faster_whisper import WhisperModel
import os
from pydub import AudioSegment
from pydub.utils import which

# Ensure ffmpeg is available in PATH
ffmpeg_path = which("ffmpeg")
if ffmpeg_path is None:
    print("[ERROR] ffmpeg not found. Please install it and ensure it's in the system PATH.")
    exit(1)

# Setup base directory relative to this script file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

audio_m4a_file = "Recording.m4a"
audio_wav_file = "Recording.wav"
audio_m4a_path = os.path.join(BASE_DIR, "audio", audio_m4a_file)
audio_wav_path = os.path.join(BASE_DIR, "audio", audio_wav_file)
transcript_path = os.path.join(BASE_DIR, "transcripts", "full_transcript.txt")
os.makedirs(os.path.dirname(transcript_path), exist_ok=True)

# Always convert M4A to WAV and overwrite existing WAV file
print(f"[INFO] Converting {audio_m4a_file} to WAV format (overwrite)...")
sound = AudioSegment.from_file(audio_m4a_path, format="m4a")
sound.export(audio_wav_path, format="wav")
print(f"[INFO] Converted audio saved as {audio_wav_path}")

# Load audio for chunked processing
audio = AudioSegment.from_file(audio_wav_path)
duration_ms = len(audio)
chunk_length_ms = 20 * 1000  # 20 seconds chunk size

# Setup Whisper transcription model
device = "cpu"
compute_type = "int8"
model_name = "Systran/faster-distil-whisper-large-v2"
model = WhisperModel(model_name, device=device, compute_type=compute_type)

full_transcript = ""

# Process audio chunks sequentially
for start_ms in range(0, duration_ms, chunk_length_ms):
    end_ms = min(start_ms + chunk_length_ms, duration_ms)
    chunk = audio[start_ms:end_ms]

    # Export chunk to temporary file
    chunk_path = os.path.join(BASE_DIR, "audio", "temp_chunk.wav")
    chunk.export(chunk_path, format="wav")

    print(f"[INFO] Transcribing audio chunk {start_ms//1000}s to {end_ms//1000}s...")
    try:
        segments, _ = model.transcribe(chunk_path, language="en")
        chunk_text = ''.join([seg.text for seg in segments])
        full_transcript += chunk_text + " "
    except Exception as e:
        print(f"[ERROR] Failed to transcribe chunk {start_ms//1000}s to {end_ms//1000}s: {e}")
        continue  # Skip this chunk and proceed with the next

# Write full concatenated transcript to file
with open(transcript_path, "w", encoding="utf-8") as tf:
    tf.write(full_transcript.strip())

print(f"[INFO] Full transcript saved to: {transcript_path}")
print("[INFO] Transcript output:")
print(full_transcript)

# Cleanup temp wav files
try:
    os.remove(audio_wav_path)
    print(f"[INFO] Removed WAV file: {audio_wav_path}")
except Exception as e:
    print(f"[WARN] Failed to remove WAV file: {e}")

try:
    os.remove(chunk_path)
    print(f"[INFO] Removed temp chunk file: {chunk_path}")
except Exception as e:
    print(f"[WARN] Failed to remove temp chunk file: {e}")
