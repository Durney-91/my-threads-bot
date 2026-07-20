import os
from datetime import datetime
from fastapi import FastAPI
import google.generativeai as genai
import requests

app = FastAPI()

def get_daily_persona_prompt():
    today_weekday = datetime.now().weekday()
    common_rules = """너는 인스타그램 쓰레드에서 'dune.log'로 활동하는 30대 직장인이야. 무조건 지켜야 할 출력 규칙: 1. 정보의 구체성(★중요★): 유용한 기능이 '정확히 무엇인지' 구체적인 행동이나 명칭을 본문에 확실하게 포함해라. 2. 단어 제한: '디깅', '테크 소식' 같은 억지 유행어 금지. 3. 줄바꿈: 문장이 끝나면 무조건 엔터(줄바꿈)를 쳐라. 4. 말투: 100% 반말 독백 어투만 사용. 5. 명칭: 반려견은 무조건 '내시키'. 6. 이모지: 글 마지막에 딱 한 개만 사용. 7. 중복된 게시물은 피할것 8. 최종 본문만 출력."""
    if today_weekday < 5:
        topic_prompt = "[오늘의 주제: 회사 생활 팁 / 직장인 일상생활] 본문에 명확한 알맹이를 담아 자연스럽게 써줘."
    else:
        topic_prompt = "[오늘의 주제: 주말 일상 / 주말에 알게 된 소소한 정보] 구체적인 내용과 함께 자연스럽게 써줘. (회사 얘기 금지)"
    return common_rules + "\n" + topic_prompt

@app.get("/api/generate")
def generate_bot_content():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    tele_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tele_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not all([gemini_key, tele_token, tele_chat_id]):
        return {"status": "error", "message": "환경변수 세팅이 덜 됐음미다."}
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = get_daily_persona_prompt()
        response = model.generate_content(contents=prompt + "\n\n오늘의 쓰레드 게시글을 생성해줘.")
        threads_text = response.text.strip()
        tele_url = f"https://api.telegram.org/bot{tele_token}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": f"🤖 오늘의 dune.log 추천 글:\n\n{threads_text}"}
        requests.post(tele_url, json=payload)
        return {"status": "success", "text": threads_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}