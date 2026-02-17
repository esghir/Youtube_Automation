import os
import subprocess
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
INPUT_FOLDER = "local_files/upload song"
OUTPUT_FOLDER = "local_files/cleaned songs"
SPEED_FACTOR = 1.015  # 1.5% Speed up
# ⚠️ DOWNLOAD "OAuth Desktop Client" JSON from Cloud Console -> Rename to 'credentials.json'
CLIENT_SECRET_FILE = 'client_secret_203814077086-45qv2fcskncr13tam0n5gnkhoi03uhlk.apps.googleusercontent.com.json'
TOKEN_FILE = 'token.json'
# ⚠️ REMPLACE HADI B FOLDER ID DYAL DRIVE DYALK
PARENT_FOLDER_ID = '1vthP0uvSTlISxuV2EJcy-sdcCSB0cMP2' 

# Create output folder
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# --- AUTHENTICATION ---
def get_drive_service():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Refresh or Login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"❌ Error: '{CLIENT_SECRET_FILE}' not found!")
                print("👉 Go to Google Cloud Console > APIs & Services > Credentials")
                print("👉 Create 'OAuth Client ID' (Application Type: Desktop App)")
                print("👉 Download JSON, rename to 'credentials.json', and put it here.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# --- 1. FUNCTION: UPLOAD TO DRIVE ---
def upload_to_drive(file_path):
    try:
        service = get_drive_service()
        if not service:
            return None

        print(f"☁️ Uploading {os.path.basename(file_path)} to Drive...")

        # Metadata
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [PARENT_FOLDER_ID]
        }

        # Media
        media = MediaFileUpload(file_path, mimetype='audio/mp3', resumable=True)

        # Execute Upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"✅ Upload Success! File ID: {file.get('id')}")
        return file.get('id')

    except Exception as e:
        print(f"❌ Drive Error: {e}")
        return None

# --- 2. FUNCTION: CLEAN AUDIO ---
def clean_and_upload(input_path, output_path):
    try:
        print(f"🔄 Processing: {input_path}...")
        
        command = [
            "ffmpeg", "-y", "-i", input_path,
            "-map_metadata", "-1",
            "-filter:a", f"asetrate=44100*{SPEED_FACTOR},aresample=44100",
            "-b:a", "320k",
            output_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            print(f"✨ Audio Cleaned: {output_path}")
            
            # --- TRIGGER UPLOAD HERE ---
            if PARENT_FOLDER_ID != 'PLACEHOLDER_ENTER_YOUR_FOLDER_ID_HERE':
                upload_to_drive(output_path)
            else:
                print("⚠️ Skipping Upload: PARENT_FOLDER_ID is missing!")
            
        else:
            print(f"❌ FFmpeg Error: {result.stderr.decode()}")

    except Exception as e:
        print(f"❌ Processing Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print(f"🚀 Antigravity Engine Started...")
    
    if not os.path.exists(INPUT_FOLDER):
         print(f"⚠️ Input folder '{INPUT_FOLDER}' not found!")
         exit(1)

    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".mp3")]
    
    if not files:
        print(f"⚠️ No MP3 files found in '{INPUT_FOLDER}'!")
    else:
        for file in files:
            in_path = os.path.join(INPUT_FOLDER, file)
            out_path = os.path.join(OUTPUT_FOLDER, f"clean_{file}")
            clean_and_upload(in_path, out_path)
