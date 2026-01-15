import os
import time
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env in root directory
# Robust validation: Find .env relative to this file to support running from any CWD
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
env_path = ROOT_DIR / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class GeminiTextGenerator:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-3-pro-preview" 

    def generate_text(self, prompt: str, temperature: float = 0.7, enable_search: bool = False) -> str:
        """
        Generates text using Google GenAI SDK.
        
        Args:
            prompt: The text prompt.
            temperature: Creativity control.
            
        Returns:
            The generated text.
        """
        try:
            logger.info(f"Generating text with model: {self.model}")
            
            # Rate limiting wait (Tier 1 key protection)
            # logger.info("Waiting 2 seconds for rate limiting...")
            # time.sleep(2) 

            config_args = {"temperature": temperature}
            
            if enable_search:
                # Enable Google Search Grounding
                config_args["tools"] = [types.Tool(google_search=types.GoogleSearch())]

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_args)
            )
            
            if response.text:
                return response.text
            
            raise Exception("Empty response from API")

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise

gemini_text_gen = GeminiTextGenerator()
