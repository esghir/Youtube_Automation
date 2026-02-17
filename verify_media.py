import PIL.Image
import PIL.ImageDraw
import subprocess
import os

# Test Image Creation
def create_test_image():
    img = PIL.Image.new('RGB', (1280, 720), color=(50, 50, 100))
    d = PIL.ImageDraw.Draw(img)
    d.text((100, 300), "TEST IMAGE", fill=(255, 255, 255))
    img.save("test_input.jpg")
    print("Created test_input.jpg")

# Test Circular Logic
def test_circular_crop():
    original_img = PIL.Image.open("test_input.jpg").convert("RGB")
    
    # Square Crop
    w, h = original_img.size
    min_dim = min(w, h)
    center_x, center_y = w // 2, h // 2
    left = center_x - min_dim // 2
    top = center_y - min_dim // 2
    right = center_x + min_dim // 2
    bottom = center_y + min_dim // 2
    
    square_img = original_img.crop((left, top, right, bottom))
    square_img = square_img.resize((500, 500), PIL.Image.LANCZOS)
    
    # Mask
    mask = PIL.Image.new("L", (500, 500), 0)
    draw = PIL.ImageDraw.Draw(mask)
    draw.ellipse((10, 10, 490, 490), fill=255)
    
    circular_img = PIL.Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    circular_img.paste(square_img, (0, 0), mask=mask)
    
    circular_img.save("test_circle_output.png")
    print("Created test_circle_output.png")

# Test FFmpeg Avectorscope
def test_ffmpeg_visualizer():
    # Generate dummy audio
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=5", "test_audio.mp3"], check=True)
    
    # Run Filter
    cmd = [
        "ffmpeg", "-y",
        "-i", "test_audio.mp3",
        "-filter_complex", "avectorscope=s=1280x720:rate=24:zoom=1.3:rc=0:gc=200:bc=255:rf=0:gf=0:bf=0,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast",
        "test_visualizer.mp4"
    ]
    subprocess.run(cmd, check=True)
    print("Created test_visualizer.mp4")

if __name__ == "__main__":
    create_test_image()
    test_circular_crop()
    test_ffmpeg_visualizer()
