# server.py
import http.server
import socketserver
import json
import sys
import os
import re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# --- Import lilith.ai Core Logic ---
from lilith import LLMClient, UI, LocalTools, MemoryManager, Config, Personas

PORT = 8001

class AIRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # --- Process Request ---
            response_data = self.handle_ai_request(data)

            # --- Send Response ---
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Server Error: {e}")

    def handle_ai_request(self, data):
        global llm_client, tools
        
        prompt = data.get('prompt')
        if not prompt:
            return {"error": "No prompt provided"}

        # Get the AI's response
        response = llm_client.get_response(prompt)
        if not response:
            return {"response": "AI did not return a response."}

        # Check for tool calls in the response
        tool_calls = re.findall(r"tool_code:\s*({.*?})", response, re.DOTALL)

        # If there are no tool calls, just return the AI's natural response
        if not tool_calls:
            return {"response": response}

        # If there are tool calls, we need to decide if the client can handle it
        # or if the server should.
        try:
            tool_call_data = json.loads(tool_calls[0])
            tool_name = tool_call_data.get("tool")

            # These tools require user interaction and should be handled by the client
            client_side_tools = ["run_shell_command", "listen_for_command"]

            if tool_name in client_side_tools:
                # Pass the full response (including the tool_code) to the client
                # The client will parse it and ask for permission or listen.
                return {"response": response}
            else:
                # Server-side tools are executed here directly
                result = tools.execute_tool_call(tool_calls[0])
                
                # Now, we need to get the AI's final analysis based on the tool result
                follow_up_prompt = f"Here is the result of your tool request ({tool_name}):\n\n{result}\n\nNow, please provide your final analysis or response to the user."
                final_response = llm_client.get_response(follow_up_prompt)
                return {"response": final_response}

        except (json.JSONDecodeError, Exception) as e:
            return {"error": f"Error processing tool call on server: {str(e)}"}


if __name__ == "__main__":
    # --- Initialize AI ---
    print("Initializing Lilith server...")
    memory = MemoryManager(Config.DB_FILE)
    tools = LocalTools(memory) # UI is not needed for server tools
    
    load_dotenv(dotenv_path=Config.ENV_FILE)
    api_key = os.getenv(Config.API_KEY_NAME)
    if not api_key:
        print(f"WARNING: Primary API key {Config.API_KEY_NAME} not found in {Config.ENV_FILE}. This may lead to API errors.")

    llm_client = LLMClient(api_key, UI(), memory, "server_session")
    llm_client.set_persona(Personas.LILITH)
    print("Lilith server initialized.")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AIRequestHandler) as httpd:
        print(f"Serving on port {PORT}")
        print("Use the client to interact or Ctrl+C to stop.")
        httpd.serve_forever()
