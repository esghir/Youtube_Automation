import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

CONFIG_FILE = 'config.json'
ENV_FILE = '.env'

@app.route('/api/save-config', methods=['POST'])
def save_config():
    data = request.json
    
    # Save Styles and Channels to config.json
    config_data = {
        "items": data.get("items", [])
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)
        
    # Save API Keys to .env
    api_keys = data.get("apiKeys", {})
    env_content = ""
    for key, value in api_keys.items():
        env_content += f"{key}={value}\n"
        
    with open(ENV_FILE, 'w') as f:
        f.write(env_content)
        
    return jsonify({"status": "success", "message": "Configuration saved successfully"})

@app.route('/api/load-config', methods=['GET'])
def load_config():
    config = {"items": []}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                pass
                
    # Load existing env vars (masked)
    load_dotenv(ENV_FILE)
    api_keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY", ""),
        # Add others as needed
    }
    
    return jsonify({"config": config, "apiKeys": api_keys})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
