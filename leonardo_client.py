import requests
import json
import time
import logging
from typing import Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def leonardo_text_to_image(prompt: str, parameters: Dict[str, Any], api_key: str) -> Optional[Dict[str, Any]]:
    """
    Call Leonardo API for text-to-image generation
    
    Args:
        prompt (str): The text prompt for image generation
        parameters (Dict[str, Any]): Generation parameters
        api_key (str): Leonardo API key
        
    Returns:
        Optional[Dict[str, Any]]: Generation result or None if failed
    """
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    payload = {
        "modelId": "b63f7119-31dc-4540-969b-2a9df997e173",  # "SDXL 0.9"
        "prompt": prompt,
        "enhancePrompt": True,
        "num_images": 1,
        "width": 512,
        "height": 512,
        "alchemy": True,
        "photoReal": True,
        "photoRealVersion": "v2",
        "presetStyle": "LONG_EXPOSURE"
    }
    
    try:
        logger.info("Starting image generation...")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
        
        # First create the generation
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the response for debugging
        logger.debug(f"Initial API Response: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"API Error: Status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
        generation_data = response.json()
        
        # Get the generation ID from the nested structure
        generation_id = generation_data.get("sdGenerationJob", {}).get("generationId")
        if not generation_id:
            logger.error("Failed to get generation ID from API")
            logger.error(f"Full response: {generation_data}")
            return None
            
        logger.info(f"Generation ID received: {generation_id}")
            
        # Poll for the generation result
        status_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        max_attempts = 30  # 30 seconds maximum wait time
        attempt = 0
        
        # Create a progress bar
        
        while attempt < max_attempts:
            status_response = requests.get(status_url, headers=headers)
            
            if status_response.status_code != 200:
                logger.error(f"Status check failed: {status_response.status_code}")
                logger.error(f"Response: {status_response.text}")
                return None
                
            status_data = status_response.json()
            logger.debug(f"Status check {attempt + 1}/{max_attempts}")
            
            # Update progress
            progress = min(1.0, (attempt + 1) / max_attempts)
           
            
            if status_data['generations_by_pk']['status'] == "COMPLETE":
                logger.info("Generation completed successfully!")
                return status_data
            elif status_data['generations_by_pk']['status'] == "FAILED":
                logger.error("Generation failed!")
                logger.error(f"Generation failed: {status_data.get('error')}")
                return None
                
            time.sleep(1)  # Wait 1 second before next poll
            attempt += 1
            
        logger.error("Generation timed out")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse API response: {str(e)}")
        logger.error(f"Raw response: {response.text}")
        return None

if __name__ == "__main__":
    prompt = '''Arujuna Shooting an Arrow in the battlefield of Mahabharata. Arjuna is an Hindu Warrior'''
    parameters = {
        "width": 768,
        "height": 1024,
        "num_images": 1
    }
    api_key = "886efd6d-cfb1-4517-8876-abd09a0740a4"


   
    result = leonardo_text_to_image(prompt, parameters, api_key)
    print(result)
    