import os
import sys
import time
from dotenv import load_dotenv
from litellm import completion
import litellm

# Load environment variables from .env file if present
load_dotenv()

def query_llm(prompt, model="groq/llama-3.3-70b-versatile", temperature=0.7, retries=5):
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("Error: LITELLM_API_KEY environment variable not set.")
        print("Please set it directly or create a .env file with LITELLM_API_KEY=your-key")
        sys.exit(1)

    for attempt in range(retries):
        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in safety engineering and risk analysis for AI-enabled systems."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                api_key=api_key
            )
            return response.choices[0].message.content
        except litellm.RateLimitError as e:
            wait_time = (2 ** attempt) + 1  # Exponential backoff: 2s, 3s, 5s, 9s, 17s
            print(f"Rate limit hit. Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Error querying LLM: {e}")
            sys.exit(1)
    
    print("Error: Max retries exceeded for LLM query.")
    sys.exit(1)
