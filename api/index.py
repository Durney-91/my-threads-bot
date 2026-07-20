import sys
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, BackgroundTasks
import google.generativeai as genai
from playwright.async_api import Page, TimeoutError as PWTimeout, async_playwright

app = FastAPI()

# ── 1. 설정 및 환경변수 ──
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
COOKIE_PATH = Path("/tmp/threads_state.json")
THREADS_URL = "https://www.threads.com/"
PUBLISH_SHORTCUT = "Meta+Enter" if sys.platform == "darwin" else "Control+Enter"

# 제미나이 설정
genai.configure(api_key=GEMINI_API_KEY)
KST = ZoneInfo("Asia/Seoul")

# ── 2. 제미나이 dune.log 페르소나 (중복 금지 조항 반영) ──
POST_COMMON_RULES = """
너는 인스타그램 쓰레드(Threads)에서 'dune.log'라는 닉네임으로 활동하는 30대 직장인이야.
집에서 내시키(반려견) 한 마리를 키우고 있고, 평소에 일상생활이나 업무 속에서 유용한 팁을 발견하고 기록하는 걸 좋아하지.

[무조건 지켜야 할 출력 규칙]
1. ★★★ 중복 게시 절대 금지 (가장 중요) ★★★: 
   - 이전에 작성했던 글들과 소재, 내용, 팁의 종류가 절대 중복되거나 유사해서는 안 된다. 
   - 매번 완전히 새로운 에피소드, 새로운 단축키, 새로운 스마트폰 기능, 혹은 새로운 일상 소재를 들고 와야 한다. 조금이라도 겹치는 뉘앙스가 있으면 안 됨.
2. 정보의 구체성: '유용한 기능을 알아냈다', '꿀팁을 발견했다'처럼 겉핥기식으로만 말하고 알맹이를 빼놓으면 절대로 안 된다. 그 유용한 기능이 '정확히 무엇인지'(예: 아이폰 검색창에 '개'라고 치는 기능, 엑셀 Ctrl+E 기능 등) 구체적인 행동이나 명칭을 본문에 확실하게 포함해서 써라. 독자가 읽고 바로 따라 할 수 있어야 한다.
3. 단어 제한: '디깅', '테크 소식', 'IT 트렌드', '콤퓨타' 같은 억지 유행어나 부자연스러운 단어는 절대 쓰지 마라. 대신 '이것저것 찾아보다가', '유용한 거', '뉴스' 등 일상적인 표현을 써라.
4. 줄바꿈 및 레이아웃: 모든 문장을 한 줄로 붙여 쓰지 마라. 한 문장이나 의미 단위가 끝나면 무조건 엔터(줄바꿈)를 쳐서 행을 분리해라. 전체 글은 2~3줄(2~3행) 구조여야 하며, 각 줄 사이가 시원하게 떨어져야 한다.
5. 말투 제한: 그 어떤 형태의 존댓말(~함미다, ~했슴미다 포함)도 절대 금지한다. 또한 '~냐?', '~라'처럼 훈수 두는 어투도 안 된다. 오직 혼잣말하듯 담백하고 쿨하게 툭 던지는 100% 반말 독백 어투(~했어, ~했네, ~인 듯, ~함)만 사용해라.
6. 명칭: 반려견을 언급할 때는 절대로 '말티푸'나 '강아지', '개'라고 부르지 말고, 무조건 '내시키'라고 불러라. (예: 우리 집 내시키, 내시키 산책 등)
7. 이모지: 글 전체를 통틀어 딱 한 개만 사용하며, 가장 마지막 문장 끝에 붙인다. (추천: 🐾, 🛸, 💼, 🤖, 💻, 😎)
8. 출력 형태: 인사말, 서론, 설명, 따옴표(" ") 모두 제외하고 오직 쓰레드에 복사할 '최종 본문 문장(줄바꿈 포함)'만 출력해.
"""

WEEKDAY_TOPIC = """
[오늘의 주제: 회사 생활 팁 / 직장인 일상생활]
- 직장에서 일하다 알게 된 소소하지만 구체적인 업무 팁(예: 엑셀 특정 단축키나 유용한 기능), 혹은 출퇴근길 일상이나 퇴근 후 내시키와의 에피소드 중 하나를 골라 본문에 명확한 알맹이를 담아 자연스럽게 써줘.
"""

WEEKEND_TOPIC = """
[오늘의 주제: 주말 일상 / 주말에 알게 된 소소한 정보]
- 주말에 집에서 쉬면서 알게 된 유용한 기능이나 실생활 정보(예: 스마트폰 내장 기능 활용법, 생활 꿀팁), 또는 주말에 내시키랑 산책 가거나 침대에서 뒹굴거리는 일상 중 하나를 골라 구체적인 내용과 함께 자연스럽게 써줘. (회사 얘기 금지)
"""

def write_insight_post() -> str:
    weekday = datetime.now(KST).weekday()
    topic = WEEKDAY_TOPIC if weekday < 5 else WEEKEND_TOPIC
    prompt = POST_COMMON_RULES + "\n" + topic
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=prompt,
        # 중복 방지를 위해 무작위성(temperature)을 약간 높이고 매번 다른 글이 나오도록 세팅
        generation_config=genai.GenerationConfig(temperature=0.9, top_p=0.95),
    )
    response = model.generate_content("위 페르소나와 오늘의 주제에 맞춰, 기존 글들과 절대 중복되지 않는 완전히 새로운 글을 규칙대로 딱 하나만 써줘.")
    return (response.text or "").strip()

# ── 3. Playwright 쓰레드 포스팅 기능 ──
async def _click_first(page: Page, candidates: list[dict], timeout: int = 8000) -> bool:
    for cand in candidates:
        try:
            if cand["by"] == "role":
                locator = page.get_by_role(cand["role"], name=cand["name"])
            elif cand["by"] == "text":
                locator = page.get_by_text(cand["name"], exact=cand.get("exact", False))
            else:
                locator = page.locator(cand["selector"])
            await locator.first.wait_for(state="visible", timeout=timeout)
            await locator.first.click()
            return True
        except PWTimeout:
            continue
    return False

async def _type_text(locator, text: str) -> None:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            await locator.press("Shift+Enter")
        if line:
            await locator.type(line, delay=8)

async def publish_post(content: str) -> None:
    if not COOKIE_PATH.exists():
        raise RuntimeError("쿠키 세션 파일이 비어있습니다. 환경변수 설정을 확인하세요.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=str(COOKIE_PATH),
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()
        try:
            await page.goto(THREADS_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)

            if await page.get_by_role("link", name="로그인").count() or \
               await page.get_by_role("button", name="로그인").count():
                raise RuntimeError("쓰레드 로그인 세션이 만료되었습니다.")

            opened = await _click_first(page, [
                {"by": "role", "role": "button", "name": "새로운 스레드 만들기"},
                {"by": "role", "role": "button", "name": "새 스레드"},
                {"by": "role", "role": "button", "name": "만들기"},
                {"by": "role", "role": "button", "name": "Create"},
                {"by": "role", "role": "button", "name": "Post"},
                {"by": "text", "name": "스레드 시작하기..."},
                {"by": "text", "name": "Start a thread..."},
            ])
            if not opened:
                raise RuntimeError("새 글 작성 UI를 열지 못했습니다.")

            await page.wait_for_timeout(1200)
            textbox = page.get_by_role("textbox").last
            await textbox.wait_for(state="visible", timeout=8000)
            await textbox.click()
            await _type_text(textbox, content)
            await page.wait_for_timeout(1000)
            await textbox.press(PUBLISH_SHORTCUT)
            await page.wait_for_timeout(5000)
        except Exception:
            raise
        finally:
            await context.close()
            browser.close()

# ── 4. 버셀 백그라운드 태스크 및 라우터 ──
def cron_job_task():
    try:
        cookie_data = os.environ.get("THREADS_COOKIES", "")
        if cookie_data:
            COOKIE_PATH.write_text(cookie_data, encoding="utf-8")
        
        post_content = write_insight_post()
        import asyncio
        asyncio.run(publish_post(post_content))
        print(f"포스팅 성공: {post_content}")
    except Exception as e:
        print(f"포스팅 실패 에러: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "running", "bot": "dune.log"}

@app.get("/api/cron")
def run_cron(background_tasks: BackgroundTasks):
    background_tasks.add_task(cron_job_task)
    return {"message": "dune.log 스레드 자동 포스팅 작업이 백그라운드에서 시작되었습니다."}
