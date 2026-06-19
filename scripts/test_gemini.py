import httpx
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")

def test_v1():
    print(f"Testing Gemini v1...")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    try:
        response = httpx.post(url, json=payload, timeout=10)
        print(f"v1 Status: {response.status_code}")
        if response.status_code == 200:
            print("v1 SUCCESS")
        else:
            print(f"v1 Error: {response.text}")
    except Exception as e:
        print(f"v1 Exception: {e}")

def test_v1beta_flash():
    print(f"\nTesting Gemini v1beta gemini-1.5-flash...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    try:
        response = httpx.post(url, json=payload, timeout=10)
        print(f"v1beta Flash Status: {response.status_code}")
        if response.status_code == 200:
            print("v1beta Flash SUCCESS")
        else:
            print(f"v1beta Flash Error: {response.text}")
    except Exception as e:
        print(f"v1beta Flash Exception: {e}")

if __name__ == "__main__":
    test_v1()
    test_v1beta_flash()
