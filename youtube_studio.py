import customtkinter as ctk
from tkinter import filedialog, messagebox
import google.generativeai as genai
# --- MONKEYPATCH FOR PILLOW 10+ ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, VideoFileClip, vfx, concatenate_audioclips, concatenate_videoclips
import os
import threading
import subprocess
from datetime import datetime
import requests
import random
import time
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

def generate_spectrum_video(audio_path, output_vis_path):
    # Generates a frequency bar visualizer using FFmpeg
    # Size: 640x120 (Small, subtle bars)
    # Mode: bar. Colors: White
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-filter_complex", "showfreqs=s=640x120:mode=bar:fscale=log:ascale=log:colors=white,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        output_vis_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
        

# --- GOOGLE AUTH IMPORTS ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
# ⚠️ Using the user provided OAuth Client File
CLIENT_SECRET_FILE = 'client_secret_203814077086-45qv2fcskncr13tam0n5gnkhoi03uhlk.apps.googleusercontent.com.json'
TOKEN_FILE = 'token.json'
PARENT_FOLDER_ID = '1vthP0uvSTlISxuV2EJcy-sdcCSB0cMP2' 

# Combined Scopes for Drive and YouTube
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/youtube.upload'
]

# --- SHARED AUTH FUNCTION ---
def get_credentials():
    creds = None
    # Load existing token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None
    
    # Refresh or Login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise Exception(f"OAuth File '{CLIENT_SECRET_FILE}' not found! Download it from Google Cloud.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds

# --- DRIVE FUNCTIONS ---
def upload_to_drive(file_path):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    print(f"☁️ Uploading {os.path.basename(file_path)} to Drive...")

    # Metadata
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [PARENT_FOLDER_ID]
    }

    # Media
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)

    # Execute Upload
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')

# --- YOUTUBE FUNCTIONS ---
def upload_to_youtube(video_path, title, description, tags):
    print(f"🎬 Starting YouTube Upload: {title}...")
    
    creds = get_credentials()
    youtube = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title[:100], # Max 100 chars
            'description': description[:5000], # Max 5000 chars
            'tags': tags,
            'categoryId': '10'  # Category 10 = Music
        },
        'status': {
            'privacyStatus': 'private', # Defaulting to Private for safety as requested
            'selfDeclaredMadeForKids': False
        }
    }

    # Media Setup
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    # Upload Request
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    # Progress Loop
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"🚀 (YouTube) Uploaded {int(status.progress() * 100)}%")

    print(f"✅ YouTube Upload Success! Video ID: {response['id']}")
    return response['id']


# Configuration de l'app
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class YouTubeStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Antigravity Studio - AI Video Maker")
        self.geometry("700x750")

        # Variables
        self.audio_paths = []
        self.api_key = ""
        self.generated_image_path = "temp_visual.jpg"
        self.visualizer_path = "assets/visualizer_overlay.mp4"

        # --- UI Layout ---
        
        # 1. API Key Section
        self.api_frame = ctk.CTkFrame(self)
        self.api_frame.pack(pady=10, padx=20, fill="x")
        
        self.label_api = ctk.CTkLabel(self.api_frame, text="Gemini API Key:")
        self.label_api.pack(side="left", padx=10)
        
        self.entry_api = ctk.CTkEntry(self.api_frame, placeholder_text="Paste your NEW API Key here", width=400, show="*")
        self.entry_api.pack(side="left", padx=10)

        # 2. File Selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(pady=10, padx=20, fill="x")

        self.btn_audio = ctk.CTkButton(self.file_frame, text="Select Songs (Batch)", command=self.select_audio)
        self.btn_audio.grid(row=0, column=0, padx=10, pady=10)
        self.lbl_audio = ctk.CTkLabel(self.file_frame, text="No files selected", text_color="gray")
        self.lbl_audio.grid(row=0, column=1, padx=10, pady=10)

        # 3. Prompt Section
        self.prompt_frame = ctk.CTkFrame(self)
        self.prompt_frame.pack(pady=10, padx=20, fill="x")
        
        self.lbl_prompt = ctk.CTkLabel(self.prompt_frame, text="Describe the Songs (Shared Prompt):")
        self.lbl_prompt.pack(anchor="w", padx=10, pady=(10,0))
        
        self.entry_prompt = ctk.CTkEntry(self.prompt_frame, placeholder_text="e.g., Energetic Moroccan Chaabi wedding song...", width=600)
        self.entry_prompt.pack(padx=10, pady=10)

        # 4. Generate Button
        self.btn_generate = ctk.CTkButton(self, text="Generate Batch & Upload", command=self.start_generation_thread, height=50, fg_color="green", hover_color="darkgreen")
        self.btn_generate.pack(pady=20, padx=20, fill="x")

        # 5. Output Area
        self.output_box = ctk.CTkTextbox(self, width=650, height=150)
        self.output_box.pack(pady=10)
        self.output_box.insert("0.0", "Logs will appear here...")

        # 6. Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="white")
        self.status_label.pack(side="bottom", pady=10)

    def select_audio(self):
        paths = filedialog.askopenfilenames(filetypes=[("Media", "*.mp3 *.wav *.mp4")])
        if paths:
            self.audio_paths = list(paths)
            count = len(self.audio_paths)
            self.lbl_audio.configure(text=f"{count} file(s) selected", text_color="white")

    def start_generation_thread(self):
        threading.Thread(target=self.process_batch, daemon=True).start()

    def safe_update(self, func, *args, **kwargs):
        """Helper to run GUI updates on the main thread"""
        self.after(0, lambda: func(*args, **kwargs))

    def log(self, message):
        print(message) # Also print to console
        self.safe_update(lambda m: (self.output_box.insert("end", m + "\n"), self.output_box.see("end")), message)
        
    def safe_status(self, text, color="white"):
        self.safe_update(lambda: self.status_label.configure(text=text, text_color=color))
        
    def safe_progress(self, val):
        self.safe_update(lambda: self.progress_bar.set(val))

    def safe_btn_config(self, **kwargs):
        self.safe_update(lambda: self.btn_generate.configure(**kwargs))

    def process_batch(self):
        # 1. Validation (must be on main thread? No, get() is generally safe but let's assume valid start from button command)
        # However, calling get() from thread is sometimes risky. better to pass args. 
        # But for now, let's just make the outputs safe.
        
        api_key = self.entry_api.get()
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
        
        user_prompt_base = self.entry_prompt.get()
        
        if not api_key or not self.audio_paths or not user_prompt_base:
            self.safe_update(lambda: messagebox.showerror("Error", "Please fill all fields and select files!"))
            return

        self.safe_btn_config(state="disabled", text="Merging & Processing...")
        count = len(self.audio_paths)
        
        try:
            # --- MERGING LOGIC ---
            self.log(f"\n--- Starting Batch Merge for {count} files ---")
            self.safe_status(f"Merging {count} songs into one...")
            
            all_videos = all(p.lower().endswith('.mp4') for p in self.audio_paths)
            
            cleaned_names = [os.path.splitext(os.path.basename(p))[0].replace("_", " ") for p in self.audio_paths]
            merged_filename_base = f"Mix_{len(self.audio_paths)}_Songs_{int(time.time())}"
            
            if all_videos:
                self.log("Detected MP4 Video Input. merging clips...")
                clips = []
                for p in self.audio_paths:
                    clips.append(VideoFileClip(p))
                
                final_merged = concatenate_videoclips(clips, method="compose")
                merged_path = f"{merged_filename_base}.mp4"
                self.log(f"Writing temporary merged video: {merged_path}...")
                final_merged.write_videofile(merged_path, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
                
            else:
                self.log("Detected Audio Input (or mixed). Merging audio tracks...")
                clips = []
                for p in self.audio_paths:
                    clips.append(AudioFileClip(p))
                
                final_merged = concatenate_audioclips(clips)
                merged_path = f"{merged_filename_base}.mp3"
                self.log(f"Writing temporary merged audio: {merged_path}...")
                final_merged.write_audiofile(merged_path, logger=None)

            self.log("Merge Complete! Starting Generation...")
            
            mix_prompt = f"{user_prompt_base}. Mix containing: {', '.join(cleaned_names)}."
            
            self.process_single_video(merged_path, api_key, mix_prompt, 1, 1)
            
            # --- CLEANUP MERGED FILE ---
            if os.path.exists(merged_path):
                self.log(f"Removing intermediate merged file: {merged_path}")
                os.remove(merged_path)
            
            self.safe_status("✅ Mix Completed!", "#00FF00")
            self.safe_update(lambda: messagebox.showinfo("Mix Complete", f"Successfully created mix from {count} files."))

        except Exception as e:
            self.safe_status(f"Error: {e}", "red")
            err_msg = str(e)
            self.safe_update(lambda: messagebox.showerror("Error", err_msg))
        finally:
            self.safe_btn_config(state="normal", text="Generate Batch & Upload")
            self.safe_progress(0)

    def process_single_video(self, audio_path, api_key, user_prompt, current_index, total_files):
        
        def update_progress(local_percent):
            base_percent = (current_index - 1) / total_files
            chunk_percent = 1 / total_files
            final_percent = base_percent + (local_percent * chunk_percent)
            self.safe_progress(final_percent)

        is_video_input = audio_path.lower().endswith('.mp4')
        update_progress(0.1)

        try:
            # 2. AI Generation
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            
            ai_prompt_text = f"""
            Act as a YouTube Expert. Song Context: "{user_prompt}".
            
            Generate:
            1. Title (with Year {datetime.now().year}).
            2. Description: Engaging, 3-4 sentences long. Include keywords.
            3. Visual Prompt: Digital art description.
            
            Strict Format:
            [TITLE]
            (title here)
            [DESCRIPTION]
            (description here)
            [IMAGE_PROMPT]
            (image prompt here)
            """
            
            payload = {
                "contents": [{
                    "parts": [{"text": ai_prompt_text}]
                }]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Gemini API Error: {response.status_code}")
                
            response_json = response.json()
            full_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            # Parsing
            try:
                # Normalize newlines
                clean_text = full_text.replace("**", "").replace("##", "")
                parts = clean_text.split("[DESCRIPTION]")
                title_part = parts[0].replace("[TITLE]", "").strip()
                
                rest = parts[1]
                parts2 = rest.split("[IMAGE_PROMPT]")
                description_part = parts2[0].strip()
                image_prompt = parts2[1].strip()
            except:
                self.log("⚠️ Metadata parsing failed. Using raw text.")
                title_part = f"AI Music Mix {datetime.now().year}"
                description_part = full_text[:500] # Fallback to first 500 chars of raw text
                image_prompt = "Abstract digital art, colorful music visualization, 4k"

            self.log(f"Title: {title_part}")
            self.log(f"Description Length: {len(description_part)} chars")
            update_progress(0.3)

            # --- BRANCHING LOGIC ---
            if is_video_input:
                # === MP4 INPUT MODE ===
                original_clip = VideoFileClip(audio_path)
                w, h = original_clip.size
                final_clip = original_clip.crop(y2=h - 100) # Crop bottom 100 pixels
                update_progress(0.6)

            else:
                # === MP3 INPUT MODE ===
                # Image Generation Logic
                import urllib.parse
                
                # Use User's Description directly + Realistic Style
                img_prompt_base = user_prompt.strip()
                style_suffix = "Realistic, Cinematic lighting, 8k, Ultra detailed, Professional Photography"
                full_img_prompt = f"{img_prompt_base}, {style_suffix}"
                
                # Truncate to safe length for URL (approx 500 chars is usually safe for GET)
                full_img_prompt = full_img_prompt[:500]
                
                temp_img_path = f"temp_visual_{current_index}.jpg"
                success = False
                
                try:
                    # Simplify prompt to just the first 200 chars to be safe + visual keywords
                    clean_prompt = "".join([c for c in img_prompt_base if c.isalnum() or c in (' ', ',')]).strip()[:200]
                    final_prompt_str = f"{clean_prompt} realistic 8k cinematic lighting"
                    
                    self.log(f"Generating Image: {final_prompt_str[:50]}...")
                    encoded_prompt = urllib.parse.quote(final_prompt_str)
                    seed = random.randint(0, 99999)
                    
                    # specific image endpoint, not the interactive /p/ one
                    # Use 'nologo=true' but correct endpoint
                    poll_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&seed={seed}&nologo=true&model=flux"
                    
                    # Add headers to avoid bot detection
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    
                    response_img = requests.get(poll_url, headers=headers, timeout=30)
                    content_type = response_img.headers.get('Content-Type', '')
                    
                    # Pollinations returns image/jpeg or image/png usually
                    if response_img.status_code == 200 and 'image' in content_type:
                        with open(temp_img_path, 'wb') as f:
                            f.write(response_img.content)
                        success = True
                        self.log("✅ Image Generated Successfully.")
                    else:
                        # Fallback: Try a simpler prompt if complex one fails
                        self.log(f"⚠️ First attempt failed ({content_type}). Retrying with simple prompt...")
                        simple_url = f"https://image.pollinations.ai/prompt/Abstract%20Music%20Visualization?width=1280&height=720&seed={seed}"
                        response_img = requests.get(simple_url, headers=headers)
                        if response_img.status_code == 200:
                            with open(temp_img_path, 'wb') as f:
                                f.write(response_img.content)
                            success = True
                            self.log("✅ Image Generated (Fallback).")
                        else:
                            self.log(f"⚠️ Image Gen Totally Failed.")
                        
                except Exception as e:
                    self.log(f"⚠️ Image Gen Error: {e}")

                if not success:
                    self.log("❌ Image Generation Failed. Creating Placeholder.")
                    # Use global PIL imports
                    img = Image.new('RGB', (1280, 720), color=(10, 10, 20)) # Dark Blue
                    d = ImageDraw.Draw(img)
                    # Add text fallback
                    try:
                        d.text((100, 300), f"Music Mix\n{datetime.now().year}", fill=(200, 200, 200))
                    except: pass
                    img.save(temp_img_path)
                
                # --- V3: REVERTED TO SIMPLE WAVEFORM (User Request) ---
                self.log("Rendering Visualizer (Standard Waveform)...")
                
                # 1. Prepare Audio
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                
                # 2. Prepare Background Image (Standard 16:9)
                # Ensure it fits 1280x720
                raw_image = ImageClip(temp_img_path)
                iw, ih = raw_image.size
                # Simple crop/resize logic from original script
                image_clip = raw_image.crop(y2=ih-60).resize((1280, 720)).set_duration(duration)
                
                # 3. Generate Simple Waveform (Fast)
                vis_video_path = f"temp_spectrum_{current_index}.mp4"
                
                # Original command (lines 471-477 of Step 12)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", audio_path,
                    "-filter_complex", "showwaves=s=1280x200:mode=line:colors=cyan|magenta,format=yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    vis_video_path
                ]
                
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    vis_clip = VideoFileClip(vis_video_path).loop(duration=duration)
                    # Position at center with opacity (Original style)
                    vis_clip = vis_clip.set_position(("center", "center")).set_opacity(0.7)
                    # Color keying black
                    vis_clip = vis_clip.fx(vfx.mask_color, color=[0,0,0], thr=50, s=2)
                    
                    final_clip = CompositeVideoClip([image_clip, vis_clip]).set_duration(duration)
                except Exception as ve:
                    self.log(f"⚠️ Visualizer Failed: {ve}. Using static image.")
                    final_clip = image_clip
                    
                final_clip = final_clip.set_audio(audio_clip)
                update_progress(0.7)

            # Export
            safe_title = "".join([c for c in title_part if c.isalnum() or c in (' ', '-', '_')]).strip()
            safe_title = safe_title[:50]
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename_out = f"{safe_title}_{date_str}.mp4"
            
            # --- OUTPUT FOLDER: Result ---
            result_dir = os.path.join(os.getcwd(), "Result")
            os.makedirs(result_dir, exist_ok=True)
            output_path = os.path.join(result_dir, filename_out)
            
            self.log(f"Writing video to: {output_path}...")
            final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', logger=None)
            update_progress(0.8)
            
            # Drive Upload
            file_id = upload_to_drive(output_path)
            self.log(f"Drive ID: {file_id}")
            
            # YouTube Upload
            yt_tags = [x.strip() for x in user_prompt.split(",")] + ["AI Music"]
            yt_id = upload_to_youtube(
                video_path=output_path,
                title=title_part,
                description=description_part,
                tags=yt_tags
            )
            self.log(f"YouTube ID: {yt_id}")
            
            update_progress(1.0)
            
            # Cleanup
            self.log("Cleaning up temporary files...")
            try:
                # Delete generated image
                if os.path.exists(temp_img_path): 
                    os.remove(temp_img_path)
                
                # Delete visualizer video
                if os.path.exists(vis_video_path): 
                    os.remove(vis_video_path)
                
                # Try to clean up any leftover temp files matching pattern
                import glob
                for p in glob.glob(f"temp_*_{current_index}.*"):
                    try: os.remove(p)
                    except: pass
                    
            except Exception as e:
                self.log(f"Cleanup Warning: {e}")

        except Exception as e:
            self.log(f"FAILED: {str(e)}")
            raise e

if __name__ == "__main__":
    app = YouTubeStudioApp()
    app.mainloop()

