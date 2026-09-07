import os
import json
import requests
from playwright.sync_api import sync_playwright

URL = "https://tl.plaync.com/en-sg/board/notice/list"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = "state.json"


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"urls": []}


def save_state(urls):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": urls}, f, ensure_ascii=False, indent=2)


def get_articles():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        links = page.locator('a[href*="/board/notice/view?articleId="]')

        articles = []

        for i in range(links.count()):
            link = links.nth(i)

            title = link.inner_text().strip()
            href = link.get_attribute("href")

            if title and href:
                if href.startswith("/"):
                    href = "https://tl.plaync.com" + href

                articles.append({
                    "title": title,
                    "url": href
                })

        browser.close()

        # URL重複を除去
        unique = {}
        for article in articles:
            unique[article["url"]] = article

        return list(unique.values())


def send_discord(article):
    payload = {
        "content": (
            "🔔 **THRONE AND LIBERTY 新着記事**\n\n"
            f"**{article['title']}**\n"
            f"{article['url']}"
        )
    }

    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()


def main():
    state = load_state()
    old_urls = set(state.get("urls", []))

    articles = get_articles()

    if not articles:
        print("記事を取得できませんでした。")
        return

    print(f"取得した記事数: {len(articles)}")

    # 初回は現在の記事を記録するだけ
    if not old_urls:
        urls = [article["url"] for article in articles[:30]]
        save_state(urls)

        print("初回登録完了。既存記事は通知しません。")
        return

    new_articles = [
    article
    for article in articles
    if article["url"] not in old_urls
]


    # 新着記事を古い順に通知
    for article in reversed(new_articles):
        print(f"新着記事: {article['title']}")
        send_discord(article)

    # 最新30件を保存
    urls = [article["url"] for article in articles[:30]]
    save_state(urls)

    print(f"新着通知: {len(new_articles)}件")


if __name__ == "__main__":
    main()
