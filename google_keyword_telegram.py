import requests
from bs4 import BeautifulSoup
import csv
import time
import urllib.parse
import telegram

# ✅ 사용자 설정
KEYWORD = "캄보디아 구인"
NUM_PAGES = 3  # 검색 페이지 수 (10개 결과 × 3페이지 = 약 30개)
OUTPUT_FILE = f"google_search_{KEYWORD}.csv"

# ✅ 텔레그램 설정
TELEGRAM_BOT_TOKEN = "8434863508:AAFZ61AtTHCOTUqCnF3_amMMv6ZPYzNCRS0"
TELEGRAM_CHAT_ID = "938756986"

def google_search_scrape(keyword, num_pages=1):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }

    for page in range(num_pages):
        start = page * 10
        query = urllib.parse.quote_plus(keyword)
        url = f"https://www.google.com/search?q={query}&start={start}"

        print(f"[+] 페이지 {page+1} 크롤링 중... ({url})")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for g in soup.select("div.tF2Cxc"):
            title_tag = g.select_one("h3")
            link_tag = g.select_one("a")
            if title_tag and link_tag:
                title = title_tag.text.strip()
                link = link_tag["href"]
                results.append({"title": title, "link": link})

        time.sleep(2)  # 구글 차단 방지용 딜레이

    return results


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "link"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"[✔] CSV 파일 저장 완료: {filename}")


def send_to_telegram(file_path):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    with open(file_path, "rb") as f:
        bot.send_document(chat_id=TELEGRAM_CHAT_ID, document=f)
    print(f"[📤] 텔레그램 전송 완료: {file_path}")


if __name__ == "__main__":
    data = google_search_scrape(KEYWORD, NUM_PAGES)
    if data:
        save_to_csv(data, OUTPUT_FILE)
        send_to_telegram(OUTPUT_FILE)
    else:
        print("검색 결과가 없습니다.")
