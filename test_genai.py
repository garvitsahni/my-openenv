import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print("Key:", api_key[:10] if api_key else "None")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    print("Models:")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
