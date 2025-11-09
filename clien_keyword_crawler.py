#!/usr/bin/env python3
"""
clien_keyword_crawler.py
www.clien.net 내부에서 특정 키워드가 포함된 페이지를 찾는 크롤러 (polite, robots.txt 준수).
저작권/이용규약을 준수하여 사용하세요.
"""

import argparse
import csv
import time
import re
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from urllib import robotparser

# 기본 설정
USER_AGENT = "KeywordCrawler/1.0 (+https://github.com/jijoytae) - polite crawler"
DEFAULT_DELAY = 1.0  # 초 (robots.txt에 crawl-delay 없다면 사용)

# 유틸: 동일 도메인 확인
def same_domain(url1, url2):
    return urlparse(url1).netloc == urlparse(url2).netloc

# robots.txt 확인 및 crawl-delay 추출
def get_robots_parser(base_url):
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        # 실패시 모든 경로 허용하는 것으로 간주 (보수적으로 설정 가능)
        rp = None
    return rp

# URL 정규화 (프래그먼트 제거, 절대화)
def normalize_url(base, href):
    if not href:
        return None
    href = href.strip()
    # 자바스크립트 링크 등 무시
    if href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("#"):
        return None
    abs_url = urljoin(base, href)
    abs_url, _ = urldefrag(abs_url)
    return abs_url

# 간단한 텍스트 검색 (키워드 포함 여부)
def page_contains_keyword(text, keyword):
    if text is None:
        return False
    return re.search(re.escape(keyword), text, re.IGNORECASE) is not None

# HTTP 페이지 요청 (타임아웃/재시도 간단 처리)
def fetch_url(url, session, timeout=10, max_retries=2):
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(1 + attempt)  # 백오프
                continue
            else:
                # 실패 최종
                return None

def crawl(start_url, keyword, output_csv, max_pages=None):
    parsed_start = urlparse(start_url)
    base_domain = f"{parsed_start.scheme}://{parsed_start.netloc}"

    rp = get_robots_parser(start_url)
    crawl_delay = DEFAULT_DELAY
    if rp:
        try:
            delay = rp.crawl_delay(USER_AGENT)
            if delay:
                crawl_delay = delay
        except Exception:
            pass

    session = requests.Session()
    to_visit = deque([start_url])
    visited = set()
    found_pages = []

    pages_crawled = 0

    while to_visit:
        url = to_visit.popleft()
        if url in visited:
            continue
        visited.add(url)

        # robots.txt에 의해 차단되면 건너뜀
        if rp and not rp.can_fetch(USER_AGENT, url):
            # print(f"Blocked by robots.txt: {url}")
            continue

        resp = fetch_url(url, session)
        pages_crawled += 1
        if max_pages and pages_crawled > max_pages:
            break

        if resp is None:
            # print(f"Failed to fetch: {url}")
            time.sleep(crawl_delay)
            continue

        content_type = resp.headers.get("Content-Type", "")
        # 텍스트/HTML만 처리
        if "text/html" not in content_type:
            time.sleep(crawl_delay)
            continue

        text = resp.text
        # 키워드 검사 (본문 전체 텍스트에서)
        if page_contains_keyword(text, keyword):
            # 저장: URL, HTTP 상태, 페이지 타이틀 (가능하면), 스니펫
            soup = BeautifulSoup(text, "html.parser")
            title_tag = soup.title.string.strip() if soup.title and soup.title.string else ""
            # 간단 스니펫: 키워드 근처 120자
            m = re.search(r".{0,60}" + re.escape(keyword) + r".{0,60}", text, re.IGNORECASE)
            snippet = m.group(0).strip() if m else (text[:120].replace("\n", " ").strip())
            found_pages.append({"url": url, "title": title_tag, "snippet": snippet})

        # HTML 파싱하여 내부 링크 추가
        soup = BeautifulSoup(text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            norm = normalize_url(url, href)
            if not norm:
                continue
            # 동일 도메인만
            if not same_domain(base_domain, norm):
                continue
            if norm in visited:
                continue
            # robots.txt 체크 미리 (선택)
            if rp and not rp.can_fetch(USER_AGENT, norm):
                continue
            to_visit.append(norm)

        # polite delay
        time.sleep(crawl_delay)

    # 결과 저장 (CSV)
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "snippet"])
        writer.writeheader()
        for row in found_pages:
            writer.writerow(row)

    return found_pages

def main():
    parser = argparse.ArgumentParser(description="Clien keyword crawler (site-internal).")
    parser.add_argument("--start", "-s", default="https://www.clien.net/service/", help="시작 URL (기본 https://www.clien.net/service/)")
    parser.add_argument("--keyword", "-k", required=True, help="검색할 키워드 (필수)")
    parser.add_argument("--output", "-o", default="clien_results.csv", help="결과 CSV 파일명")
    parser.add_argument("--max-pages", type=int, default=None, help="최대 크롤링할 페이지 수 (선택)")
    args = parser.parse_args()

    print(f"Start crawling from {args.start} for keyword '{args.keyword}' ...")
    found = crawl(args.start, args.keyword, args.output, max_pages=args.max_pages)
    print(f"Found {len(found)} pages containing '{args.keyword}'. Saved to {args.output}")

if __name__ == "__main__":
    main()
