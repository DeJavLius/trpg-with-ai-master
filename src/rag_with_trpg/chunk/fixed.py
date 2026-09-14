from rag_with_trpg.chunk.type import Chunk

# ── 계약 C1~C7 ────────────────────────────────────────────────────
#
# 근거: [[구현 가이드 3주차 청킹]] §3-3. 그 표가 바뀌면 여기도 바꾼다.
#
# 기호 — 아래 식은 전부 이 이름들로 쓴다.
#        starts / ends 의 값은 「원문 글자 오프셋(int)」이지 글자 자체가 아니다.
#        text[start:end] 의 그 start / end 다.
#
#   text    : 입력 원문 문자열
#   size    : 창 크기 (글자 수)
#   overlap : 이웃한 두 창이 겹치는 글자 수
#   chunks  : 반환값 list[Chunk]
#   starts  = [c.start for c in chunks]   # 각 청크의 시작 오프셋 (닫힌 구간)
#   ends    = [c.end   for c in chunks]   # 각 청크의 끝   오프셋 (열린 구간)
#   n       = len(chunks)
#
#   따라서 starts[0] == 0 은 "첫 글자가 0" 이 아니라
#          "첫 청크가 원문 0번 위치에서 시작한다" 는 뜻이다.
#
# 전제: text == "" 이면 chunks == [] 이고, C1' 이하는 적용하지 않는다.
#
# ── C1  커버리지 (총량) ──────────────────────────  개정: 등식 -> 항등식
#     laps = sum(ends[i] - starts[i + 1] for i in range(n - 1))   # 총겹침
#     sum(len(c.text) for c in chunks) == len(text) + laps
#
#     # 청크 길이의 총합 = 원문 길이 + 겹친 만큼. overlap 값과 무관하게 성립한다.
#     # A안이 마지막 창을 되감아 만드는 꼬리 겹침도 우변에 그대로 들어가기 때문이다.
#
#     # 특수해 1 — overlap == 0 이고 len(text) > size 이고 len(text) % size != 0 이면
#     #            꼬리 겹침이 정확히 size - (len(text) % size) 하나뿐이다.
#     #            예) len=10, size=4 -> 꼬리 2자, 겹침 4-2=2, 합 12 == 10+2
#     # 특수해 2 — laps == 0 이면  "".join(c.text for c in chunks) == text
#     #            laps == 0  <->  overlap == 0 이고
#     #                            (len(text) % size == 0 또는 len(text) <= size)
#
#     # 옛 C1("overlap=0 이면 이어붙이면 원문") 은 A안과 양립하지 않는다.
#     # 되감기가 overlap=0 에서도 꼬리에 겹침을 만든다 (§3-2 A안의 명시된 대가).
#     # 항등식 자체는 C1'(양끝 도달)에서 텔레스코핑으로 나오고,
#     # C5(포함 금지)가 있어야 우변의 laps 가 실제 중복 글자 수와 일치한다.
#
# ── C1' 커버리지 (일반) ──────────────────────────  신설
#     starts[0] == 0                                       # 원문 맨 앞에서 시작
#     ends[-1] == len(text)                                # 원문 맨 끝에서 끝
#     all(starts[i + 1] <= ends[i] for i in range(n - 1))  # 사이에 구멍이 없다
#     # overlap > 0 에서도 커버리지를 검증할 수 있게 오프셋으로 쓴 것이다.
#
# ── C2  최대 길이 ───────────────────────────────  기존 유지
#     all(len(c.text) <= size for c in chunks)
#     # 결함 1 의 A안(마지막 창 되감기)이 이걸 지킨다.
#
# ── C3  겹침 ───────────────────────────────────  결함 2 정정: 등식 -> 부등식
#     all(ends[i] - starts[i + 1] >= overlap for i in range(n - 1))
#     # 마지막 창을 max(0, len(text) - size) 로 되감아 꼬리를 흡수하므로
#     # 마지막 한 쌍의 겹침은 overlap 보다 커진다. 그래서 등식이 아니다.
#
# ── C4  최소 길이 ───────────────────────────────  신설
#     all(len(c.text) >= min_chunk for c in chunks)
#     # 예외: len(text) < min_chunk 이면 n == 1 (원문 전체가 청크 하나)
#     # 꼬리 청크를 계약으로 막는다.
#
# ── C5  포함 금지 ───────────────────────────────  신설
#     어떤 i != j 에 대해서도 다음이 성립하지 않는다:
#         starts[i] <= starts[j] and ends[j] <= ends[i]
#     # 청크 j 가 청크 i 안에 통째로 들어가면 같은 내용이 벡터 2개가 되어
#     # top-k 자리를 둘 먹는다. 중복 벡터를 계약으로 막는다.
#
# ── C6  입력 가드 ───────────────────────────────  3갈래로 분리
#     size <= 0       -> ValueError
#     overlap < 0     -> ValueError
#     overlap >= size -> ValueError
#
# ── C7  결정성 ─────────────────────────────────  신설
#     같은 인자로 두 번 부르면 같은 결과가 나온다.
#     # semantic 은 여기서 의도적으로 실패한다 — 그게 관찰 대상이다.
#
# ── Chunk 불변식 (§4. C1~C7 과 별개다) ────────────────────────────
#     all(c.text == text[c.start:c.end] for c in chunks)
#     # type.py 가 선언한 계약. C1'·C3·C5 가 오프셋으로 쓰여 있으므로
#     # 이게 깨지면 그 세 개는 검증 자체가 무의미해진다.


def fixed_chunking(
    text: str,
    size: int,
    overlap: int = 0,
    min_chunk: int = 0,
    *,
    doc_id: str | None = None,  # PageEntry.slug — provenance (D-35 · D-07)
) -> list[Chunk]:
    if size <= 0 or overlap < 0 or overlap >= size or min_chunk > size or min_chunk < 0:
        raise ValueError(
            "size, overlap, min_chunk value error. size is 0 or less, overlap is (smaller than 0) or (size or more), min_chunk is (0 or less) and (bigger than size)"
        )

    index, start, stride, end = 0, 0, size - overlap, size
    last_chunk = False
    chunk_result: list[Chunk] = []
    while start < len(text) and not last_chunk:
        end = min(end, len(text))
        if start + size >= len(text):
            start = max(0, end - size)
            last_chunk = True

        chunk = text[start:end]
        chunk_result.append(
            Chunk(
                doc_id="" if doc_id is None else doc_id,
                strategy="fixed",
                text=chunk,
                index=index,
                start=start,
                end=end,
                chars_nonspace=len("".join(chunk.split())),
            )
        )

        index += 1
        start += stride
        end = start + size

    return chunk_result
