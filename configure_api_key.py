# configure_api_key.py
import os
from dotenv import set_key
from pwinput import pwinput
import colorama

# Initialize colorama
colorama.init(autoreset=True)

# Define the config file path and key name directly
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lilith")
API_KEY_NAME = "LILITH_API_KEY"

def configure_key():
    """Prompts the user for API keys and saves them to the .lilith file."""
    print(f"{colorama.Fore.CYAN}--- Lilith API Key Configuration ---{colorama.Style.RESET_ALL}")
    print(f"This script will save your API keys to the '{ENV_FILE}' file.")
    print("You can press Enter to skip a key if you don't want to change it.")

    # --- Create the .lilith file if it doesn't exist ---
    try:
        if not os.path.exists(ENV_FILE):
            open(ENV_FILE, 'a').close()
            print(f"Created new config file: {ENV_FILE}")
    except Exception as e:
        print(f"{colorama.Fore.RED}Could not create config file: {e}{colorama.Style.RESET_ALL}")
        return

    

    # --- Get GEMINI_API_KEY (for primary Gemini model) ---
    gemini_api_key = pwinput(
        prompt=f"{colorama.Fore.YELLOW}╚═> {colorama.Fore.WHITE}Enter your API_KEY: {colorama.Style.RESET_ALL}", 
        mask='*'
    )
    if gemini_api_key and gemini_api_key.strip():
        try:
            set_key(ENV_FILE, "GEMINI_API_KEY", gemini_api_key)
            print(f"{colorama.Fore.GREEN}Success! API key has been saved.{colorama.Style.RESET_ALL}")
        except Exception as e:
            print(f"{colorama.Fore.RED}An error occurred while saving the key: {e}{colorama.Style.RESET_ALL}")
    else:
        print(f"{colorama.Fore.CYAN}No API key entered. Skipping.{colorama.Style.RESET_ALL}")

    print("\nConfiguration complete. You can now start the server using 'python server.py'.")


if __name__ == "__main__":
    configure_key()
