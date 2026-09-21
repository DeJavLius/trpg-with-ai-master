import time
from pathlib import Path
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.crawl.util import clear_dir
from trpg_with_ai_master.util import save_file


def crawler(config: CrawlConfig, raw_files: list[Path]):
    crawler_restart_flag = len(raw_files) == 0 or config.do_crawl
    if crawler_restart_flag:
        print(
            f"initial: {'재수집 수행' if config.do_crawl else '수집 파일 없음'}, 최초 수집 시작: {config.raw_path}"
        )
        _target_crawl(config)
    else:
        for raw in raw_files:
            html = raw.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            wrong_check = soup.find_all("h1")

            if len(wrong_check) > 0:
                for w in wrong_check:
                    if w.text == "404":
                        print(
                            "wrong crawl: 파일 중 잘못 크롤링된 파일이 있음. 전역 재수집 시작"
                        )
                        crawler_restart_flag = True
                        break
            else:
                print("empty content: 파일은 있으나 수집된 내용이 없음")
                crawler_restart_flag = True

        if crawler_restart_flag:
            clear_dir(config.raw_path)
            _target_crawl(config)


def _target_crawl(config: CrawlConfig):
    config.raw_path.mkdir(parents=True, exist_ok=True)

    home_html = fetch_handler(config, config.url_keyword)
    links = enroll_all_links(home_html, config.url_keyword)

    for link in links:
        file_name = link.replace(config.url_keyword, "").removesuffix("/")
        page_html = fetch_handler(config, link)
        save_file(
            file_name, config.raw_path / f"{file_name.replace('-', '')}.html", page_html
        )
        time.sleep(1)


def fetch_handler(config: CrawlConfig, link: str) -> str:
    try:
        return _fetch(config.site_url + quote(link), config.user_agent)
    except httpx.HTTPError as e:
        print(e)
        clear_dir(config.raw_path)
        raise httpx.HTTPError("request failed, stop fetching")


def _fetch(url: str, user: str) -> str:
    r = httpx.get(url, follow_redirects=True, timeout=5, headers={"User-Agent": user})
    r.raise_for_status()
    return r.text


def enroll_all_links(home_html: str, target_url: str) -> list[str]:
    soup = BeautifulSoup(home_html, "html.parser")
    links = [str(a["href"]) for a in soup.find_all("a", href=True)]
    endpoints = sorted({l for l in links if l.startswith(target_url)})
    return endpoints
