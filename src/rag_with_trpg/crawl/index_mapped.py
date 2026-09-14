import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
from bs4.element import AttributeValueList

from rag_with_trpg.crawl.config import CrawlConfig
from rag_with_trpg.crawl.util import md_head_counter, title_decision
from rag_with_trpg.util import find_file, save_file, serialize

"""
title: claude 작성 python script — 시그니처 전용
content: D-20 조건부. 시그니처·docstring·함정만 AI 가 적었고 본문은 직접 쓴다.
         목적은 provenance(원문 URL) 보존 — D-07 응답 각주와 3주차 청킹 메타데이터의 재료.
"""


@dataclass(frozen=True, kw_only=True)
class PageEntry:
    slug: str  # PK. "직업/마법사/마법사-주문" — 하이픈이 살아 있는 원본
    parent: str | None  # 부모의 slug. 루트면 None
    title: str | None  # "마법사 주문" — <title> 에서 (D-28)
    def_title: str  # 변환 제목
    url: str  # 퍼센트 인코딩된 og:url 원본. D-07 각주에 그대로 붙일 값
    raw: str  # "raw/직업/마법사/마법사주문.html"
    md: str | None  # "md/마법사 주문.md" — 제외되면 None
    excluded: str | None  # "index" | None
    chars: int
    headings: list[int] | None  # 인덱스 + 1 위치가 header 크기

    @classmethod
    def from_page(
        cls, config: CrawlConfig, raw_path: Path, md_path: Path | None, def_title: str
    ) -> "PageEntry":
        base_path = str(Path(config.base_path).absolute())
        html = raw_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")

        raw = str(raw_path).replace(base_path, "")[1:]
        url = unquote(source_url(soup))
        slug = slug_of(url, config.site_url + config.url_keyword)
        parent = parent_of(slug)
        title: str | None = None
        md: str | None = None
        exclude: str | None = "index"
        chars: int = 0
        headings: list[int] | None = None

        if md_path is not None:
            exclude = None
            md = str(md_path).replace(base_path, "")[1:]
            title, chars, headings = md_head_counter(md_path)

        return cls(
            slug=slug,
            parent=parent,
            title=title,
            def_title=def_title,
            url=url,
            raw=raw,
            md=md,
            excluded=exclude,
            chars=chars,
            headings=headings,
        )


def mapper(
    config: CrawlConfig, raw_path_list: list[Path], md_path_list: list[Path]
) -> None:
    page_entries: list[PageEntry] = []

    for raw_path in raw_path_list:
        raw_html = raw_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(raw_html, "html.parser")
        md_title = title_decision(soup)
        md_file = find_file(md_path_list, md_title)
        page_entry = PageEntry.from_page(
            config=config, raw_path=raw_path, md_path=md_file, def_title=md_title
        )
        page_entries.append(page_entry)

    save_index(config, page_entries)


def save_index(config: CrawlConfig, page_entries: list[PageEntry]) -> None:
    save_file(
        config.index_file.stem,
        config.index_file,
        json.dumps([asdict(e) for e in page_entries], ensure_ascii=False, indent=2),
    )


def source_url(soup: BeautifulSoup) -> str:
    url = soup.find("meta", attrs={"property": "og:url"})

    if url is None:
        raise RuntimeError("url not found")

    url_content = url.get("content")
    if url_content is None:
        raise RuntimeError(f"content not founded: {url}")

    return (
        url_content[0] if isinstance(url_content, AttributeValueList) else url_content
    )


def slug_of(url: str, url_keyword: str) -> str:
    return url.replace(url_keyword, "")


def parent_of(slug: str) -> str | None:
    nodes = slug.split("/")
    return None if len(nodes) == 1 else nodes[-2]


def load_index(config: CrawlConfig) -> list[PageEntry]:
    index_json = json.loads(config.index_file.read_text(encoding="utf-8"))
    return [PageEntry(**d) for d in index_json]


def exclude_file_check(config: CrawlConfig) -> tuple[int, list[str]]:
    index_infos: list[PageEntry] = load_index(config)

    count = 0
    exclude_files: list[str] = []
    for m in index_infos:
        if m.excluded is not None:
            count += 1
            exclude_files.append(m.def_title)

    return count, exclude_files


def show_markdown_heading(config: CrawlConfig):
    page_entries = load_index(config)

    count = 0
    for page_entry in page_entries:
        if page_entry.excluded is None:
            count += 1
            print(
                f"{page_entry.title} - chars: {page_entry.chars}, heading: {serialize([] if page_entry.headings is None else page_entry.headings)}"
            )
