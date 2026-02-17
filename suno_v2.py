import os
import time
import logging
import threading
import shutil
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

# --- MONKEYPATCH FOR PILLOW 10+ ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Third-party imports
from playwright.sync_api import sync_playwright, Page, expect
from pydub import AudioSegment
from moviepy.editor import (
    AudioFileClip, 
    ImageClip, 
    CompositeVideoClip, 
    VideoFileClip, 
    concatenate_audioclips,
    vfx
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# --- CONFIGURATION ---
# USER MUST UPDATE THIS PATH
CHROME_USER_DATA_DIR = "/home/amine/.config/google-chrome" # Default Linux path, user may need to adjust
HEADLESS_MODE = False
OUTPUT_DIR = os.path.join(os.getcwd(), "output")
CLIENT_SECRET_FILE = 'client_secret_203814077086-45qv2fcskncr13tam0n5gnkhoi03uhlk.apps.googleusercontent.com.json'
TOKEN_FILE = 'token.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/youtube.upload'
]

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("suno_v2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SunoBot:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def _create_profile_snapshot(self, source_dir: str) -> str:
        """
        Creates a temporary copy of the Chrome profile to bypass the singleton lock.
        Ignores heavy cache directories to speed up copying.
        """
        temp_dir = tempfile.mkdtemp(prefix="suno_chrome_profile_")
        logger.warning(f"Chrome profile is locked. Creating a temporary snapshot in {temp_dir}...")
        logger.warning("This may take 10-20 seconds. Please wait...")

        try:
            # Define what to ignore to make it fast
            def ignore_patterns(path, names):
                ignore_list = [
                    'Cache', 'Code Cache', 'GPUCache', 'ShaderCache', 'GrShaderCache',
                    'DawnCache', 'Service Worker', 'CacheStorage', 'ScriptCache', 
                    'History', 'History-journal', 'Safe Browsing', 'Crashpad'
                ]
                # Filter matching names
                return [n for n in names if n in ignore_list or n.startswith("Cache")]

            shutil.copytree(source_dir, temp_dir, ignore=ignore_patterns, dirs_exist_ok=True, symlinks=True)
            logger.info("Profile snapshot created successfully.")
            return temp_dir
        except Exception as e:
            logger.error(f"Failed to copy profile: {e}")
            # If copy fails, fallback to None and try fresh (or error out)
            return None

    def run_generation(self, prompt: str, count: int = 4):
        """
        Navigates to Suno, prompts for generation, and downloads files.
        """
        logger.info("Starting Suno Automation...")
        downloaded_files = []
        
        p = sync_playwright().start()
        user_data_dir = CHROME_USER_DATA_DIR
        using_temp_profile = False
        context = None

        try:
            # 1. Try launching with original profile
            try:
                logger.info(f"Attempting to launch browser with profile: {user_data_dir}")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=HEADLESS_MODE,
                    args=["--disable-blink-features=AutomationControlled"],
                    accept_downloads=True,
                    timeout=10000 # Short timeout for initial lock check
                )
            except Exception as e:
                # 2. Check for Lock Error
                error_msg = str(e)
                if "SingletonLock" in error_msg or "File exists" in error_msg or "executable doesn't exist" not in error_msg: 
                    # If it's a lock error (File exists for SingletonLock), try snapshot
                    logger.warning(f"Profile locked ({error_msg}). attempting snapshot fallback...")
                    
                    snapshot = self._create_profile_snapshot(CHROME_USER_DATA_DIR)
                    if snapshot:
                        user_data_dir = snapshot
                        using_temp_profile = True
                        logger.info(f"Retrying with snapshot: {user_data_dir}")
                        context = p.chromium.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=HEADLESS_MODE,
                            args=["--disable-blink-features=AutomationControlled"],
                            accept_downloads=True
                        )
                    else:
                        raise e # Re-raise if snapshot failed
                else:
                    raise e # Re-raise other errors
            
            # --- Browser Automation Logic ---
            page = context.new_page()
            try:
                logger.info(f"Navigating to Suno Create page...")
                page.goto("https://suno.com/create", timeout=60000)
                
                logger.info("Waiting for prompt input...")
                
                # Robust Selector Logic
                # Try finding textarea by placeholder
                prompt_box = page.get_by_placeholder("Song description", exact=False).first
                if not prompt_box.is_visible():
                     # Fallback 2: "Enter your own lyrics" (Custom Mode)
                     prompt_box = page.get_by_placeholder("Enter your own lyrics").first
                
                if not prompt_box.is_visible():
                    # Fallback 3: Generic Textarea
                    prompt_box = page.locator("textarea").first
                
                # Loop for generations
                generations_needed = (count + 1) // 2 
                
                for i in range(generations_needed):
                    logger.info(f"Triggering Generation Batch {i+1}/{generations_needed}...")
                    
                    prompt_box.click()
                    prompt_box.fill(prompt)
                    
                    # Click Create
                    create_btn = page.get_by_role("button", name="Create", exact=True).last
                    if not create_btn.is_visible():
                        create_btn = page.get_by_text("Create").last
                    
                    create_btn.click()
                    page.wait_for_timeout(5000)
                
                logger.info("Waiting for generations to complete (approx 60s)...")
                # Wait longer for generation
                page.wait_for_timeout(60000) 
                
                # Downloading
                logger.info("Starting Download sequence...")
                page.reload()
                page.wait_for_timeout(5000)
                
                # Download Logic
                more_buttons = page.get_by_label("More actions").all()
                logger.info(f"Found {len(more_buttons)} songs available.")
                
                if len(more_buttons) == 0:
                     # Fallback: try finding by 3-dots class or similar if aria-label fails
                     # But for now, just log warning
                     pass

                files_to_download = min(len(more_buttons), count)
                
                for i in range(files_to_download):
                    logger.info(f"Downloading song {i+1}...")
                    buttons = page.get_by_label("More actions").all()
                    if i >= len(buttons): break
                    
                    buttons[i].click()
                    
                    # Click Download
                    page.get_by_text("Download", exact=True).click()
                    
                    # Click Audio
                    with page.expect_download() as download_info:
                        page.get_by_text("Audio", exact=True).click()
                    
                    download = download_info.value
                    fname = f"song_{int(time.time())}_{i}.mp3"
                    save_path = os.path.join(self.output_dir, fname)
                    download.save_as(save_path)
                    downloaded_files.append(save_path)
                    logger.info(f"Saved: {save_path}")
                    
                    # Close menu
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

            except Exception as e:
                logger.error(f"Suno Automation Error: {e}")
                page.screenshot(path="error_suno.png")
            finally:
                if context: context.close()
        
        except Exception as e:
            logger.error(f"Playwright Context Launch Error: {e}")
            if "SingletonLock" in str(e): 
                logger.critical("Failed to launch context due to lock. Please close Chrome manually.")
        
        finally:
            p.stop()
            if using_temp_profile and user_data_dir and os.path.exists(user_data_dir):
                try:
                    logger.info(f"Cleaning up temporary profile: {user_data_dir}")
                    shutil.rmtree(user_data_dir)
                except:
                    pass

        return downloaded_files

class MediaProcessor:
    def __init__(self):
        pass

    def merge_audio(self, file_paths: List[str], crossfade_ms: int = 2000) -> str:
        """
        Merges MP3s with crossfade. Returns path to merged file.
        """
        if not file_paths:
            raise ValueError("No audio files provided for merging.")
            
        logger.info(f"Merging {len(file_paths)} audio files...")
        combined = AudioSegment.empty()
        
        # Sort to ensure order (optional, but good if numbered)
        file_paths.sort()
        
        for i, path in enumerate(file_paths):
            logger.info(f"Processing: {os.path.basename(path)}")
            audio = AudioSegment.from_file(path)
            
            if i == 0:
                combined = audio
            else:
                # Appends with crossfade
                combined = combined.append(audio, crossfade=crossfade_ms)
        
        output_path = os.path.join(OUTPUT_DIR, f"merged_mix_{int(time.time())}.mp3")
        combined.export(output_path, format="mp3")
        logger.info(f"Merged audio saved to {output_path}")
        return output_path

    def _generate_visualizer_layer(self, audio_path: str, duration: float) -> str:
        """
        Generates a transparent visualizer video using FFmpeg.
        """
        vis_path = audio_path.replace(".mp3", "_vis.mov") #.mov for alpha if supported, or just mp4 with black bg to screen
        # Using MP4 with black background is safer for MoviePy composition (using 'screen' blending or ColorKey)
        vis_path = audio_path.replace(".mp3", "_vis.mp4")
        
        logger.info(f"Generating visualizer overlay: {vis_path}")
        
        # FFmpeg command for waveform
        # showwaves is fast. mode=line. 
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", "showwaves=s=1280x300:mode=line:colors=cyan,format=yuv420p", 
            "-c:v", "libx264", "-preset", "ultrafast",
            vis_path
        ]
        
        import subprocess
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return vis_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg Visualizer generation failed: {e}")
            return None

    def create_video(self, audio_path: str) -> str:
        """
        Creates video with background and visualizer.
        """
        logger.info(f"Creating Video from {audio_path}...")
        
        try:
            # Load Audio
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 1. Background
            # Use a solid color or gradient if no image. 
            # Or generate/load one. For v2.0, let's create a nice generated gradient using PIL or just a solid color.
            # User asked for "Static background image".
            bg_path = os.path.join(OUTPUT_DIR, "background.jpg")
            self._create_background_image(bg_path)
            
            bg_clip = ImageClip(bg_path).set_duration(duration).resize((1280, 720))
            
            # 2. Visualizer Overlay
            vis_video_path = self._generate_visualizer_layer(audio_path, duration)
            if vis_video_path and os.path.exists(vis_video_path):
                vis_clip = VideoFileClip(vis_video_path)
                # Loop visualizer if it's shorter (unlikely for showwaves of full audio) or trim
                vis_clip = vis_clip.set_duration(duration)
                
                # Position: Bottom center
                vis_clip = vis_clip.set_position(("center", "bottom"))
                
                # Blend: Screen mode to remove black background
                # MoviePy CompositeVideoClip supports masking. 
                # Simplest is to make black transparent.
                vis_clip = vis_clip.fx(vfx.mask_color, color=[0,0,0], thr=20, s=5)
                
                final_video = CompositeVideoClip([bg_clip, vis_clip], size=(1280, 720))
            else:
                logger.warning("Visualizer failed, using clean background.")
                final_video = bg_clip
            
            final_video = final_video.set_audio(audio_clip)
            
            output_video_path = audio_path.replace(".mp3", "_final_video.mp4")
            
            # Write video file using threads
            logger.info("Writing video file (this may take time)...")
            final_video.write_videofile(
                output_video_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=24, 
                preset='ultrafast',
                threads=4, # Multithreading
                logger='bar' # Show progress bar in console
            )
            
            # Cleanup temp
            if vis_video_path and os.path.exists(vis_video_path):
                os.remove(vis_video_path)
                
            return output_video_path
            
        except Exception as e:
            logger.error(f"Video Creation Error: {e}")
            raise e

    def _create_background_image(self, path: str):
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (1280, 720), color=(10, 10, 20))
        d = ImageDraw.Draw(img)
        # Simple gradient-like effect
        for i in range(720):
            color = (10, 10 + int(i/10), 20 + int(i/5))
            d.line([(0, i), (1280, i)], fill=color)
        img.save(path)


class Uploader:
    def __init__(self):
        self.creds = self._get_credentials()

    def _get_credentials(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        return creds

    def upload_drive(self, file_path: str):
        logger.info(f"Uploading {file_path} to Drive...")
        try:
            service = build('drive', 'v3', credentials=self.creds)
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': ['1vthP0uvSTlISxuV2EJcy-sdcCSB0cMP2'] # Using ID from previous script
            }
            media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            logger.info(f"Drive Upload Success. File ID: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            logger.error(f"Drive Upload Error: {e}")
            raise e

    def upload_youtube(self, file_path: str, title: str, description: str):
        logger.info(f"Uploading {file_path} to YouTube...")
        try:
            youtube = build('youtube', 'v3', credentials=self.creds)
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': ["AI Music", "Suno", "Generated"],
                    'categoryId': '10'  # Music
                },
                'status': {
                    'privacyStatus': 'private', # Defaulting to Private
                    'selfDeclaredMadeForKids': False
                }
            }
            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")
            
            logger.info(f"YouTube Upload Success! Video ID: {response['id']}")
            return response['id']
        except Exception as e:
            logger.error(f"YouTube Upload Error: {e}")
            raise e

def main():
    logger.info("Initializing Suno v2.0 Workflow")
    
    # 0. User Prompt
    prompt = input("Enter Song Prompt or press Enter for default: ").strip() or "Energetic cinematic soundtrack"
    logger.info(f"Using prompt: {prompt}")

    # 1. Suno
    bot = SunoBot()
    try:
        files = bot.run_generation(prompt, count=4)
        pass # Allow logic below to run even if empty list returned directly (handled)
    except Exception as e:
        logger.error(f"Suno generation failed: {e}")
        files = []
    
    # Check for local files if Suno skipped/failed or in testing mode
    if not files:
        logger.warning("No files downloaded from Suno run. Checking /output for existing new files.")
        # Try to find recentmp3s
        all_files = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp3')]
        files = sorted(all_files, key=os.path.getctime, reverse=True)[:4]
        
    if not files or len(files) < 1:
        logger.error("No audio files found to process. Exiting.")
        return
        
    logger.info(f"Processing {len(files)} files: {files}")

    # 2. Media
    try:
        processor = MediaProcessor()
        merged_audio = processor.merge_audio(files)
        video_path = processor.create_video(merged_audio)
    except Exception as e:
        logger.error(f"Media processing failed: {e}")
        return

    # 3. Upload
    try:
        uploader = Uploader()
        uploader.upload_drive(video_path)
        
        title = f"AI Mix: {prompt[:30]}... ({datetime.now().strftime('%Y-%m-%d')})"
        desc = f"Generated by Suno v2.0 Automation.\nPrompt: {prompt}\n"
        uploader.upload_youtube(video_path, title, desc)
    except Exception as e:
        logger.error(f"Upload failed: {e}")

if __name__ == "__main__":
    main()
