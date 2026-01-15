import os
import time
import mimetypes
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from config/.env
# Load environment variables from .env in project root
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
env_path = ROOT_DIR / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class GeminiImageGenerator:
    def __init__(self):
        # Use direct os.environ like the old version
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        
        # Model mapping
        self.models = {
            "standard": "gemini-2.5-flash-image",
            "premium": "gemini-3-pro-image-preview"
        }

    def generate_image(self, prompt: str, output_path: str, model_type: str = "standard") -> str:
        """
        Generates an image using Google GenAI SDK and saves it to the output path.
        
        Args:
            prompt: The image description.
            output_path: Path to save the generated image.
            model_type: "standard" or "premium".
            
        Returns:
            The absolute path to the saved image.
        """
        try:
            model_name = self.models.get(model_type, self.models["standard"])
            logger.info(f"Generating image with model: {model_name}")
            logger.info(f"Prompt: {prompt[:100]}...")
            
            # Rate limiting wait (Tier 1 key protection)
            logger.info("Waiting 10 seconds for rate limiting...")
            time.sleep(10) 

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            # CRITICAL: Use GenerateContentConfig with response_modalities
            generate_content_config = types.GenerateContentConfig(
                response_modalities=[
                    "IMAGE",
                    "TEXT",
                ],
            )

            # Use generate_content (non-streaming) for images to ensure we get the full blob
            logger.info("Requesting image generation...")
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=generate_content_config,
            )

            if (
                response.candidates is None
                or not response.candidates
                or response.candidates[0].content is None
                or response.candidates[0].content.parts is None
            ):
                raise Exception("Empty response from API")

            part = response.candidates[0].content.parts[0]
            
            # Check for inline image data
            if part.inline_data and part.inline_data.data:
                data_buffer = part.inline_data.data
                # file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
                
                # Save to file
                with open(output_path, "wb") as f:
                    f.write(data_buffer)
                
                logger.info(f"Image saved to {output_path}")
                return output_path
            elif part.text:
                logger.warning(f"Received text instead of image: {part.text}")
                raise Exception(f"API returned text: {part.text}")

            raise Exception("No image data received from API")

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise

gemini_image_gen = GeminiImageGenerator()
