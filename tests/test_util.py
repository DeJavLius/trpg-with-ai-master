from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from trpg_with_ai_master.crawl.util import clear_dir, md_head_counter, title_decision
from trpg_with_ai_master.util import find_file, header_counting, save_file, serialize

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·assert 표현은 AI 가 적었다.
         util.py 소관 — 도메인을 모르는 순수 헬퍼들.
"""


# ─── D-28 제목 소스 ──────────────────────────────────────────────────
def test_title_decision_strips_site_prefix():
    """<title> 의 " - " 앞을 떼어낸다. h1 이 아니라 <title> 이 소스다."""
    soup = BeautifulSoup("<title>던전월드 임시 - 마법사 주문</title>", "html.parser")

    assert title_decision(soup) == "마법사 주문"


def test_title_decision_keeps_whole_when_no_separator():
    """구분자가 없는 유일한 페이지(홈)를 잠근다. 잘라내면 제목이 빈다."""
    soup = BeautifulSoup("<title>던전월드 한국어 공개판</title>", "html.parser")

    assert title_decision(soup) == "던전월드 한국어 공개판"


def test_title_decision_falls_back_without_title_tag():
    """<title> 이 없으면 "_" 로 떨어진다. 예외를 던지지 않는다."""
    soup = BeautifulSoup("<html><body>본문</body></html>", "html.parser")

    assert title_decision(soup) == "_"


def test_title_decision_splits_on_first_separator_only():
    """제목 자체에 " - " 가 들어 있어도 사이트 접두사만 떼어낸다."""
    soup = BeautifulSoup("<title>사이트 - 국면 - 백색 관문</title>", "html.parser")

    assert title_decision(soup) == "국면 - 백색 관문"


# ─── 헤딩 계수 — 3주차 청킹 재료 (D-34 가드) ──────────────────────────
def test_header_counting_indexes_h1_to_h6():
    """head_count[0] 이 h1 이다. 인덱스가 뒤집히면 3주차 판단이 통째로 뒤집힌다."""
    markdown = "# a\n## b\n### c\n#### d\n##### e\n###### f\n본문"

    _, counts = header_counting(markdown)

    assert counts == [1, 1, 1, 1, 1, 1]


def test_header_counting_does_not_double_count_deeper_levels():
    """긴 헤딩부터 지우므로 `###### ` 가 `# ` 로 6번 세지지 않는다."""
    _, counts = header_counting("###### 깊은 것 하나뿐\n")

    assert counts == [0, 0, 0, 0, 0, 1]


def test_header_counting_total_is_original_length():
    """total 은 헤딩을 지우기 전 길이다 — D-04 임계값이 이 값을 쓴다."""
    markdown = "# 제목\n본문"

    total, _ = header_counting(markdown)

    assert total == len(markdown)


def test_header_counting_on_body_without_headings():
    """헤딩이 없어도 0 이 나온다. 39개 중 26개가 제목 하나뿐인 코퍼스다."""
    total, counts = header_counting("헤딩 없는 본문")

    assert counts == [0, 0, 0, 0, 0, 0]
    assert total == len("헤딩 없는 본문")


def test_md_head_counter_titles_from_stem(tmp_path: Path):
    """제목은 파일명(stem)에서 온다 — md 파일명이 곧 제목이라는 전제."""
    md = tmp_path / "마법사 주문.md"
    md.write_text("# 마법사 주문\n본문", encoding="utf-8")

    title, total, counts = md_head_counter(md)

    assert title == "마법사 주문"
    assert counts[0] == 1
    assert total == len(md.read_text(encoding="utf-8"))


# ─── serialize — 사람이 읽는 출력 ────────────────────────────────────
def test_serialize_hides_zero_levels():
    """0 인 레벨은 안 찍는다. 39줄 출력에서 노이즈를 줄이려는 의도."""
    assert serialize([24, 0, 3, 0, 0, 0]) == "h1: (24) h3: (3) "


def test_serialize_empty_when_all_zero():
    assert serialize([0, 0, 0, 0, 0, 0]) == ""


# ─── find_file ──────────────────────────────────────────────────────
def test_find_file_matches_by_stem(tmp_path: Path):
    """확장자를 뺀 이름으로 찾는다 — mapper 가 제목으로 md 를 되찾는 경로."""
    paths = [tmp_path / "액션.md", tmp_path / "직업.md"]

    assert find_file(paths, "직업") == tmp_path / "직업.md"


def test_find_file_returns_none_when_absent(tmp_path: Path):
    """제외된 페이지는 md 가 없다. None 이 정상 경로이므로 예외가 아니다."""
    assert find_file([tmp_path / "액션.md"], "직업") is None


def test_find_file_on_empty_list():
    assert find_file([], "직업") is None


# ─── 파일 조작 ───────────────────────────────────────────────────────
def test_save_file_creates_parent_dirs(tmp_path: Path):
    """raw/ 는 하위 디렉터리 3개를 갖는다. 부모가 없어도 저장돼야 한다."""
    target = tmp_path / "직업" / "마법사" / "마법사주문.html"

    save_file("마법사 주문", target, "본문")

    assert target.read_text(encoding="utf-8") == "본문"


def test_save_file_writes_utf8(tmp_path: Path):
    """한글 코퍼스라 인코딩이 로케일에 좌우되면 안 된다 (D-21 2번)."""
    target = tmp_path / "한글.md"

    save_file("한글", target, "닢 겡 뭅")

    assert target.read_bytes().decode("utf-8") == "닢 겡 뭅"


def test_clear_dir_removes_files_and_subdirs(tmp_path: Path):
    """재수집 전 비우기. 하위 디렉터리가 남으면 이전 수집물이 섞인다."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "old.html").write_text("x", encoding="utf-8")
    (tmp_path / "top.html").write_text("x", encoding="utf-8")

    clear_dir(tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_clear_dir_keeps_the_directory_itself(tmp_path: Path):
    """디렉터리는 남긴다 — 지우면 뒤이은 mkdir 전제가 깨진다."""
    clear_dir(tmp_path)

    assert tmp_path.is_dir()


def test_clear_dir_is_noop_when_missing(tmp_path: Path):
    """최초 실행에는 raw/ 가 없다. 예외 없이 통과해야 한다."""
    clear_dir(tmp_path / "없는디렉터리")


def test_clear_dir_is_noop_on_file(tmp_path: Path):
    """파일을 넘겨도 지우지 않는다 — is_dir 가드가 살아 있는지."""
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")

    clear_dir(f)

    assert f.exists()


@pytest.mark.parametrize("level, expected_index", [(1, 0), (3, 2), (6, 5)])
def test_header_counting_level_mapping(level: int, expected_index: int):
    """레벨 n 이 인덱스 n-1 에 들어간다 — PageEntry.headings 의 계약."""
    _, counts = header_counting(f"{'#' * level} 제목\n")

    assert counts[expected_index] == 1
    assert sum(counts) == 1
