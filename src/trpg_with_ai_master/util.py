import json
import re
from dataclasses import fields
from pathlib import Path

from trpg_with_ai_master.config import Config


def save_file(file_name: str, path: Path, content: str):
    print(f"저장 확인 - 파일명: {file_name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def header_re(s: int = 1, e: int = 6, flags: int | re.RegexFlag = 0):
    if s < 1 or e > 6:
        raise RuntimeError("wrong header length.. 1 ~ 6 can be possible")
    elif s > e:
        raise RuntimeError("start position is greater than end position")

    return re.compile(rf"^(#{{{s},{e}}}) (.*)$", flags)


def header_counting(content: str) -> tuple[int, list[int]]:
    head_count: list[int] = [0] * 6
    for m in header_re(flags=re.M).finditer(content):
        head_count[len(m.group(1)) - 1] += 1

    return len(content), head_count


def find_header(lines: list[str]) -> list[
    tuple[int, re.Match[str]]]:
    header = header_re()
    return [(i, m) for i, line in enumerate(lines) if
            (m := header.match(line))]


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
