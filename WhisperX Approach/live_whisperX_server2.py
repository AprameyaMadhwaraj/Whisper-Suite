import asyncio
import websockets
import whisperx
import pyaudio
import tempfile
import base64
import wave
from text_correction_v2 import *  # noqa: F403
import re
import os
import datetime
import shutil

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 10

#local_directory_name = "ENTER/YOUR/PATH"
model = whisperx.load_model('small', device='cuda', compute_type='float16', language='en')
'''Bad Perfomance'''
# model = whisperx.load_model('medium', device='cpu', compute_type='float32', language='en') # bad accuracy, disconnects from client
# model = whisperx.load_model('distil-small', device='cpu', compute_type='float32', language='en') very low accuracy, slow
# model = whisperx.load_model('distil-medium.en', device='cpu', compute_type='float32', language='en') low accuracy, slow
# model = whisperx.load_model('distil-large-v2', device='cpu', compute_type='float32', language='en') # low accuracy, very slow, disconnects from client

'''Good Performance'''
# model = whisperx.load_model('distil-medium.en', device='cuda', compute_type='float16', language='en')
# model = whisperx.load_model('large-v2', device='cuda', compute_type='int8', language='en')
# model = whisperx.load_model('small', device='cpu', compute_type='int8', language='en') # missing segments, slow
# model = whisperx.load_model('whisper-medium-int8-dynamic', device='cpu', compute_type='int8', language='en')



audio = pyaudio.PyAudio()

async def receive_and_write_audio(websocket):
    tmp_audio_file_path = None  # Define the variable at the beginning of the function
    try:
        while True:
            # Receive base64 encoded audio data from the client
            audio_data_base64 = await websocket.recv()

            # Decode base64
            audio_data = base64.b64decode(audio_data_base64)

            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
                tmp_audio_file_path = tmp_audio_file.name

                # Write audio frames to the WAV file
                with wave.open(tmp_audio_file_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(audio.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(audio_data)

                # Schedule the transcribing coroutine
                asyncio.create_task(transcribe_and_send(websocket, tmp_audio_file_path))

    except websockets.exceptions.ConnectionClosed:
        print("\n \t CLIENT DISCONNECTED.")
    finally:
        # Clean up the temporary WAV file
        if tmp_audio_file_path and os.path.exists(tmp_audio_file_path):
            try:
                os.remove(tmp_audio_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary WAV file: {e}")

async def transcribe_and_send(websocket, tmp_audio_file_path):
    try:
        # Transcribe audio using Whisper
        audio_in = whisperx.load_audio(tmp_audio_file_path)
        result = model.transcribe(audio_in)

        # For Speech
        if 'segments' in result and result['segments']:
            transcript = result['segments'][0]['text']
            #print(trascript)

            # Post processing Transcript - **OPTIONAL        
            text_ = transcript.strip()
            text_before = text_
            text_after = re.sub(r'\b(\w+)\.(?=\s|$)', r'\1', text_before)
            text_lower = text_after.lower()
            text_ = convert_measurement(text_lower)  # noqa: F405
            print(text_)

            # Send transcription back to the Client
            await websocket.send(text_)

        # For Silence
        else:
            await websocket.send('')

    except Exception as e:
        print(f"Error in transcription: {e}")
        await websocket.send('Error in transcription')

if __name__ == "__main__":
    start_server = websockets.serve(receive_and_write_audio, "localhost", 8765)

    print("\n \t SERVER IS READY AND LISTENING ON ws://localhost:8765")

    try:
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print("\n \t SERVER STOPPED.")
    finally:
        # Clean up resources
        audio.terminate()
