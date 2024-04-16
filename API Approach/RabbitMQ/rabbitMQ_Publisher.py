import pika #type:ignore
import pyaudio
import wave
import tempfile
import requests
import threading
#from concurrent.futures import ThreadPoolExecutor
import queue
from openai import OpenAI
from dotenv import load_dotenv
#import datetime

load_dotenv()
client = OpenAI()

# RabbitMQ setup
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Create a queue to hold audio data
audio_queue = queue.Queue()

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 10  # Adjust as needed

audio = pyaudio.PyAudio()


stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

print("\n...LISTENING...\n")

#print(f"Audio Received Time: {datetime.datetime.now().strftime('%H:%M:%S')}\n",flush = True)

# Change as needed
system_prompt = ''' correct spelling mistakes. Don't print commas after pause. 
                    Read next line and make sure the text that follows will be in the next line. 
                    Also if the speaker says colon, print the symbol ':' in place of the word. 
                    do not print anything unnecessary if there is silence. be very quick and accurate.
                    do not print the segments in the next line, unless clearly specified as 'next line' 
                    even if there are long pauses in the speech, add them to the same line as the previous
                    transcript, unless clearly specified as 'next line' 
                    '''

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
            with open(tmp_audio_file.name, 'rb') as audio_file:
                try:
                    transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file, 
                    response_format="text",
                    temperature=0,
                    language='en'
                    )
                    
                    #print(f"Whisper Transcipt Time: {datetime.datetime.now().strftime('%H:%M:%S')}\n",flush = True)  
                    
                    response = client.chat.completions.create(
                        model="gpt-4-0125-preview",
                        temperature=0,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": transcript
                            } # type: ignore
                        ]
                    )
                    
                    
                    generated_text = response.choices[0].message.content
                    #print(generated_text)

                    #print(f"GPT-4 Response Time: {datetime.datetime.now().strftime('%H:%M:%S')}\n",flush = True)

                    # Publish the transcript to RabbitMQ
                    channel.basic_publish(exchange='', routing_key='transcript_queue', body=str(generated_text)) #type:ignore

                except requests.exceptions.RequestException as req_error:
                    print(f"API request error: {req_error}")
                except Exception as e:
                    print(f"Unexpected error: {e}")

# Start a new thread to process audio data
threading.Thread(target=process_audio, daemon=True).start()
#executor = ThreadPoolExecutor(max_workers=3)

try:
    while True:
        # Start recording
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        # Add the recorded audio data to the queue
        audio_queue.put(frames)

except KeyboardInterrupt:
    print("\n...RECORDING STOPPED...")

finally:
    # Clean up
    stream.stop_stream()
    stream.close()
    audio.terminate()
