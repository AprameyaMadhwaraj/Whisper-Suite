import pyaudio
import wave
import tempfile
import threading
import queue
import whisperx

# Create a queue to hold audio data
audio_queue = queue.Queue()

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 8  # Adjust as needed
compute_type = 'float16'  # float16 for GPU, int 8 for cpu
device = 'cuda'  # cuda for GPU else cpu

audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

print("\nListening...\n")


def process_audio():
    while True:
        # Get the next audio data from the queue
        frames = audio_queue.get()

        # Save recorded audio to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
            wf = wave.open(tmp_audio_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            # Send audio file to Whisper API for transcription
            try:
                model = whisperx.load_model('small', device, compute_type=compute_type, language='en')
                audio_in = whisperx.load_audio(tmp_audio_file.name)

                result = model.transcribe(audio_in)

                if 'segments' in result and result['segments']:
                    transcript = result['segments'][0]['text']
                    print('\n', transcript, '\n')
                else:
                    print('\nNo audio recognized\n')

            except Exception as e:
                print(f"Unexpected error: {e}")


# Start a new thread to process audio data
threading.Thread(target=process_audio, daemon=True).start()

try:
    while True:
        # Start recording
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        # Add the recorded audio data to the queue
        audio_queue.put(frames.copy())  # Use a copy to avoid modifying the list in the queue

except KeyboardInterrupt:
    print("\nRecording stopped.")

finally:
    # Clean up
    stream.stop_stream()
    stream.close()
    audio.terminate()
