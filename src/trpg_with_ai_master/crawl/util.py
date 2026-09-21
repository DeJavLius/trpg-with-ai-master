import shutil
from pathlib import Path

from bs4 import BeautifulSoup

from trpg_with_ai_master.util import header_counting

# crawl 도메인 전용 헬퍼. 최상위 util.py 는 「도메인을 모르는 순수 헬퍼」로 두고,
# bs4 · 사이트 <title> 규약(D-28) · 마크다운 파일을 아는 것만 여기 남긴다.
SITE_TITLE_SEP = " - "


def clear_dir(path: Path) -> None:
    if not path.is_dir():
        return

    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def title_decision(soup: BeautifulSoup) -> str:
    if soup.title is None:
        return "_"

    title = soup.title.get_text(strip=True)
    _, sep, page = title.partition(SITE_TITLE_SEP)

    return page.strip() if sep else title


def md_head_counter(path: Path) -> tuple[str, int, list[int]]:
    title = path.stem
    markdown = path.read_text(encoding="utf-8")
    md_total, md_head_count = header_counting(markdown)
    return title, md_total, md_head_count
