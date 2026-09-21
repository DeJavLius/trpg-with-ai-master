from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.crawl.util import clear_dir, title_decision
from trpg_with_ai_master.util import save_file


def converter(
    config: CrawlConfig, raw_files: list[Path], md_files: list[Path]
) -> list[str]:
    exclude_list: list[str] = []

    if not len(md_files) > 0 or config.do_create:
        clear_dir(config.md_path)
        exclude_list = _extracting(config, raw_files)

    return exclude_list


def _extracting(config: CrawlConfig, raw_files: list[Path]) -> list[str]:
    config.md_path.mkdir(parents=True, exist_ok=True)

    exclude_titles: list[str] = []
    for raw in raw_files:
        html = raw.read_text(encoding="utf-8")
        title, content = extract(html)

        if not is_index_page(content):
            save_file(title, config.md_path / f"{title}.md", content)
        else:
            exclude_titles.append(title)

    print(
        f"미 저장 파일 {len(exclude_titles)}건: "
        f"{"".join([f"{t}.md " for t in exclude_titles])}"
    )

    return exclude_titles


def extract(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title: str = title_decision(soup)
    contents = soup.find_all("section")

    indexed_content: list[str] = []
    for content in contents:
        indexed_content.append(str(content))

    result: str = "".join(
        md(str(section), heading_style="ATX", strip=["a", "img"]).replace("\xa0", " ")
        + "\n"
        for section in indexed_content
    )

    return title, result


def is_index_page(markdown: str) -> bool:
    return len(markdown) < 500
