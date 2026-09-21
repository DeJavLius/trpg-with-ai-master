import re
from dataclasses import replace

import pytest
from bs4 import BeautifulSoup
from conftest import EXPECTED_MD, INDEX_TITLE

from trpg_with_ai_master.crawl import convert
from trpg_with_ai_master.crawl.convert import (
    converter,
    extract,
    is_index_page,
    title_decision,
)

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·픽스처 배선·assert 표현은 AI 가 적었다.
         각 테스트가 잠그는 결정 번호를 주석 한 줄로 남긴다.
"""

# markdownify 가 <a> 를 남겼을 때 나오는 형태: [텍스트](/view/...)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")

# <section> 밖에만 있는 Google Sites 크롬. 본문에 섞이면 선택자가 틀린 것이다.
NAVIGATION_MARKERS = ("Google Sites", "Report abuse", "Page details")


# ─── D-29 · 가장 중요 ────────────────────────────────────────────────
def test_no_markdown_links(raw_files):
    """strip=['a','img'] 가 살아 있는지 잠근다.

    지우면 에러 없이 갭이 5.6배 → 1.8배로 무너지고 제외가 0건이 된다
    (2026-09-04 실측: strip 제거 시 39개 중 임계값 미만 0개).
    """
    offenders = [
        raw.name
        for raw in raw_files
        if MARKDOWN_LINK.search(extract(raw.read_text(encoding="utf-8"))[1])
    ]

    assert offenders == []


# ─── <section> 선택자 (D-33) ─────────────────────────────────────────
def test_extract_drops_navigation(raw_files):
    """네비게이션·푸터가 본문에 섞이지 않는다."""
    offenders = [
        (raw.name, marker)
        for raw in raw_files
        for marker in NAVIGATION_MARKERS
        if marker in extract(raw.read_text(encoding="utf-8"))[1]
    ]

    assert offenders == []


# ─── D-04 건수 가드 ──────────────────────────────────────────────────
def test_excluded_count_is_one(tmp_config, raw_files):
    """raw 39 → md 38. 제외는 정확히 「직업」 1건."""
    converter(tmp_config, raw_files, [])

    assert len(list(tmp_config.md_path.glob("*.md"))) == EXPECTED_MD


def test_converter_returns_excluded_titles(tmp_config, raw_files):
    """제외 목록을 돌려준다 — 판정은 이 반환값으로 하고, 출력에 기대지 않는다 (D-04).

    ♻️ 09-05: 가드가 converter 안의 RuntimeError 에서 __main__ 의 인덱스 대조로
    옮겨갔다. converter 의 책임은 「무엇이 제외됐는지 알려주는 것」까지다.
    """
    excluded = converter(tmp_config, raw_files, [])

    assert excluded == [INDEX_TITLE]


def test_converter_reports_zero_when_threshold_disabled(
    tmp_config, raw_files, monkeypatch
):
    """제외가 0건이면 빈 리스트가 나온다 — 호출부가 판정할 수 있어야 한다 (D-21 4번).

    is_index_page 가 무력화되면(임계값 실수·strip 누락) 제외가 0건이 된다.
    그 상태가 조용히 「정상」으로 보이지 않는지 잠근다.
    """
    monkeypatch.setattr(convert, "is_index_page", lambda markdown: False)

    excluded = converter(tmp_config, raw_files, [])

    assert excluded == []
    assert len(list(tmp_config.md_path.glob("*.md"))) == EXPECTED_MD + 1


# ─── converter 분기 ──────────────────────────────────────────────────
def test_converter_writes_md(tmp_config, raw_files):
    converter(tmp_config, raw_files, [])

    assert list(tmp_config.md_path.glob("*.md"))


def test_converter_skips_when_md_exists(tmp_config, raw_files):
    converter(tmp_config, raw_files, [tmp_config.md_path / "already.md"])

    assert not tmp_config.md_path.exists()


@pytest.mark.parametrize("do_create", [True, False])
def test_do_create_controls_rebuild(make_config, raw_files, do_create):
    config = make_config(do_create=do_create)
    converter(config, raw_files, [config.md_path / "already.md"])

    assert config.md_path.is_dir() is do_create


def test_replace_overrides_single_flag(tmp_config, raw_files):
    config = replace(tmp_config, do_create=True)
    converter(config, raw_files, [config.md_path / "already.md"])

    assert list(config.md_path.glob("*.md"))


# ─── D-28 제목 소스 ──────────────────────────────────────────────────
def test_title_decision_without_separator(home_html):
    soup = BeautifulSoup(home_html, "html.parser")

    assert title_decision(soup) == soup.title.get_text(strip=True)


def test_title_decision_strips_site_name(body_html):
    soup = BeautifulSoup(body_html, "html.parser")
    title = title_decision(soup)

    assert " - " not in title
    assert soup.title.get_text(strip=True).endswith(title)


# ─── D-04 임계값 경계 ────────────────────────────────────────────────
def test_is_index_page_boundary(index_html, body_html):
    _, index_md = extract(index_html)
    _, body_md = extract(body_html)

    assert is_index_page(index_md)
    assert not is_index_page(body_md)
