"""
google_search_to_telegram.py

설명:
 - Google Custom Search API로 검색 결과를 가져와 CSV와 TXT로 저장한 뒤
   Telegram bot을 통해 파일(문서)로 전송합니다.
 - API 키가 없는 경우 (권장하지 않음) 구글 HTML을 직접 스크래핑하는 대체 함수도 포함되어 있습니다.
"""

import os
import time
import csv
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()  # .env 파일 사용 시

GOOGLE_API_KEY = "AIzaSyAq4nsVdls0LICB6a5jsoOUBdvmdgGhtU0"
GOOGLE_CX = "a49fa766d3d5a46a1"
TELEGRAM_BOT_TOKEN = "8434863508:AAFZ61AtTHCOTUqCnF3_amMMv6ZPYzNCRS0"
TELEGRAM_CHAT_ID = "938756986"

# ------------------------
# 유틸: Google Custom Search API 방식
# ------------------------
def google_cse_search(query: str, api_key: str, cx: str, num_results: int = 10, delay: float = 1.0) -> List[Dict[str, Any]]:
    """
    Google Custom Search API로 query에 대한 결과를 수집.
    num_results는 최대 100까지(실무에서는 10씩 페이징).
    """
    results = []
    per_page = 10  # CSE 기본값
    start = 1
    while len(results) < num_results:
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "start": start,
            "num": min(per_page, num_results - len(results))
        }
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"CSE API error: {resp.status_code} {resp.text}")
        data = resp.json()
        items = data.get("items", [])
        for it in items:
            results.append({
                "title": it.get("title"),
                "link": it.get("link"),
                "snippet": it.get("snippet")
            })
        # paging
        start += per_page
        time.sleep(delay)
        if not items:
            break
    return results

# ------------------------
# 대체 유틸: (주의) Google HTML 직접 스크래핑 (차단됨/비권장)
# ------------------------
def google_html_scrape(query: str, num_results: int = 10, delay: float = 1.0) -> List[Dict[str, Any]]:
    """
    Google 검색 페이지 HTML을 파싱하는 간단한 스크래퍼.
    주의: Google의 robots/ToS에 위배될 수 있으며, 차단될 수 있습니다.
    권장: 가능한 경우 Custom Search API 사용.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0 Safari/537.36"
    }
    results = []
    start = 0
    while len(results) < num_results:
        url = "https://www.google.com/search"
        params = {"q": query, "num": 10, "start": start, "hl": "ko"}
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Google HTML fetch error: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        # 결과 선택자 (Google은 자주 바뀝니다)
        for g in soup.select("div.g"):
            a = g.find("a", href=True)
            title_tag = g.find("h3")
            snippet_tag = g.select_one("div.IsZvec") or g.select_one("span.aCOpRe")
            if a and title_tag:
                link = a["href"]
                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                results.append({"title": title, "link": link, "snippet": snippet})
                if len(results) >= num_results:
                    break
        start += 10
        time.sleep(delay)
        if start >= 100:  # 안전장치
            break
    return results

# ------------------------
# 파일 저장( CSV, TXT )
# ------------------------
def save_results(results: List[Dict[str, Any]], base_filename: str):
    df = pd.DataFrame(results)
    csv_path = f"{base_filename}.csv"
    txt_path = f"{base_filename}.txt"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    # TXT: 간단한 라인별 요약
    with open(txt_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(results, start=1):
            f.write(f"{i}. {r.get('title')}\n{r.get('link')}\n{r.get('snippet')}\n\n")
    return csv_path, txt_path

# ------------------------
# 텔레그램으로 파일 전송
# ------------------------
def send_file_to_telegram(bot_token: str, chat_id: str, file_path: str, caption: Optional[str] = None):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(url, data=data, files=files, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram API error: {resp.status_code} {resp.text}")
    return resp.json()

# ------------------------
# 메인 함수: 키워드 목록 처리
# ------------------------
def crawl_keywords_and_send(
    keywords: List[str],
    use_api: bool = True,
    results_per_keyword: int = 20,
    delay_between_requests: float = 1.0,
    output_prefix: str = "search_results"
):
    all_files = []
    for kw in keywords:
        safe_kw = kw.replace(" ", "_")[:40]
        base_name = f"{output_prefix}_{safe_kw}"
        print(f"[+] 처리: {kw}")
        if use_api and GOOGLE_API_KEY and GOOGLE_CX:
            try:
                results = google_cse_search(kw, GOOGLE_API_KEY, GOOGLE_CX, num_results=results_per_keyword, delay=delay_between_requests)
            except Exception as e:
                print(f"[!] CSE 실패: {e} — HTML 스크래핑 시도")
                results = google_html_scrape(kw, num_results=results_per_keyword, delay=delay_between_requests)
        else:
            print("[!] Google API 키/설정이 없거나 use_api=False — HTML 스크래핑 사용 (비권장)")
            results = google_html_scrape(kw, num_results=results_per_keyword, delay=delay_between_requests)

        csv_path, txt_path = save_results(results, base_name)
        print(f"    -> 저장: {csv_path}, {txt_path}")
        all_files.append((csv_path, txt_path))
        # 텔레그램에 전송 (CSV 파일 우선)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                send_resp = send_file_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_path, caption=f"Search results for: {kw}")
                print(f"    -> Telegram 전송 성공: {csv_path}")
            except Exception as e:
                print(f"    -> Telegram 전송 실패: {e}")
        else:
            print("    -> TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되어 있지 않습니다. 전송 건너뜁니다.")
    return all_files

# ------------------------
# 실행 예시
# ------------------------
if __name__ == "__main__":
    # 예시: 키워드 리스트
    keywords_to_search = [
        "tm",
        "tm 구인",
        "ㅌㄹ",
        "출국장",
        "해외구직",
        "캄보디아x",
        {"tm", "ㅌㄹ"}
    ]

    # 설정: API 사용 권장. 없으면 HTML 스크래핑 사용(차단 가능).
    USE_API = True  # False로 설정하면 무조건 HTML 스크래핑

    # 한 키워드당 가져올 결과 수
    RESULTS_PER_KEYWORD = 20

    # 실행
    try:
        files = crawl_keywords_and_send(
            keywords=keywords_to_search,
            use_api=USE_API,
            results_per_keyword=RESULTS_PER_KEYWORD,
            delay_between_requests=1.0,
            output_prefix="google_search"
        )
        print("모든 작업 완료. 생성된 파일:")
        for csvp, txtp in files:
            print(f" - {csvp}, {txtp}")
    except Exception as exc:
        print("오류 발생:", exc)
