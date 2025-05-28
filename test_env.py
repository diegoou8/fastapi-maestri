from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).parent.parent / ".env"
print("Looking for .env at:", env_path)

if env_path.exists():
    print("✅ .env file found. Contents:")
    print(env_path.read_text())
else:
    print("❌ .env file not found!")

load_dotenv(dotenv_path=env_path)
print("✅ ENV KEY FOUND?:", os.getenv("OPENAI_API_KEY"))
