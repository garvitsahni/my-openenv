import os
import openai
import dotenv

dotenv.load_dotenv()

models = ["gemini/gemini-2.0-flash", "gemini/gemini-pro"]
for m in models:
    try:
        client = openai.OpenAI(
            base_url=os.environ.get("API_BASE_URL"),
            api_key=os.environ.get("API_KEY", "dummy")
        )
        response = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.0
        )
        print(f"Success with {m}: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error with {m}: {e}")
