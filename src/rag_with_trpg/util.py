import json
from dataclasses import fields
from pathlib import Path

from rag_with_trpg.config import Config

HEAD_SECTIONS: str = "###### "


def save_file(file_name: str, path: Path, content: str):
    print(f"저장 확인 - 파일명: {file_name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def header_counting(content: str) -> tuple[int, list[int]]:
    total = len(content)

    head_count: list[int] = [0 for _ in range(6)]
    for h in range(6):
        header = HEAD_SECTIONS[h:]
        head_count[5 - h] = content.count(header)
        content = content.replace(header, "")

    return total, head_count


def serialize(values: list) -> str:
    return "".join([f"h{i + 1}: ({v}) " if v > 0 else "" for i, v in enumerate(values)])


def find_file(path_list: list[Path], keyword: str) -> Path | None:
    for p in path_list:
        if p.stem == keyword:
            return p

    return None


def load_json[T](cls: type[T], config: Config, file_name: str) -> list[T]:
    config_setting = {f.name: f.type for f in fields(config)}
    if config_setting.get(file_name) is None:
        raise RuntimeError(
            f"wrong file call.. only {",".join(filter(lambda x: x.find("_file"), config_setting.keys()))} can be used"
        )

    file: Path = getattr(config, file_name)
    return [cls(**j) for j in json.loads(file.read_text(encoding="utf-8"))]
