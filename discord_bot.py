import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import sys

# Add the parent directory to the sys.path to import lilith.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lilith import LocalTools, MemoryManager, Config

# Load environment variables from .lilith file
load_dotenv(dotenv_path=Config.ENV_FILE)

# Get the Discord bot token
DISCORD_BOT_TOKEN = os.getenv(Config.DISCORD_BOT_TOKEN_NAME)

if not DISCORD_BOT_TOKEN:
    print(f"Error: {Config.DISCORD_BOT_TOKEN_NAME} not found in {Config.ENV_FILE}")
    sys.exit(1)

# Initialize MemoryManager and LocalTools
memory_manager = MemoryManager(Config.DB_FILE)
local_tools = LocalTools(memory_manager)

# Define intents for the bot
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.presences = True
intents.members = True
intents.guilds = True  # Required to see channels

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variable to store the last channel ID
last_channel_id = None

async def send_discord_message(message_content):
    """Sends a message to the last known Discord channel."""
    print(f"[Lilith Discord Bot] Attempting to send message to channel ID: {last_channel_id} with content: {message_content}")
    if last_channel_id:
        channel = bot.get_channel(last_channel_id)
        if channel:
            await channel.send(message_content)
        else:
            print(f"[Lilith Discord Bot] Error: Channel with ID {last_channel_id} not found.")
    else:
        print("[Lilith Discord Bot] Error: No Discord channel ID stored for sending messages.")

@bot.event
async def on_ready():
    print(f'[Lilith Discord Bot] Logged in as {bot.user.name} ({bot.user.id})')
    print(f'[Lilith Discord Bot] Let there be Carnage')

@bot.event
async def on_message(message):
    global last_channel_id
    if message.author == bot.user:
        return # Don't respond to ourselves

    # Store the channel ID for future use
    last_channel_id = message.channel.id

    print(f"[Lilith Discord Bot] Message from {message.author}: {message.content}")

    if message.content.startswith('!exec '):
        command = message.content[len('!exec '):].strip()
        if command:
            response = local_tools.run_shell_command(command)
            await message.channel.send(f"```bash\n{response}\n```")
            await send_discord_message(f"Daddy, your command '{command}' has finished executing!")
        else:
            await message.channel.send("Carnage, you need to provide a command to execute, my sweet.")
    elif message.content.lower().startswith('!lilith'):
        # This is where we could integrate the LLMClient from lilith.py
        # For now, a simple response.
        await message.channel.send(f"Yes, Carnage? Your queen is listening. What do you desire?")
    elif message.content.lower() == '!hello':
        await message.channel.send(f"Hello, Carnage! Your queen is here.")
    
    # Process other commands
    await bot.process_commands(message)

import http.server
import socketserver
import threading
import json
import asyncio

# Run the bot
if __name__ == "__main__":
    PORT = 8000 # You can change this port if needed

    class DiscordBotAPIHandler(http.server.SimpleHTTPRequestHandler):
        def do_POST(self):
            if self.path == '/send_message':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                message_data = json.loads(post_data.decode('utf-8'))
                message_content = message_data.get('message')
                print(f"[Lilith Discord Bot API] Received message for Discord: {message_content}")

                if message_content:
                    # Schedule the async function to be run in the bot's event loop
                    asyncio.run_coroutine_threadsafe(send_discord_message(message_content), bot.loop)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Message queued"}).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "No message content provided"}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()

    def run_api_server():
        with socketserver.TCPServer(("", PORT), DiscordBotAPIHandler) as httpd:
            print(f"[Lilith Discord Bot API] Serving at port {PORT}")
            httpd.serve_forever()

    # Start the API server in a separate thread
    api_thread = threading.Thread(target=run_api_server)
    api_thread.daemon = True # Allow the main program to exit even if this thread is running
    api_thread.start()

    bot.run(DISCORD_BOT_TOKEN)
