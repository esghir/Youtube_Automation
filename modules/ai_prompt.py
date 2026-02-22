import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def configure_gemini():
    """Configures the Gemini API with the key from .env"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def generate_music_prompt(style_name):
    """
    Generates a 200-character music prompt for Suno AI using Google Gemini.
    
    Args:
        style_name (str): The name of the music style (e.g., "Calm song").
        
    Returns:
        str: A concise, optimized prompt for Suno AI.
    """
    try:
        configure_gemini()
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        system_instruction = (
            "You are a professional music curator for Suno AI. "
            "Write a high-quality, concise song description including instruments, mood, and tempo. "
            "The output must be optimized for Suno AI and strictly under 200 characters."
        )
        
        user_prompt = f"Write a prompt for a song in this style: '{style_name}'. Make it unique and catchy."
        
        response = model.generate_content(f"{system_instruction}\n\n{user_prompt}")
        
        # Clean up the response
        prompt_text = response.text.strip()
        
        # Ensure it's under 200 chars (truncate if necessary, though Gemini usually obeys)
        if len(prompt_text) > 200:
            prompt_text = prompt_text[:197] + "..."
            
        return prompt_text
        
    except Exception as e:
        print(f"Error generating prompt with Gemini: {e}")
        return f"A {style_name} song with high quality production." # Fallback

if __name__ == "__main__":
    # Test the function
    print(generate_music_prompt("Cha3bi"))
