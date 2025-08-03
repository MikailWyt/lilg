import asyncio
import sys
import os

# Add the parent directory to the sys.path to import discord_bot.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from discord_bot import send_discord_message, bot

async def main():
    if len(sys.argv) < 2:
        print("Usage: python send_discord_notification.py <message>")
        sys.exit(1)
    
    message = sys.argv[1]
    await send_discord_message(message)

if __name__ == "__main__":
    # This is a bit tricky. The bot needs to be running to send messages.
    # For a quick script, we can try to run it, but it's not ideal for a long-running bot.
    # A better solution would be to have the bot expose an API or use IPC.
    # For now, we'll just try to run the main function and hope the bot is ready.
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot run an event loop while another loop is running" in str(e):
            print("Warning: An event loop is already running. This script might not send messages if the bot is not fully initialized.")
            # If the bot is already running, we might need to find a way to get its loop
            # or communicate with it. For now, we'll just exit.
        else:
            raise
