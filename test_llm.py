import os
import litellm
import dotenv

dotenv.load_dotenv()

models = ["gemini/gemini-1.5-flash-001", "gemini/gemini-pro", "gemini/gemini-1.0-pro"]
for m in models:
    try:
        response = litellm.completion(
            model=m,
            messages=[{"role": "user", "content": "hello"}],
        )
        print(f"Success with {m}: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error with {m}: {e}")
