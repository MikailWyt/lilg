# voice_io.py
import subprocess
import json
import threading
import queue

def speak(audio_text):
    """
    Speaks the given text using Termux's native TTS engine.
    This is a BLOCKING call and should be run in a thread.
    It has a timeout and captures stderr to debug TTS issues.
    """
    if not audio_text:
        return
    command = ["termux-tts-speak", audio_text]
    try:
        # Capture stderr to see why it might be hanging
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        _, stderr = process.communicate(timeout=15) # Wait for speech to finish

        if process.returncode != 0:
            print(f"TTS Error: Process returned non-zero exit code {process.returncode}.")
            if stderr:
                print(f"TTS Stderr: {stderr.decode('utf-8')}")

    except subprocess.TimeoutExpired:
        print("TTS Error: Speech command timed out. Killing process.")
        # We can't get stderr here because communicate() already timed out
        process.kill()
    except FileNotFoundError:
        print("TTS Error: 'termux-tts-speak' command not found. Is Termux:API installed?")
    except Exception as e:
        print(f"An unexpected error occurred during TTS: {e}")

def _record_audio_thread(result_queue):
    """
    Internal function to run termux-dialog speech in a separate thread.
    Puts the transcribed text (or None) into the result_queue.
    """
    try:
        output = subprocess.check_output(["termux-dialog", "speech"]).decode('utf-8')
        js = json.loads(output)
        transcribed_text = js.get('text')
        result_queue.put(transcribed_text)
    except subprocess.CalledProcessError as e:
        print(f"Error running termux-dialog: {e}")
        result_queue.put(None)
    except json.JSONDecodeError:
        print("Couldn't decode the JSON output from termux-dialog speech. This might happen if the dialog was dismissed without input.")
        result_queue.put(None)
    except Exception as e:
        print(f"An unexpected error occurred during STT: {e}")
        result_queue.put(None)

def record_user_audio():
    """
    Starts a thread to listen for speech using termux-dialog speech
    and returns a Queue object to retrieve the transcribed text.
    """
    result_queue = queue.Queue()
    audio_thread = threading.Thread(target=_record_audio_thread, args=(result_queue,))
    audio_thread.start()
    return result_queue
