import os
from fastapi import FastAPI, Request
import telegram
from google import genai

app = FastAPI()

# 환경변수 로드
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 제미나이 및 텔레그램 초기화
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

@app.get("/")
def read_root():
    return {"status": "Threads Bot is running!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    # 여기에 텔레그램 봇 연동 및 제미나이 기능이 작동합니다.
    return {"status": "ok"}
