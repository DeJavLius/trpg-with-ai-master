import pytest

from trpg_with_ai_master.crawl.__main__ import file_check

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·assert 표현은 AI 가 적었다.
         __main__.py 소관 — 파이프라인 가드 (D-34 「가드」).
"""


# ─── file_check — D-04 「반드시 검증」의 목록 대조 ─────────────────────
#
# 이 함수는 「converter 가 제외한 목록」과 「인덱스에 기록된 제외 목록」이
# 같은지 본다. 두 경로가 갈리면 md 저장과 인덱스 기록 중 하나가 틀린 것이다.


def test_file_check_false_on_identical_lists():
    """같으면 False — 가드가 발동하지 않는다."""
    assert file_check(["직업"], ["직업"]) is False


def test_file_check_false_on_multiple_identical():
    """원소가 2개 이상이어도 같으면 False.

    ♻️ 09-05: 이전 이중 루프 구현은 여기서 True 를 냈다. 제외가 1건뿐이라
    드러나지 않았고, 코퍼스가 늘어 제외가 2건이 되는 순간 가드가 상시 발동했을 것이다.
    """
    assert file_check(["직업", "괴물"], ["직업", "괴물"]) is False


def test_file_check_ignores_order():
    """순서는 다르되 내용이 같으면 통과한다.

    converter 는 raw 순회 순서로, 인덱스는 엔트리 순서로 목록을 만든다.
    두 순서가 같다는 보장이 없으므로 순서 차이로 멈추면 안 된다.
    """
    assert file_check(["직업", "괴물"], ["괴물", "직업"]) is False


def test_file_check_true_on_different_content():
    assert file_check(["직업"], ["괴물"]) is True


def test_file_check_true_when_one_side_empty():
    """한쪽이 비면 다르다.

    ♻️ 09-05: 이전 구현은 빈 리스트에서 루프를 한 번도 안 돌아 False 를 냈다.
    「제외가 0건인데 인덱스에는 있다」는 가장 잡아야 할 상태가 조용히 통과했다.
    """
    assert file_check([], ["직업"]) is True
    assert file_check(["직업"], []) is True


def test_file_check_false_on_both_empty():
    """둘 다 비면 같다 — 이 판정만으로는 0건을 못 잡는다.

    0건 자체의 판정은 len(execute_exclude) != prev_exclude_count 쪽이 맡는다.
    file_check 는 「목록이 같은가」만 본다.
    """
    assert file_check([], []) is False


@pytest.mark.parametrize(
    "left, right, expected",
    [
        (["a"], ["a", "b"], True),
        (["a", "b"], ["a"], True),
        (["a", "a"], ["a"], True),
    ],
)
def test_file_check_detects_length_mismatch(
    left: list[str], right: list[str], expected: bool
):
    """길이가 다르면 다르다 — 중복 원소가 한쪽에만 있는 경우 포함."""
    assert file_check(left, right) is expected
