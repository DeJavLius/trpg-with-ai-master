from dataclasses import dataclass

from rag_with_trpg.config import Config, get_int_env


@dataclass(frozen=True, kw_only=True)
class ChunkConfig(Config):
    chunk_size: int | None
    chunk_overlap: int | None
    chunk_min: int | None
    semantic_percentile: int | None
    semantic_buffer: int | None

    @classmethod
    def _extra_kwargs(cls) -> dict[str, int | None]:
        return {
            "chunk_size": get_int_env("CHUNK_SIZE"),
            "chunk_overlap": get_int_env("CHUNK_OVERLAP"),
            "chunk_min": get_int_env("CHUNK_MIN"),
            "semantic_percentile": get_int_env("SEMANTIC_PERCENTILE"),
            "semantic_buffer": get_int_env("SEMANTIC_BUFFER"),
        }
