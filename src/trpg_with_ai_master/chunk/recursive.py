from trpg_with_ai_master.chunk.type import Chunk

SEPARATORS = ["\n## ", "\n\n", "\n", None, ""]  # None = 문장 정규식, "" = 글자


def recursive_chunking(
    text: str,
    size: int,
    overlap: int = 0,
    min_chunk: int = 0,
    *,
    doc_id: str | None = None,
) -> list[Chunk]:
    raise NotImplementedError


def split_recursive(text, budget, seps: list[str | None] = SEPARATORS) -> list[str]:
    # 1. len(text) <= budget 이면 [text] 반환 (재귀 바닥)
    # 2. seps 가 비었으면 chunk_fixed 로 강제 절단해서 반환 (진짜 바닥)
    # 3. 현재 단 구분자로 text 를 조각낸다
    #      - 구분자를 버리지 않는다: 헤딩/줄바꿈이 사라지면 문맥이 준다
    #      - 나눠지지 않으면(조각 1개) 다음 단으로 넘어간다  <- 25개 페이지가 여기
    # 4. 각 조각에 대해: budget 이하면 그대로, 넘으면 seps[1:] 로 재귀
    # 5. 조각 리스트 반환 (아직 청크가 아니다 — 다음이 pack)
    raise NotImplementedError


def pack(pieces, budget, min_chunk) -> list[Chunk]:
    # 조각을 앞에서부터 이어 붙인다 (greedy)
    #   - 현재 덩어리 + 다음 조각 <= budget 이면 붙인다
    #   - 넘으면 현재 덩어리를 방출하고 다음 조각으로 새로 시작
    #   - 방출 직전 len < min_chunk 이면: 앞 청크에 흡수 or 예산 초과 허용
    #     ^^^ 어느 쪽을 골랐는지가 DECISIONS 4줄이다
    #   - 헤딩 경계를 넘어서는 붙이지 않는다 (실패 4 방지)
    # 오프셋(start,end)을 잃지 않도록 조각 단계부터 위치를 들고 다닌다
    raise NotImplementedError
