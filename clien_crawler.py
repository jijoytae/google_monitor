import requests
from bs4 import BeautifulSoup
import time

def crawl_clien(keyword, num_pages=5, output_file="clien_filtered.txt"):
    """
    클리앙 게시판에서 특정 키워드가 포함된 게시글만 크롤링합니다.
    """
    base_url = "https://www.clien.net/service/group/board_all"  # 원하는 게시판 주소
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    results = []

    for page in range(num_pages):
        url = f"{base_url}?&po={page}"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        posts = soup.select("div.list_item.symph_row")

        for post in posts:
            title_tag = post.select_one("span.subject_fixed")
            link_tag = post.select_one("a.list_subject")

            if not (title_tag and link_tag):
                continue

            title = title_tag.get_text(strip=True)
            link = "https://www.clien.net" + link_tag["href"]

            # 키워드 포함된 게시글만 저장
            if keyword.lower() in title.lower():
                results.append(f"{title}\n{link}\n")

        print(f"[{page+1}] 페이지 완료")
        time.sleep(1)

    # 결과 저장
    if results:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n✅ '{keyword}' 키워드 포함된 게시글 {len(results)}건 저장 완료 ({output_file})")
    else:
        print(f"\n❌ '{keyword}' 키워드 포함된 게시글을 찾지 못했습니다.")

if __name__ == "__main__":
    keyword = input("검색할 키워드를 입력하세요: ")
    crawl_clien(keyword, num_pages=10)