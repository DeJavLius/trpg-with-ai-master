from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from conftest import EXPECTED_PAGES, URL_KEYWORD

from trpg_with_ai_master.crawl import crawl as crawl_mod
from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.crawl.crawl import crawler, enroll_all_links, fetch_handler

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·assert 표현은 AI 가 적었다.
         수집(crawl.py) 소관. 변환(convert.py) 테스트는 test_convert.py 에 있다.
         네트워크를 타지 않는다 — httpx 호출은 전부 monkeypatch 로 막는다.
"""


# ─── 사이트맵 (1주차 완료 조건) ───────────────────────────────────────
def test_enroll_all_links_collects_every_page(home_html):
    """홈 한 장에서 39개가 나온다 — 재귀 크롤링이 필요 없다는 전제를 잠근다.

    1주차 완료 조건 「raw/ 에 HTML 39개」의 회귀 가드다.
    """
    links = enroll_all_links(home_html, URL_KEYWORD)

    assert len(links) == EXPECTED_PAGES


def test_enroll_all_links_is_deduped_and_sorted(home_html):
    links = enroll_all_links(home_html, URL_KEYWORD)

    assert links == sorted(set(links))


def test_enroll_all_links_drops_external(home_html):
    """사이트 밖 링크가 섞이면 크롤이 남의 서버를 때린다."""
    links = enroll_all_links(home_html, URL_KEYWORD)

    assert all(link.startswith(URL_KEYWORD) for link in links)


def test_enroll_all_links_keeps_hyphens(home_html):
    """슬러그의 하이픈이 링크 단계에서는 살아 있다.

    raw 파일명은 `replace('-', '')` 로 하이픈을 지우므로 (비가역),
    원본 슬러그를 얻을 수 있는 곳은 여기와 og:url 뿐이다 — meta_mapped.slug_of 참조.
    """
    links = enroll_all_links(home_html, URL_KEYWORD)

    assert any("-" in link.removeprefix(URL_KEYWORD) for link in links)


def test_enroll_all_links_on_page_without_links():
    """링크가 없으면 빈 리스트다. 예외로 죽지 않는다."""
    assert enroll_all_links("<html><body>본문</body></html>", URL_KEYWORD) == []


# ─── fetch — 상태 코드와 User-Agent (09-04 이행) ──────────────────────
class _FakeResponse:
    def __init__(self, text: str = "ok", status: int = 200):
        self.text = text
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise httpx.HTTPStatusError(
                f"status {self._status}", request=None, response=None
            )


def test_fetch_sends_user_agent(monkeypatch, tmp_config: CrawlConfig):
    """식별 가능한 User-Agent 를 보낸다 — 익명 크롤러로 차단당하지 않기 위해."""
    seen: dict = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        seen["url"] = url
        return _FakeResponse()

    monkeypatch.setattr(crawl_mod.httpx, "get", fake_get)
    fetch_handler(tmp_config, "/view/dwtemporary/액션")

    assert seen["headers"]["User-Agent"] == tmp_config.user_agent


def test_fetch_percent_encodes_korean_slug(monkeypatch, tmp_config: CrawlConfig):
    """한글 슬러그를 인코딩하지 않으면 400 이 온다."""
    seen: dict = {}

    monkeypatch.setattr(
        crawl_mod.httpx,
        "get",
        lambda url, **kw: (seen.update(url=url), _FakeResponse())[1],
    )
    fetch_handler(tmp_config, "/view/dwtemporary/액션")

    assert "액션" not in seen["url"]
    assert "%" in seen["url"]


def test_fetch_raises_on_error_status(monkeypatch, make_config, tmp_path: Path):
    """4xx·5xx 에서 멈춘다. h1 == "404" 사후 검사는 5xx·타임아웃을 못 잡는다."""
    config = replace(make_config(), raw_path=tmp_path / "raw")
    config.raw_path.mkdir()
    monkeypatch.setattr(
        crawl_mod.httpx, "get", lambda url, **kw: _FakeResponse(status=500)
    )

    with pytest.raises(httpx.HTTPError):
        fetch_handler(config, "/view/dwtemporary/액션")


def test_fetch_failure_clears_raw_dir(monkeypatch, make_config, tmp_path: Path):
    """실패하면 raw/ 를 비운다 — 절반만 수집된 코퍼스를 남기지 않는다.

    raw_path 를 tmp 로 바꿔서 돌린다. 실제 corpora/raw 로 돌리면 39개가 지워진다.
    """
    config = replace(make_config(), raw_path=tmp_path / "raw")
    config.raw_path.mkdir()
    (config.raw_path / "half.html").write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        crawl_mod.httpx, "get", lambda url, **kw: _FakeResponse(status=503)
    )

    with pytest.raises(httpx.HTTPError):
        fetch_handler(config, "/view/dwtemporary/액션")

    assert list(config.raw_path.iterdir()) == []


# ─── crawler 분기 ────────────────────────────────────────────────────
def test_crawler_recrawls_when_no_files(monkeypatch, tmp_config: CrawlConfig):
    """수집물이 없으면 최초 수집을 돈다."""
    called: list[bool] = []
    monkeypatch.setattr(crawl_mod, "_target_crawl", lambda c: called.append(True))

    crawler(tmp_config, [])

    assert called == [True]


def test_crawler_recrawls_when_flag_set(
    monkeypatch, make_config, raw_files: list[Path]
):
    """DO_CRAWL=1 이면 파일이 있어도 다시 긁는다."""
    called: list[bool] = []
    monkeypatch.setattr(crawl_mod, "_target_crawl", lambda c: called.append(True))

    crawler(make_config(do_crawl=True), raw_files)

    assert called == [True]


def test_crawler_skips_when_files_are_healthy(
    monkeypatch, tmp_config: CrawlConfig, raw_files: list[Path]
):
    """정상 수집물이 있으면 사이트를 다시 때리지 않는다."""
    called: list[bool] = []
    monkeypatch.setattr(crawl_mod, "_target_crawl", lambda c: called.append(True))

    crawler(tmp_config, raw_files)

    assert called == []


def test_crawler_recrawls_on_404_page(monkeypatch, make_config, tmp_path: Path):
    """h1 이 "404" 인 파일이 섞이면 전역 재수집한다."""
    config = replace(make_config(), raw_path=tmp_path / "raw")
    config.raw_path.mkdir()
    bad = config.raw_path / "bad.html"
    bad.write_text("<h1>404</h1>", encoding="utf-8")
    called: list[bool] = []
    monkeypatch.setattr(crawl_mod, "_target_crawl", lambda c: called.append(True))

    crawler(config, [bad])

    assert called == [True]


def test_crawler_recrawls_on_empty_page(monkeypatch, make_config, tmp_path: Path):
    """h1 이 하나도 없으면 내용이 안 받아진 것으로 본다."""
    config = replace(make_config(), raw_path=tmp_path / "raw")
    config.raw_path.mkdir()
    empty = config.raw_path / "empty.html"
    empty.write_text("<html><body></body></html>", encoding="utf-8")
    called: list[bool] = []
    monkeypatch.setattr(crawl_mod, "_target_crawl", lambda c: called.append(True))

    crawler(config, [empty])

    assert called == [True]
