import requests
import json
import time
from datetime import datetime
import os

# 검색 키워드
KEYWORDS = ["캄보디아 tm", "해외 텔레", "해외구인", "ㅌㄹ", "캄보디아x", "동남아 ㅌㄹ", "동남아TM", "해외구인 tm"]

# 텔레그램 설정
TELEGRAM_BOT_TOKEN = "8434863508:AAFZ61AtTHCOTUqCnF3_amMMv6ZPYzNCRS0"
TELEGRAM_CHAT_ID = "6552756191"

# Google Custom Search 설정
GOOGLE_API_KEY = "AIzaSyAq4nsVdls0LICB6a5jsoOUBdvmdgGhtU0"
GOOGLE_CX = "a49fa766d3d5a46a1"
NUM_RESULTS = 10  # 한 번에 가져올 검색 결과 수

# 데이터 저장 파일
RESULT_FILE = "search_results.txt"




# 기존 저장된 URL+제목 불러오기
def load_previous_results():
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

# 새로운 결과 저장 (제목 | URL)
def save_results(results):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        for title, url in results:
            f.write(f"{title} | {url}\n")

# 텔레그램 메시지 전송
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        print(f"텔레그램 전송 start")
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")

# Google Custom Search API 호출 (뉴스 제외 + 커뮤니티 중심)
def google_search_api(keyword, num_results=10):
    results = []
    start_index = 1

    while len(results) < num_results:
        query = f"{keyword} -site:news.google.com -inurl:news"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "start": start_index,
            "num": min(10, num_results - len(results))
        }
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
            data = response.json()

            if "items" not in data:
                break

            for item in data["items"]:
                url = item["link"]
                title = item["title"]
                # URL 필터링: 커뮤니티 관련 페이지만
                if any(k in url for k in ["bbs", "board", "community"]):
                    results.append((title, url))

            start_index += len(data["items"])
            time.sleep(1)
        except Exception as e:
            print(f"검색 오류 ({keyword}): {e}")
            break

    return results

# 메인 로직
def monitor():
    print(f"[{datetime.now()}] 🔍 검색 시작")

     # "제목 | URL" 형태
    previous_results = load_previous_results() 
    new_results = []

    for keyword in KEYWORDS:
        print(f"  - '{keyword}' 검색 중...")
        results = google_search_api(keyword, num_results=NUM_RESULTS)
        for title, url in results:
            line = f"{title} | {url}"
            if line not in previous_results:
                new_results.append((title, url))

    if new_results:
        print(f" 새로운 게시글 {len(new_results)}개 발견!!!!!")
        save_results(new_results)
      #  send_telegram_message("📢 새로운 게시글 발견!\n\n")

        # 텔레그램 메시지 분할 전송
        MAX_LENGTH = 4000
        msg = "새로운 게시글 발견!!!!!\n\n"
        for title, url in new_results:
            entry = f"{title}\n{url}\n\n"
            if len(msg) + len(entry) > MAX_LENGTH:
                send_telegram_message(msg)
                msg = ""
            msg += entry

        print(f" msg :{msg}")

        if msg:
            send_telegram_message(msg)
    else:
        print("새로운 게시글 없음.")

if __name__ == "__main__":
    while True:
        monitor()
        print("⏰ 30분 후 재검색...\n")
        time.sleep(1800)