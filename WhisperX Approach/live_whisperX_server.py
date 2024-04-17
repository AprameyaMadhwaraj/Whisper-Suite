import asyncio
import websockets
import whisperx
import pyaudio
import tempfile
import base64
import wave
from text_correction import *  # This is a local import, skip if not needed
import re
import os


# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 6

#local_directory_name = "D:/Personal/Aikenist/Server_audio"
model = whisperx.load_model('small', device='cuda', compute_type='float16', language='en')

audio = pyaudio.PyAudio()

async def process_audio(websocket, path):
    tmp_audio_file_path = None  # Initialize the variable

    try:
        while True:
            # Receive base64 encoded audio data from the client
            audio_data_base64 = await websocket.recv()

            # Decode base64 and write to a temporary WAV file with adaptive header
            audio_data = base64.b64decode(audio_data_base64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
                tmp_audio_file_path = tmp_audio_file.name

                # Write adaptive WAV header and audio frames
                with wave.open(tmp_audio_file_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(audio.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(audio_data)
          
            # Transcribe audio using Whisper
            try:
                #model = whisperx.load_model('small', device='cuda', compute_type='float16', language='en')
                audio_in = whisperx.load_audio(tmp_audio_file_path)
                result = model.transcribe(audio_in)

                # For Speech
                if 'segments' in result and result['segments']:
                    transcript = result['segments'][0]['text']
                    #print(transcript)
                    
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

    except websockets.exceptions.ConnectionClosed:
        print("\n \t CLIENT DISCONNECTED.")
    finally:
        # Clean up the temporary WAV file
        try:
            if tmp_audio_file_path is not None:
                os.remove(tmp_audio_file_path)

        except Exception as e:
            print(f"Error cleaning up temporary WAV file: {e}")


if __name__ == "__main__":
    #start_server = websockets.serve(process_audio, "localhost", 8765)
    start_server = websockets.serve(process_audio, "0.0.0.0", 8765)
    print("\n \t SERVER IS READY AND LISTENING ON ws://:8765")

    try:
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print("\n \t SERVER STOPPED.")
    finally:
        # Clean up resources
        audio.terminate()
