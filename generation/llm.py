import os
import requests
import json
from openai import OpenAI
from .prompts import PROMPT_TEMPLATE
from dotenv import load_dotenv

load_dotenv()

def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """
    Generates an answer using Gemini (via REST) or OpenAI based on available keys.
    """
    if not context_chunks:
        return "Information not available in the document."
        
    context_text = "\n\n".join([c['chunk'] for c in context_chunks])
    prompt = PROMPT_TEMPLATE.format(context=context_text, question=question)

    # DEBUG LOGGING
    print(f"\n--- LLM PROMPT DEBUG ---")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print(f"------------------------\n")

    # 1. Try Google Gemini (REST API)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-001:generateContent?key={gemini_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            # Robust retry mechanism for 429 errors
            max_retries = 5
            for attempt in range(max_retries):
                response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract text from response
                    try:
                        return data['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                         return f"Unexpected Gemini response format: {response.text}"
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 3, 6, 12, 24, 48 seconds
                        wait_time = (2 ** attempt) * 3
                        import time
                        print(f"Quota exceeded. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return f"Gemini API Error {response.status_code} (Quota Exceeded after {max_retries} retries): {response.text}"
                else:
                     return f"Gemini API Error {response.status_code}: {response.text}"
                 
        except Exception as e:
            return f"Error generating answer with Gemini REST: {str(e)}"

    # 2. Try OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating answer with OpenAI: {str(e)}"

    return "Error: No API key found. Please set GEMINI_API_KEY or OPENAI_API_KEY."
