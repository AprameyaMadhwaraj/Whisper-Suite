import asyncio
import websockets
import pyaudio
import base64
import os
import datetime
import wave

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 6

local_directory_name = "D:/Personal/Aikenist/Client_audio"
audio = pyaudio.PyAudio()

async def record_audio(queue):
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    
    print("\n \t Listening... Press Ctrl+C to stop.")

    try:
        while True:
            frames = []
            for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)
            await queue.put(frames)
    except Exception as e:
        print("Error while recording audio:", e)
    finally:
        stream.stop_stream()
        stream.close()

async def send_audio(queue):
    async with websockets.connect("ws://localhost:8765") as websocket:
        try:
            while True:
                frames = await queue.get()
                current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = os.path.join(local_directory_name, f"audio_{current_time}.wav")

                # Save audio frames to a new file
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(audio.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))

                audio_data = base64.b64encode(b''.join(frames)).decode('utf-8')
                await websocket.send(audio_data)

                # Receive transcription from the server
                response = await websocket.recv()
                print(response, end='', flush=True)  # Flush the output buffer after each print
        except websockets.exceptions.ConnectionClosedError:
            print("\n \t Connection to server closed.")
        except Exception as e:
            print("Error while sending audio:", e)
        finally:
            await websocket.close()

async def main():
    queue = asyncio.Queue()
    asyncio.create_task(record_audio(queue))
    await send_audio(queue)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n \t CLIENT STOPPED.")
