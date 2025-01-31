import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# OpenAI Configuration
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env")

client = OpenAI(api_key=api_key)

# FastAPI App
app = FastAPI()

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 10))


# Rate Limiter Class
class RateLimiter:
    def __init__(self, rate_limit_per_minute):
        self.rate_limit = rate_limit_per_minute
        self.requests = defaultdict(list)

    def is_rate_limited(self, client_id: str) -> bool:
        now = datetime.now()
        self.requests[client_id] = [
            timestamp
            for timestamp in self.requests[client_id]
            if timestamp > now - timedelta(minutes=1)
        ]
        if len(self.requests[client_id]) >= self.rate_limit:
            return True
        self.requests[client_id].append(now)
        return False


rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)


@app.get("/")
async def health_check():
    return {"status": "Chatbot API Running"}


@app.post("/chat")
async def chat(request: Request):
    client_id = request.client.host
    if rate_limiter.is_rate_limited(client_id):
        return {
            "role": "assistant",
            "content": "Rate limit exceeded. Try again later.",
            "error": True,
        }

    try:
        data = await request.json()
        message = data.get("message", "")
        prompt = data.get("prompt", "")

        response = client.chat.completions.create(
            model="chatgpt-4o-latest",  # Or your preferred model
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
        )
        reply = response.choices[0].message.content
        return {"role": "assistant", "content": reply}

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return {
            "role": "assistant",
            "content": "An unexpected error occurred. Please try again later.",
            "error": True,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8203)),
    )
