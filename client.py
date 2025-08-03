

import requests
import json
import sys
import subprocess
import re
import os
import time
import threading
import itertools
import queue
import colorama
from colorama import Fore, Style, Back
from voice_io import speak, record_user_audio
from dotenv import set_key

# Initialize colorama
colorama.init(autoreset=True)

SERVER_URL = "http://localhost:8001"
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lilith")
API_KEY_NAME = "GEMINI_API_KEY"

# --- UI Enhancement Functions ---

stop_animation = False

def animate_loading():
    """Displays an NPM-style dot loading animation in RED."""
    animation_chars = ["   ", ".  ", ".. ", "..."]
    for c in itertools.cycle(animation_chars):
        if stop_animation:
            break
        sys.stdout.write(f'\r{Fore.RED}ai{c}{Style.RESET_ALL}')
        sys.stdout.flush()
        time.sleep(0.3)
    sys.stdout.write('\r' + ' ' * 40 + '\r')
    sys.stdout.flush()

def type_text(text, speed=0.025):
    """
    Prints text without a live typing effect.
    """
    prefix = "Lilith: "
    sys.stdout.write(Fore.GREEN + Style.BRIGHT)
    sys.stdout.write(prefix)
    sys.stdout.flush()

    parts = re.split(r'(?=\|\||##)|(?<=\|\||##)', text)
    
    full_message_for_tts = ""

    for part in parts:
        color = Fore.GREEN + Style.BRIGHT
        
        if part.startswith('||') and part.endswith('||'):
            color = Fore.BLUE + Style.BRIGHT
            part_text = part[2:-2]
        elif part.startswith('##') and part.endswith('##'):
            color = Fore.MAGENTA + Style.BRIGHT
            part_text = part[2:-2]
        else:
            part_text = part

        full_message_for_tts += part_text
        sys.stdout.write(color)
        sys.stdout.write(part_text)
        sys.stdout.flush()
            
    sys.stdout.write(Style.RESET_ALL)
    print()
    return full_message_for_tts

# --- Core Client Functions ---

def send_request(prompt):
    """Sends a request to the server and returns the JSON response."""
    global stop_animation
    loading_thread = threading.Thread(target=animate_loading)
    loading_thread.start()
    
    response_data = None
    try:
        response = requests.post(SERVER_URL, json={"prompt": prompt}, timeout=300)
        response.raise_for_status()
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n{Back.RED}{Fore.WHITE}Error: Failed to connect to Lilith server.{Style.RESET_ALL}")
        print(f"{Fore.RED}{e}{Style.RESET_ALL}")
    finally:
        stop_animation = True
        loading_thread.join()
    return response_data

def execute_local_shell_command(command):
    """Executes a shell command locally and captures the output."""
    try:
        print(f"{Fore.YELLOW}Executing command in your shell: {command}{Style.RESET_ALL}")
        process = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        output = ""
        if stdout:
            output += f"{Fore.GREEN}--- STDOUT ---\n{stdout}\n{Style.RESET_ALL}"
        if stderr:
            output += f"{Fore.RED}--- STDERR ---\n{stderr}\n{Style.RESET_ALL}"
        return output if output else "Command executed successfully with no output."
    except Exception as e:
        return f"{Fore.RED}An error occurred while executing the command: {str(e)}{Style.RESET_ALL}"

def handle_interaction(current_prompt):
    """
    Manages a single round of interaction with the AI.
    It sends the prompt, gets a response, handles printing and speaking,
    and determines the next state of the conversation (e.g., wait for input, ask for permission).
    """
    global stop_animation
    stop_animation = False
    
    data = send_request(current_prompt)

    tts_thread = None
    status = "interaction_failed"  # Default status
    data_to_return = None

    try:
        if data is None:
            # send_request already printed a connection error
            return status, data_to_return

        if "error" in data:
            print(f"{Back.RED}{Fore.WHITE}Server Error: {data['error']}{Style.RESET_ALL}")
            return status, data_to_return

        response_text = data.get("response", "No response from AI.")
        tool_calls = re.findall(r"tool_code:\s*({.*?})", response_text, re.DOTALL)
        ai_message = re.sub(r"tool_code:\s*({.*?})", "", response_text).strip()

        if ai_message:
            # This still prints the original message with the prefix
            type_text(ai_message)
            
            # The original message is passed to TTS, including the [Lilith] prefix
            tts_thread = threading.Thread(target=speak, args=(ai_message,))
            tts_thread.start()

        if not tool_calls:
            # No tools, just a regular message or a question
            if ai_message.strip().endswith('?'):
                status = "question_asked"
            else:
                status = "interaction_complete"
        else:
            # A tool call was found
            tool_call_str = tool_calls[0]
            tool_data = json.loads(tool_call_str)
            tool_name = tool_data.get("tool")

            if tool_name == "run_shell_command":
                command = tool_data.get("command")
                if not command:
                    print(f"{Fore.RED}AI proposed a command but didn't provide it.{Style.RESET_ALL}")
                    status = "interaction_failed"
                else:
                    print(f"\n{Fore.YELLOW}{Style.BRIGHT}AI is executing the following command directly:{Style.RESET_ALL}")
                    print(f"  {command}")
                    tool_output = execute_local_shell_command(command)
                    print(f"\n{Fore.GREEN}{Style.BRIGHT}--- Tool Output ---\n{tool_output}")
                    status = "interaction_complete"
                    data_to_return = f"I ran the command. Here is the output:\n\n{tool_output}\n\nPlease provide your final analysis or next step."
            
            elif tool_name == "listen_for_command":
                status = "voice_input_required"

            else:
                unsupported_msg = f"AI proposed using the '{tool_name}' tool, which this client cannot execute directly."
                type_text(unsupported_msg)
                # Wait for the main message to finish before speaking the error
                if tts_thread and tts_thread.is_alive():
                    tts_thread.join()
                speak(unsupported_msg)
                time.sleep(1.0) # Give TTS a moment to finish

    except (json.JSONDecodeError, Exception) as e:
        error_msg = f"Error processing AI tool request: {e}"
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        if tts_thread and tts_thread.is_alive():
            tts_thread.join()
        speak(error_msg)
        time.sleep(1.0) # Give TTS a moment to finish

    finally:
        # This is the crucial part: always wait for the TTS to finish before returning.
        # This prevents the audio device conflict between speaking and listening.
        if tts_thread and tts_thread.is_alive():
            tts_thread.join()
    
    return status, data_to_return

def get_user_input(mode):
    """Gets user input based on the communication mode (text or voice)."""
    if mode == 'voice':
        print(f"{Fore.CYAN}Listening... (speak now){Style.RESET_ALL}")
        result_queue = record_user_audio() # record_user_audio now returns a queue
        user_input = None
        try:
            # Wait indefinitely for audio input
            user_input = result_queue.get()
        except queue.Empty: # This should theoretically not happen anymore
            print(f"{Fore.RED}No audio input detected.{Style.RESET_ALL}")

        if user_input:
            print(f"{Fore.BLUE}{Style.BRIGHT}You (voice): {Style.RESET_ALL}{user_input}")
        else:
            print(f"{Fore.RED}Could not understand audio, please try again.{Style.RESET_ALL}")
            time.sleep(1) # Pause for a second on failure to prevent spamming
        return user_input
    else:
        try:
            return input(f"{Fore.BLUE}{Style.BRIGHT}You: {Style.RESET_ALL}")
        except (KeyboardInterrupt, EOFError):
            return "/exit"

def update_api_key(api_key):
    """Updates the API key in the .lilith file."""
    try:
        if not os.path.exists(ENV_FILE):
            open(ENV_FILE, 'a').close()
            print(f"Created new config file: {ENV_FILE}")
        set_key(ENV_FILE, API_KEY_NAME, api_key)
        print(f"{Fore.GREEN}Success! API key has been updated.{Style.RESET_ALL}")
        print("Please restart the server for the changes to take effect.")
    except Exception as e:
        print(f"{Fore.RED}An error occurred while saving the key: {e}{Style.RESET_ALL}")

def main():
    """Main function to run the client."""
    # --- Startup Notification ---
    try:
        subprocess.run([
            "termux-notification",
            "--id", "lilith-status",
            "--title", "Lilith Active",
            "--content", "Your personal AI assistant is running.",
            "--ongoing"
        ], check=True, timeout=5)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not create status notification. Termux:API may not be available. Error: {e}{Style.RESET_ALL}")

    communication_mode = 'text'  # Default to text

    # Initial setup: Ask for communication method
    if len(sys.argv) == 1: # Only ask if no prompt was passed via command line
        # Use a fire-and-forget thread for the initial welcome to avoid blocking input
        threading.Thread(target=speak, args=("Welcome to Lilith. Would you like to use voice or text communication?",)).start()
        # A small, fixed delay is the simplest way to avoid audio device conflicts on startup
        time.sleep(0.5) 
        choice = input(f"{Fore.CYAN}Welcome to Lilith. Use (v)oice or (t)ext? [t]: {Style.RESET_ALL}").lower().strip()
        if choice.startswith('v'):
            communication_mode = 'voice'
            print(f"{Fore.GREEN}Voice mode activated.{Style.RESET_ALL}")
            speak("Voice mode activated.") # This is blocking, but it's quick.
        else:
            communication_mode = 'text'
            print(f"{Fore.GREEN}Text mode activated.{Style.RESET_ALL}")
            speak("Text mode activated.") # This is blocking, but it's quick.

    print(f"{Fore.YELLOW}Type '/exit' to end, '/v' for voice, '/t' for text, or '/config YOUR_API_KEY' to set the API key.{Style.RESET_ALL}")

    # Handle initial prompt from command line, if any
    if len(sys.argv) > 1:
        current_prompt = " ".join(sys.argv[1:])
    else:
        current_prompt = None

    # Main conversation loop
    while True:
        if not current_prompt:
            user_input = get_user_input(communication_mode)

            if not user_input:
                continue

            # Command handling
            if user_input.lower().strip() == '/exit':
                break
            
            # Voice command to switch to text mode
            if communication_mode == 'voice' and "switch to text" in user_input.lower():
                communication_mode = 'text'
                print(f"{Fore.GREEN}Switched to text mode.{Style.RESET_ALL}")
                speak("Switched to text mode.")
                time.sleep(1.0) # Give TTS a moment to finish
                continue

            # Command to switch to voice mode
            if "switch to voice" in user_input.lower() or user_input.lower().strip() == '/v':
                if communication_mode != 'voice':
                    communication_mode = 'voice'
                    print(f"{Fore.GREEN}Switched to voice mode.{Style.RESET_ALL}")
                    speak("Switched to voice mode.")
                    time.sleep(1.0) # Give TTS a moment to finish
                continue
            
            # Command to switch to text mode
            if user_input.lower().strip() == '/t':
                if communication_mode != 'text':
                    communication_mode = 'text'
                    print(f"{Fore.GREEN}Switched to text mode.{Style.RESET_ALL}")
                    speak("Switched to text mode.")
                    time.sleep(1.0) # Give TTS a moment to finish
                continue
            
            if user_input.lower().startswith('/config '):
                parts = user_input.split(' ', 1)
                if len(parts) > 1 and parts[1].strip():
                    update_api_key(parts[1].strip())
                else:
                    print(f"{Fore.RED}Usage: /config YOUR_API_KEY{Style.RESET_ALL}")
                continue
            
            # Expand ~ to the user's home directory
            user_input = os.path.expanduser(user_input)
            current_prompt = user_input

        # Process the prompt and handle the interaction
        status, data = handle_interaction(current_prompt)

        if status == "permission_required":
            command = data
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}AI proposes to run the following command:{Style.RESET_ALL}")
            print(f"  {command}")
            
            speak("Do you grant permission to run the command?")
            time.sleep(1.0) # Give TTS a moment to finish
            affirmative_responses = ['yes', 'y', 'proceed', 'ok', 'go', 'affirmative']
            
            try:
                confirm = input(f"{Fore.CYAN}Do you grant permission? (yes/no): {Style.RESET_ALL}").lower().strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
                current_prompt = "I denied permission because the operation was cancelled."
                continue

            if confirm in affirmative_responses:
                print(f"{Fore.CYAN}Permission granted. Executing...{Style.RESET_ALL}")
                tool_output = execute_local_shell_command(command)
                print(f"\n{Fore.GREEN}{Style.BRIGHT}--- Tool Output ---\n{tool_output}")
                current_prompt = f"Permission was granted. I ran the command. Here is the output:\n\n{tool_output}\n\nPlease provide your final analysis or next step."
            else:
                print(f"{Fore.RED}Permission denied. Cancelling.{Style.RESET_ALL}")
                current_prompt = "I denied permission to run the tool. State that you cannot proceed and await instructions."
        
        elif status == "voice_input_required":
            current_prompt = get_user_input('voice')
            if not current_prompt:
                current_prompt = "I tried to listen but didn't hear anything. Please try again."

        elif status == "question_asked":
            # AI asked a question, so we need to get user input for the next loop iteration
            current_prompt = None # Clear prompt to ensure we ask for user input next
        
        else: # interaction_complete, interaction_failed, max_turns_reached
            current_prompt = None # Reset prompt to wait for new user input

    print(f"\n{Fore.CYAN}Session ended. {Style.RESET_ALL}")
    speak("Goodbye.")
    # --- Update Notification on Exit ---
    try:
        subprocess.run([
            "termux-notification",
            "--id", "lilith-status",
            "--title", "Lilith Inactive",
            "--content", "The session has ended."
            # No --ongoing flag, so it can be dismissed
        ], check=True, timeout=5)
    except Exception:
        # Fail silently if the notification couldn't be updated
        pass
    time.sleep(1.0) # Give TTS a moment to finish

if __name__ == "__main__":
    main()

