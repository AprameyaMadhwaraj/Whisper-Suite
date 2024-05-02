import asyncio
import time

import websockets
import pyaudio
import base64

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 8

async def send_audio_data(websocket):
    try:
        audio = pyaudio.PyAudio()

        stream = audio.open(format=FORMAT,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        print("\nListening... Press Ctrl+C to stop.")

        while True:
            frames = []
            print("Recording...")
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow = False)
                frames.append(data)

            # Convert binary audio data to base64
            audio_data = base64.b64encode(b''.join(frames)).decode('utf-8')

            # Send base64 encoded audio data to the server
            await websocket.send(audio_data)

            response = await websocket.recv()
            print("Received response:", response, flush=True)

    except KeyboardInterrupt:
        print("\nSending audio data stopped.")
    finally:
        # Clean up
        stream.stop_stream()
        stream.close()
        audio.terminate()

async def main():
    async with websockets.connect("ws://localhost:8765") as websocket:
        # Start sending audio data and receiving responses concurrently
        await asyncio.gather(send_audio_data(websocket))

if __name__ == "__main__":
    asyncio.run(main())
