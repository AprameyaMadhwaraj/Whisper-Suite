import pyaudio
import wave
import tempfile
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

# Audio parameters
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 6  # Adjust as needed

audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

print("\n...LISTESING...\n")

try:
    while True:
        # Start recording
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

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
                    language='en'
                    )

                    system_prompt = '''correct spelling mistakes. You will be dealing with Medical reports. 
                    Don't print commas after pause. 
                    Read next line and make sure the text that follows will be in the next line. 
                    Also if the speaker says colon, print the symbol ':' in place of the word. 
                    do not print anything unnecessary if there is silence. be very quick and accurate.
                    do not print the segments in the next line, unless clearly specified as 'next line' 
                    even if there are long pauses in the speech, add them to the same line as the previous
                    transcript, unless clearly specified as 'next line' 
                    DO NOT PRINT STATEMENTS LIKE : You're welcome, I'm here to help, 
                    Please provide the medical report or details you need assistance with.'''

                    response = client.chat.completions.create(
                        model="gpt-4-0125-preview",
                        temperature=0,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            { #type:ignore
                                "role": "user",
                                "content": transcript
                            }
                        ]
                    )
                    transcription = response.choices[0].message.content
                    print(transcription, end=' ')


                except requests.exceptions.RequestException as req_error:
                    print(f"API request error: {req_error}")
                except Exception as e:
                    print(f"Unexpected error: {e}")

except KeyboardInterrupt:
    print("\n...Recording stopped...\n")

finally:
    # Clean up
    stream.stop_stream()
    stream.close()
    audio.terminate()