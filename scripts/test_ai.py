import os
import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv()

def test_anthropic():
    key = os.getenv("ANTHROPIC_API_KEY")
    # Mask key for printing
    masked = f"{key[:10]}...{key[-5:]}" if key else "None"
    print(f"Testing Anthropic Key: {masked}")
    if not key:
        print("[ERROR] No Anthropic key found")
        return
    
    try:
        # Use the exact model from the app
        model = "claude-3-5-sonnet-20240620"
        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"[SUCCESS] Anthropic ({model}): {message.content[0].text}")
    except Exception as e:
        print(f"[ERROR] Anthropic: {str(e)}")

def test_gemini():
    key = os.getenv("GEMINI_API_KEY")
    masked = f"{key[:5]}...{key[-5:]}" if key else "None"
    print(f"Testing Gemini Key: {masked}")
    if not key:
        print("[ERROR] No Gemini key found")
        return
    
    try:
        # Exact URL pattern from services.py
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": "Hi"}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }
        response = httpx.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            text = res_json['candidates'][0]['content']['parts'][0]['text']
            print(f"[SUCCESS] Gemini: {text.strip()}")
        else:
            print(f"[ERROR] Gemini ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[ERROR] Gemini: {str(e)}")

if __name__ == "__main__":
    print("--- AI Connection Test ---")
    test_anthropic()
    print("\n--- Gemini Test ---")
    test_gemini()
