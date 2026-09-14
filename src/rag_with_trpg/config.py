import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

# 파일명이 겹치면 뒤엣것이 앞엣것을 덮어쓴다. 키가 늘어도 검사가 따라오도록
# 이름을 한 곳에 모아 두고 순회한다 — 개별 상수로 두면 추가할 때마다 검사를 빠뜨린다.
FILE_NAME_ENVS: tuple[str, ...] = (
    "INDEX_FILE",
    "META_FILE",
    "META_RESULT_FILE",
    "MODEL_COMPARE_FILE",
    "CHUNK_RESULT_FILE",
)

"""
title: claude 작성 python script
content: 작업 규칙에 따라 crawl 본문 작성은 요청하지 않고 env 호출 및 기타 AI 미정의 개발 구현에서는 정리 및 구현을 요구함
"""


@dataclass(frozen=True, kw_only=True)
class Config:
    base_path: str
    raw_path: Path
    md_path: Path
    index_file: Path
    meta_file: Path
    meta_result_file: Path
    model_compare_file: Path
    chunk_result_file: Path

    @classmethod
    def from_config(cls) -> Self:
        """
        `**` 두 개를 한 호출에 펼치므로, 서브클래스가 공통 필드와 같은 키를 내면
        TypeError(multiple values) 로 즉시 죽는다 — 조용히 덮어쓰지 않는다.
        """
        return cls(**cls._base_kwargs(), **cls._extra_kwargs())

    @classmethod
    def _base_kwargs(cls) -> dict[str, Any]:
        """공통 필드의 환경변수 해석. 이 조립을 아는 유일한 곳이다."""
        return {
            "base_path": require_env("CORPORA_DUNGEONWORLD_PATH"),
            "raw_path": pre_require_path("raw"),
            "md_path": pre_require_path("md"),
            "index_file": require_json_env("INDEX_FILE"),
            "meta_file": require_json_env("META_FILE"),
            "meta_result_file": require_json_env("META_RESULT_FILE"),
            "model_compare_file": require_json_env("MODEL_COMPARE_FILE"),
            "chunk_result_file": require_json_env("CHUNK_RESULT_FILE"),
        }

    @classmethod
    def _extra_kwargs(cls) -> dict[str, Any]:
        """서브클래스가 추가한 필드만 돌려주는 훅. 베이스는 추가분이 없다."""
        return {}

    @classmethod
    def is_not_set(cls, instance, name) -> bool:
        if not isinstance(instance, cls):
            raise ValueError("wrong instance usage")

        return getattr(instance, name) is None


def load_config() -> None:
    """공용 설정을 먼저 읽고, 로컬 비밀값이 덮어쓰게 한다."""
    load_dotenv(ROOT / ".env.execute")
    load_dotenv(ROOT / ".env.shared", override=True)
    load_dotenv(ROOT / ".env", override=True)

    names = [require_env(name) for name in FILE_NAME_ENVS]
    if len(set(names)) < len(names):
        raise RuntimeError(
            f"환경변수 {', '.join(FILE_NAME_ENVS)} 중 같은 값이 있습니다. 각각의 파일명을 지정해 주세요."
        )


def get_env(name: str) -> str | None:
    """미설정, 빈 문자열, 공백만 입력을 모두 걸러낸 환경변수 값을 돌려준다."""
    value = os.getenv(name, "").strip()
    return None if not value else value


def get_int_env(name: str) -> int | None:
    """미설정, 빈 문자열, 공백만 입력을 모두 걸러낸 환경변수 값을 돌려준다."""
    value = os.getenv(name, "").strip()
    return None if not value else int(value)


def require_json_env(name: str) -> Path:
    """파일명 환경변수를 코퍼스 루트 밑의 `<이름>.json` 경로로 확정한다.

    joinpath(".json") 은 확장자가 아니라 `<이름>/.json` 이라는 경로 한 칸을 더 만든다.
    파일명 결합은 문자열로 하고, 루트 밖 검사는 require_path 에 맡긴다.
    """
    return pre_require_path(f"{require_env(name)}.json")


def require_bool_env(name: str) -> bool:
    return require_env(name) == "1"


def require_env(name: str) -> str:
    """미설정, 빈 문자열, 공백만 입력을 모두 걸러낸 환경변수 값을 돌려준다."""
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"환경변수 {name} 가 비어 있습니다. .env.shared / .env / .env.execute 를 확인하세요."
        )

    return value


def pre_require_path(*parts: str) -> Path:
    return require_path("CORPORA_DUNGEONWORLD_PATH", *parts)


def require_path(name: str, *parts: str) -> Path:
    """환경변수의 경로를 프로젝트 루트 기준으로 확정한다. 루트 밖은 거부한다."""
    base = Path(require_env(name)).expanduser()
    path = (base if base.is_absolute() else ROOT / base).joinpath(*parts).resolve()

    if not path.is_relative_to(ROOT):
        raise RuntimeError(f"환경변수 {name} 가 프로젝트 밖을 가리킵니다: {path}")

    return path
