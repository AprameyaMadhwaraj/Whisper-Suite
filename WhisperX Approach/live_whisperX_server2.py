import asyncio
import websockets
import whisperx
import pyaudio
import tempfile
import base64
import wave
from text_correction import *  # noqa: F403
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

local_directory_name = "D:/Personal/Aikenist/Server_audio"
model = whisperx.load_model('small', device='cuda', compute_type='float16', language='en')

audio = pyaudio.PyAudio()

async def receive_and_write_audio(websocket):
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

                # For Saving Audio
                current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
                filename = os.path.join(local_directory_name,  f"{os.path.basename(tmp_audio_file_path)}_{current_time}.wav")
                shutil.copy(tmp_audio_file_path, filename)

                # Schedule the transcribing coroutine
                asyncio.create_task(transcribe_and_send(websocket, tmp_audio_file_path))

    except websockets.exceptions.ConnectionClosed:
        print("\n \t CLIENT DISCONNECTED.")
    finally:
        # Clean up the temporary WAV file
        try:
            if tmp_audio_file_path is not None:
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

            # Post processing Transcript        
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
