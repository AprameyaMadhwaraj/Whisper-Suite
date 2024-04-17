import asyncio
import websockets
import pyaudio
import base64
import os
import datetime
#import shutil
import wave

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 6

local_directory_name = "D:/Personal/Aikenist/Client_audio"

async def record_and_transmit():
    async with websockets.connect("ws://172.24.86.1:8765") as websocket:
    #async with websockets.connect("ws://192.168.0.133:9090", ping_interval=None) as websocket:
        try:
            audio = pyaudio.PyAudio()

            stream = audio.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)

            print("\nListening... Press Ctrl+C to stop.")

            while True:
                frames = []

                for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK)
                    frames.append(data)

                # For Saving Audio
                current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
                filename = os.path.join(local_directory_name, f"audio_{current_time}.wav")

                # Save audio frames to a new file
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(audio.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))

                
                # Convert binary audio data to base64
                audio_data = base64.b64encode(b''.join(frames)).decode('utf-8')

                # Send base64 encoded audio data to the server
                await websocket.send(audio_data)

                # Receive transcription from the server
                response = await websocket.recv()
                print(response, end='', flush=True)  # Flush the output buffer after each print

        except KeyboardInterrupt:
            print("\n \t RECORDING STOPPED.")
        finally:
            # Clean up
            stream.stop_stream()
            stream.close()
            audio.terminate()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(record_and_transmit())
    except KeyboardInterrupt:
        print("\n \t CLIENT STOPPED.")

    
