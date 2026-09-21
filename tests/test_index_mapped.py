import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from conftest import EXPECTED_EXCLUDED, EXPECTED_MD, EXPECTED_PAGES, INDEX_TITLE

from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.crawl.convert import converter
from trpg_with_ai_master.crawl.index_mapped import (
    PageEntry,
    exclude_file_check,
    load_index,
    mapper,
    parent_of,
    slug_of,
    source_url,
)

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·픽스처 배선·assert 표현은 AI 가 적었다.
         index_mapped.py 소관 — D-35 페이지 인덱스. 각 테스트가 잠그는 결정 번호를 남긴다.
"""

KEYWORD = "https://sites.google.com/view/dwtemporary/"


# ─── slug / parent — 페이지 관계 (D-04 「포기」의 복원 경로) ─────────────
def test_slug_of_strips_site_and_keyword():
    assert slug_of(f"{KEYWORD}액션", KEYWORD) == "액션"


def test_slug_keeps_hyphens():
    """raw 파일명은 하이픈을 지우므로(비가역), 원본 슬러그는 og:url 에만 남는다."""
    assert (
        slug_of(f"{KEYWORD}직업/마법사/마법사-주문", KEYWORD)
        == "직업/마법사/마법사-주문"
    )


def test_parent_of_root_is_none():
    assert parent_of("액션") is None


@pytest.mark.parametrize(
    "slug, expected",
    [("직업/마법사", "직업"), ("직업/마법사/마법사-주문", "마법사")],
)
def test_parent_of_nested(slug: str, expected: str):
    """부모는 바로 위 한 단계다. 루트가 아니라 직속 부모."""
    assert parent_of(slug) == expected


# ─── source_url — provenance (D-07 응답 각주의 재료) ────────────────────
def test_source_url_reads_og_url():
    soup = BeautifulSoup(
        '<meta property="og:url" content="https://example.test/a">', "html.parser"
    )

    assert source_url(soup) == "https://example.test/a"


def test_source_url_raises_when_missing():
    """og:url 이 없으면 멈춘다. 조용히 빈 문자열을 넣으면 각주를 못 만든다."""
    soup = BeautifulSoup("<html></html>", "html.parser")

    with pytest.raises(RuntimeError):
        source_url(soup)


# ─── PageEntry — D-35 스키마 ────────────────────────────────────────
def test_from_page_marks_excluded_when_no_md(corpus_config: CrawlConfig):
    """md 가 없으면 excluded="index". 「제외됨」과 「저장 실패」를 구분하는 필드다."""
    raw = corpus_config.raw_path / "직업.html"

    entry = PageEntry.from_page(
        config=corpus_config, raw_path=raw, md_path=None, def_title=INDEX_TITLE
    )

    assert entry.excluded == "index"
    assert entry.md is None
    assert entry.chars == 0
    assert entry.headings is None


def test_from_page_fills_measures_when_md_exists(
    corpus_config: CrawlConfig, tmp_path: Path
):
    """md 가 있으면 excluded=None 이고 계측값이 채워진다."""
    md = tmp_path / "액션.md"
    md.write_text("# 액션\n## 접근전\n본문", encoding="utf-8")
    raw = corpus_config.raw_path / "액션.html"

    entry = PageEntry.from_page(
        config=corpus_config, raw_path=raw, md_path=md, def_title="액션"
    )

    assert entry.excluded is None
    assert entry.chars > 0
    assert entry.headings is not None
    assert entry.headings[0] == 1


def test_from_page_trims_base_path(corpus_config: CrawlConfig):
    """raw 경로는 코퍼스 루트 기준 상대 경로로 저장된다 — 절대 경로가 커밋되면 안 된다."""
    raw = corpus_config.raw_path / "액션.html"

    entry = PageEntry.from_page(
        config=corpus_config, raw_path=raw, md_path=None, def_title="액션"
    )

    assert entry.raw.endswith("raw/액션.html")
    assert str(corpus_config.raw_path) not in entry.raw


def test_page_entry_is_frozen(corpus_config: CrawlConfig):
    """인덱스 엔트리는 불변이다. 만든 뒤 고치면 파일과 메모리가 갈린다."""
    raw = corpus_config.raw_path / "액션.html"
    entry = PageEntry.from_page(
        config=corpus_config, raw_path=raw, md_path=None, def_title="액션"
    )

    with pytest.raises(FrozenInstanceError):
        entry.title = "다른 제목"  # type: ignore[misc]


# ─── mapper → save_index → load_meta 왕복 (D-35) ─────────────────────
def test_mapper_writes_index_at_configured_path(corpus_config: CrawlConfig):
    """저장 위치는 설정의 index_file 그 자체다.

    코드가 base_path + 이름 + ".json" 으로 다시 조립하면 조립 규칙이 두 곳에 생기고,
    한쪽만 바뀌면 조용히 다른 파일에 쓴다 (09-07 파일명 드리프트).
    """
    raw_files = sorted(corpus_config.raw_path.rglob("*.html"))
    converter(corpus_config, raw_files, [])
    md_files = sorted(corpus_config.md_path.rglob("*.md"))

    mapper(corpus_config, raw_files, md_files)

    assert corpus_config.index_file.is_file()
    assert corpus_config.index_file.suffix == ".json"


def test_index_round_trip_preserves_entries(corpus_config: CrawlConfig):
    """asdict → json → PageEntry(**d) 가 값을 잃지 않는다.

    kw_only 라 ** 로 그대로 복원된다. 필드가 늘 때 이 테스트가 먼저 깨진다.
    """
    raw_files = sorted(corpus_config.raw_path.rglob("*.html"))
    converter(corpus_config, raw_files, [])
    mapper(corpus_config, raw_files, sorted(corpus_config.md_path.rglob("*.md")))

    loaded = load_index(corpus_config)

    assert len(loaded) == len(raw_files)
    assert all(isinstance(e, PageEntry) for e in loaded)


def test_index_is_written_as_readable_utf8(corpus_config: CrawlConfig):
    """ensure_ascii=False + indent — 커밋되는 파일이라 diff 가 읽혀야 한다 (D-06)."""
    raw_files = sorted(corpus_config.raw_path.rglob("*.html"))
    converter(corpus_config, raw_files, [])
    mapper(corpus_config, raw_files, sorted(corpus_config.md_path.rglob("*.md")))

    text = corpus_config.index_file.read_text(encoding="utf-8")

    assert "\\u" not in text
    assert "\n" in text


def test_exclude_file_check_counts_index_pages(corpus_config: CrawlConfig):
    """축소 코퍼스 3종 중 제외는 「직업」 1건 — 임계값이 경계에서 도는지."""
    raw_files = sorted(corpus_config.raw_path.rglob("*.html"))
    converter(corpus_config, raw_files, [])
    mapper(corpus_config, raw_files, sorted(corpus_config.md_path.rglob("*.md")))

    count, titles = exclude_file_check(corpus_config)

    assert count == EXPECTED_EXCLUDED
    assert titles == [INDEX_TITLE]


# ─── D-35 정합성 6항목 — 실제 산출물 대상. 읽기 전용 ────────────────────
#
# [[decisions phase 1]] D-04 「반드시 검증」 / D-35.
# 09-05 에 jq 로 수기 확인한 6항목을 코드로 옮긴 것이다.


@pytest.fixture(scope="module")
def entries(index_path: Path) -> list[dict]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def test_index_entry_count_matches_raw(entries: list[dict], raw_files: list[Path]):
    """① 엔트리 수 = raw HTML 수. 어긋나면 크롤 누락이나 매핑 실패다."""
    assert len(entries) == len(raw_files) == EXPECTED_PAGES


def test_index_excluded_count(entries: list[dict]):
    """② 제외 건수 = EXPECTED_EXCLUDED. 0건이나 다건이면 임계값이 아니라 extract 가 깨진 것."""
    excluded = [e for e in entries if e["excluded"] is not None]

    assert len(excluded) == EXPECTED_EXCLUDED
    assert excluded[0]["def_title"] == INDEX_TITLE


def test_index_md_count_matches_files(entries: list[dict], md_files: list[Path]):
    """③ md 를 가진 엔트리 수 = 실제 md 파일 수."""
    assert len([e for e in entries if e["md"] is not None]) == len(md_files)
    assert len(md_files) == EXPECTED_MD


def test_index_slug_is_unique(entries: list[dict]):
    """④ slug 는 PK 다. 겹치면 다른 페이지가 한 칸에 덮인다."""
    slugs = [e["slug"] for e in entries]

    assert len(set(slugs)) == len(slugs)


def test_index_md_paths_exist(entries: list[dict], corpora_root: Path):
    """⑤ 인덱스가 가리키는 md 가 실제로 있다. 경로 계산 오류를 잡는다."""
    missing = [
        e["md"]
        for e in entries
        if e["md"] is not None and not (corpora_root / e["md"].lstrip("/")).is_file()
    ]

    assert missing == []


def test_index_excluded_entries_have_no_measures(entries: list[dict]):
    """⑥ 제외 건은 chars=0 · headings=null. 제외 판정과 본문이 어긋나면 안 된다."""
    offenders = [
        e["slug"]
        for e in entries
        if e["excluded"] is not None and (e["chars"] != 0 or e["headings"] is not None)
    ]

    assert offenders == []


def test_index_keeps_provenance(entries: list[dict]):
    """url 은 전건에 있어야 한다 — 잃으면 재크롤링 말고는 복원할 방법이 없다 (D-07)."""
    assert all(e["url"] for e in entries)
