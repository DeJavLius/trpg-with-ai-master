from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Chunk:
    doc_id: str  # PageEntry.slug or title INDEX_FILE 과 잇는 키 (D-35)
    strategy: str  # "fixed" | "recursive" | "semantic"
    index: int  # 문서 내 순번. 0부터
    start: int  # 원문 글자 오프셋 (닫힌 구간 시작)
    end: int  # 원문 글자 오프셋 (열린 구간 끝)
    text: str  # == source[start:end] 여야 한다   <- 이것도 계약이다
    chars_nonspace: int  # 공백 없는 text 길이


@dataclass(frozen=True, kw_only=True)
class ChunkSnapshot(Chunk):
    model_name: str
    chunks: list[Chunk]
    finish_date: str


@dataclass(frozen=True, kw_only=True)
class Piece:
    rung: int
    start: int
    end: int
