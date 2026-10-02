import statistics
from pathlib import Path

import pytest

from trpg_with_ai_master.diagnose.diagnos import (
    DiagnoseMeta,
    SectionMeta,
    analyze_heading_section_middle,
    measure_meta_m,
    section_analyze,
    section_filter,
)
from trpg_with_ai_master.util import header_counting

"""
title: claude 작성 python script — diagnose M 측정 테스트
content: Phase 1 2주차 M(섹션 규모 중앙값) 측정 로직만 잠근다. 토크나이저·모델이 필요한
         meta_analyze / diagnose() 는 건드리지 않는다 (순수 함수만).

         잠그는 것:
         - 섹션 본문 = 헤딩 다음 줄 ~ 다음 헤딩(레벨 무관) 직전. 중복 집계 없음.
         - 키 0 = 첫 헤딩 앞 도입부. 내용이 있을 때만 들어간다.
         - 구간(도입부 + 헤딩) 2개 미만 페이지는 M 정의 밖 (§2-1).
         - util.header_counting 과 섹션 수가 어긋나지 않는다.
"""


def _sections(text: str) -> dict[int, list[SectionMeta]]:
    sections, _ = analyze_heading_section_middle(text)
    return sections


def _titles(sections: list[SectionMeta]) -> list[str]:
    return [s.section_title for s in sections]


# ─── analyze_heading_section_middle — 섹션 분할 ───────────────────────
def test_sections_have_keys_0_to_6():
    """0 은 도입부, 1~6 은 헤딩 레벨이다. 비어 있어도 키는 항상 있다."""
    sections = _sections("# 제목\n본문")

    assert sorted(sections) == [0, 1, 2, 3, 4, 5, 6]


def test_section_body_runs_until_next_heading_of_any_level():
    """부모 섹션은 자식 헤딩 앞에서 끊긴다 — 상위 레벨 본문에 하위 본문이 중복되지 않는다."""
    sections = _sections("# A\naaa\n## B\nbbbb\n# C\ncc")

    assert [(s.section_title, s.chars) for s in sections[1]] == [("A", 3), ("C", 2)]
    assert [(s.section_title, s.chars) for s in sections[2]] == [("B", 4)]


def test_section_chars_nonspace_excludes_all_whitespace():
    """\\s 는 개행·탭·전각 공백까지 지운다. chars 는 그대로 센다."""
    sections = _sections("# 제목\na b\n\tc　d")

    (section,) = sections[1]
    assert section.chars == len("a b\n\tc　d")
    assert section.chars_nonspace == 4


def test_section_title_is_stripped():
    sections = _sections("#  공백 제목  \n본문")

    assert _titles(sections[1]) == ["공백 제목"]


def test_empty_body_heading_is_kept_with_zero_chars():
    """본문이 빈 헤딩도 섹션으로 들어간다. 거르는 건 section_filter 몫이다."""
    sections = _sections("# A\n## B\n본문")

    assert [(s.section_title, s.chars) for s in sections[1]] == [("A", 0)]
    assert [s.section_title for s in sections[2]] == ["B"]


def test_non_heading_hash_lines_stay_in_body():
    """줄 중간 `C# `, 7개 `#`, `#` 뒤 공백 없음은 헤딩이 아니다."""
    sections = _sections("# 제목\nC# 언어\n####### 일곱\n#붙임")

    assert _titles(sections[1]) == ["제목"]
    assert sum(len(v) for v in sections.values()) == 1


@pytest.mark.xfail(strict=True, reason="코드 펜스 내부 `# ` 인식은 아직 미구현")
def test_hash_inside_code_fence_is_not_heading():
    """구현되면 strict xfail 이 깨져서 이 마커를 지우라고 알려준다."""
    sections = _sections("# 제목\n```\n# 주석\n```\n본문")

    assert _titles(sections[1]) == ["제목"]


# ─── 도입부 (키 0) ────────────────────────────────────────────────────
def test_preamble_is_collected_under_key_0():
    sections, preamble_nonspace = analyze_heading_section_middle(
        "도입 부분\n## 소제목\n본문"
    )

    assert [(s.section_title, s.chars) for s in sections[0]] == [
        ("", len("도입 부분"))
    ]
    assert preamble_nonspace == 4
    assert _titles(sections[2]) == ["소제목"]


def test_no_preamble_leaves_key_0_empty():
    sections, preamble_nonspace = analyze_heading_section_middle("# 제목\n본문")

    assert sections[0] == []
    assert preamble_nonspace == 0


def test_whitespace_only_preamble_is_ignored():
    """첫 줄이 빈 줄이어도 도입부로 세지 않는다 — 안 그러면 §2-1 판정이 깨진다."""
    sections, preamble_nonspace = analyze_heading_section_middle("\n\n# 제목\n본문")

    assert sections[0] == []
    assert preamble_nonspace == 0


def test_text_without_headings_is_all_preamble():
    sections, preamble_nonspace = analyze_heading_section_middle("헤딩 없는 본문")

    assert len(sections[0]) == 1
    assert preamble_nonspace == len("헤딩없는본문")
    assert all(sections[n] == [] for n in range(1, 7))


# ─── section_filter — §2-1 적용 범위 ──────────────────────────────────
def test_filter_drops_single_heading_page_without_preamble():
    """제목 하나뿐인 페이지는 섹션 = 페이지 전체라 경계가 없다 (드루이드 등 25건)."""
    assert section_filter(_sections("# 드루이드\n" + "본문 " * 100)) == []


def test_filter_drops_single_non_h1_heading_without_preamble():
    """레벨이 아니라 위치 기준이다 — 맨 위의 h2 하나도 페이지 전체다."""
    assert section_filter(_sections("## 소제목\n본문")) == []


def test_filter_keeps_single_heading_page_with_preamble():
    """중간에 헤딩이 하나 있으면 `도입부 | 섹션` 경계가 있다."""
    result = section_filter(_sections("도입 부분\n## 소제목\n본문"))

    assert _titles(result) == ["", "소제목"]


def test_filter_drops_empty_and_no_heading_input():
    assert section_filter(_sections("")) == []
    assert section_filter(_sections("   \n\n")) == []


def test_filter_keeps_multiple_headings_of_same_level():
    """h1 이 여러 개인 페이지(국면의 예 등)는 레벨이 하나여도 경계가 있다."""
    result = section_filter(_sections("# A\naaa\n# B\nbbb\n# C\nccc"))

    assert sorted(_titles(result)) == ["A", "B", "C"]


def test_filter_removes_empty_body_sections_from_result():
    result = section_filter(_sections("# A\n내용\n# B\n# C\n내용2"))

    assert sorted(_titles(result)) == ["A", "C"]


def test_filter_counts_empty_body_headings_as_boundaries():
    """현재 동작을 고정한다: 판정은 헤딩 수 기준이라 본문 빈 헤딩도 경계로 센다.

    그래서 내용이 있는 섹션이 1개뿐인 페이지(임시 웹페이지: h1×4 중 1개)가
    n=1 로 통과한다. 「내용 있는 섹션 2개 이상」으로 바꾸면 이 테스트가 깨진다.
    """
    result = section_filter(_sections("# A\n# B\n내용"))

    assert _titles(result) == ["B"]


# ─── measure_meta_m ───────────────────────────────────────────────────
def _meta_sections(*sizes: int) -> list[SectionMeta]:
    return [
        SectionMeta(section_title=f"s{i}", chars=n, chars_nonspace=n - 1)
        for i, n in enumerate(sizes)
    ]


def test_measure_meta_m_basic_stats():
    detail = measure_meta_m("페이지", _meta_sections(10, 30, 20), budget=100)

    assert detail.title == "페이지"
    assert detail.n == 3
    assert detail.m == 20
    assert detail.m_nonspace == 19
    assert (detail.min, detail.max) == (10, 30)
    assert detail.over_budget_ratio == 0.0


def test_measure_meta_m_median_of_even_count_is_float():
    detail = measure_meta_m("페이지", _meta_sections(10, 20), budget=100)

    assert detail.m == 15.0


def test_measure_meta_m_budget_is_exclusive():
    """`c > budget` — 예산과 같은 길이는 초과가 아니다. 단위는 글자 수다 (토큰 아님)."""
    detail = measure_meta_m("페이지", _meta_sections(10, 20, 30), budget=20)

    assert detail.over_budget_ratio == pytest.approx(1 / 3)


def test_measure_meta_m_rejects_empty_sections():
    """빈 입력은 호출부(section_analyze)가 막는다. 여기서는 터지는 것을 고정한다."""
    with pytest.raises(statistics.StatisticsError):
        measure_meta_m("페이지", [], budget=100)


# ─── section_analyze — 페이지 집계 ────────────────────────────────────
def _page(title: str, text: str | None) -> DiagnoseMeta:
    meta = DiagnoseMeta(title=title, chars=len(text or ""), headings=[0] * 6)
    meta.sections = _sections(text) if text is not None else None
    return meta


def test_section_analyze_skips_excluded_and_sectionless_pages():
    pages = [
        _page("단일 헤딩", "# 단일\n" + "가" * 50),
        _page("섹션 없음", None),
        _page("정상", "# A\n" + "가" * 10 + "\n## B\n" + "나" * 30),
    ]

    detail, pooled = section_analyze(pages, max_chars=100)

    assert [d.title for d in detail] == ["정상"]
    assert [s.chars for s in pooled] == [10, 30]


def test_section_analyze_pools_sections_across_pages():
    """M 은 페이지별 중앙값의 중앙값이 아니라 섹션 전체를 풀링한 중앙값이다."""
    pages = [
        _page("P1", "# A\n" + "가" * 10 + "\n# B\n" + "가" * 20),
        _page("P2", "# C\n" + "가" * 30 + "\n# D\n" + "가" * 40 + "\n# E\n" + "가" * 50),
    ]

    detail, pooled = section_analyze(pages, max_chars=100)

    assert [d.n for d in detail] == [2, 3]
    assert len(pooled) == 5
    assert measure_meta_m("pooled", pooled, 100).m == 30


def test_section_analyze_uses_rounded_budget_in_chars():
    """safe_chars(223.15…) 는 반올림해서 글자 수 예산으로 쓴다."""
    pages = [_page("P", "# A\n" + "가" * 223 + "\n# B\n" + "가" * 224)]

    (detail,), _ = section_analyze(pages, max_chars=223.15)

    assert detail.over_budget_ratio == 0.5


def test_section_analyze_returns_empty_when_every_page_is_filtered():
    detail, pooled = section_analyze([_page("단일", "# 단일\n본문")], max_chars=100)

    assert detail == []
    assert pooled == []


# ─── 실제 코퍼스 — util.header_counting 과의 정합 ─────────────────────
def test_section_count_matches_header_counting_on_real_corpus(md_files: list[Path]):
    """index.json 의 headings 와 섹션 수가 어긋나면 헤딩 판정 로직이 갈라진 것이다."""
    assert md_files, "코퍼스 md 가 없다"

    for md in md_files:
        text = md.read_text(encoding="utf-8")
        sections = _sections(text)
        _, counts = header_counting(text)

        assert [len(sections[n]) for n in range(1, 7)] == counts, md.name


def test_pooled_m_on_real_corpus(md_files: list[Path]):
    """dungeonworld 기준값 — 단일 헤딩 25건 제외, 121개 섹션, M = 622."""
    pages = []
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        meta = DiagnoseMeta(title=md.stem, chars=len(text), headings=[0] * 6)
        meta.sections = _sections(text)
        pages.append(meta)

    detail, pooled = section_analyze(pages, max_chars=223.15)

    assert len(detail) == 13
    assert len(pooled) == 121
    assert measure_meta_m("pooled", pooled, 223).m == 622
