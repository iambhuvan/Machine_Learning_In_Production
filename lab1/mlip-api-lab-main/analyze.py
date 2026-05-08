import json
import os
from typing import Any, Dict
from litellm import completion


# You can replace these with other models as needed but this is the one we suggest for this lab.
MODEL = "groq/llama-3.3-70b-versatile"

def get_itinerary(destination: str) -> Dict[str, Any]:
    """
    Returns a JSON-like dict with keys:
      - destination
      - price_range
      - ideal_visit_times
      - top_attractions
    """
    # implement litellm call here to generate a structured travel itinerary for the given destination

    # See https://docs.litellm.ai/docs/ for reference.
    
    messages = [
        {"role": "system", "content": "You are a helpful travel assistant. Always respond in valid JSON format."},
        {"role": "user", "content": f"Provide a travel itinerary for {destination}. Include: destination, price_range, ideal_visit_times, and a list of top_attractions."}
    ]
    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
         
    except Exception as e:
        print(f"LiteLLM Error: {e}")
        raise e
