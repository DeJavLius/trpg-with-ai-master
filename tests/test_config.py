from dataclasses import FrozenInstanceError, fields

import pytest

import trpg_with_ai_master.config as config_module
from trpg_with_ai_master.chunk.config import ChunkConfig
from trpg_with_ai_master.config import (
    ROOT,
    Config,
    get_env,
    get_int_env,
    load_config,
    require_bool_env,
    require_env,
    require_json_env,
    require_path,
)
from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.diagnose.config import DiagnoseConfig

"""
title: claude 작성 python script — 테스트 본문
content: D-20 조건부 (2026-09-04 개정). 「무엇을 잠그나」와 기대값은 직접 정하고,
         pytest 문법·monkeypatch 배선은 AI 가 적었다.

         ♻️ 09-09 전면 개정 — 필드를 열거하지 않는다.
         종전 판은 설정 클래스마다 필드 값을 하나하나 assert 했다. 그러면 환경변수가
         하나 늘 때마다 테스트를 같이 고쳐야 하는데, 그 수정은 「구현을 그대로 옮겨 적는」
         작업이라 회귀를 못 잡는다 (실제로 chunk_result_file 추가 때 테스트만 깨졌다).

         대신 두 가지를 잠근다.
           ① 헬퍼의 규칙 — 빈 값·경로 이탈·"1" 만 참. 필드 목록과 무관하다
           ② 조립 구조 — 선언된 필드가 전부 채워지는가, 키가 필드와 맞는가.
              dataclasses.fields() 로 순회하므로 필드가 늘어도 테스트는 그대로다
"""

# from_config() 을 가진 설정 클래스 전부. 새 패키지가 생기면 여기 한 줄만 는다.
CONFIG_CLASSES = [Config, CrawlConfig, DiagnoseConfig, ChunkConfig]
CORPORA = ROOT / "corpora" / "dungeonworld"


def _ids(cls) -> str:
    return cls.__name__


# ─── require_env — 빈 값이 조용히 통과하지 않는다 ─────────────────────
def test_require_env_returns_value(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "value")

    assert require_env("SOME_KEY") == "value"


def test_require_env_raises_when_unset(monkeypatch):
    monkeypatch.delenv("결코_없는_변수", raising=False)

    with pytest.raises(RuntimeError):
        require_env("결코_없는_변수")


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_require_env_rejects_blank(monkeypatch, value: str):
    """빈 문자열·공백만 있는 값도 미설정으로 본다.

    dotenv 는 `KEY=` 를 빈 문자열로 읽는다. 통과시키면 URL 이 사이트 루트가 되어
    엉뚱한 곳을 크롤링한다 — 에러 없이.
    """
    monkeypatch.setenv("BLANK_KEY", value)

    with pytest.raises(RuntimeError):
        require_env("BLANK_KEY")


def test_require_env_strips_surrounding_space(monkeypatch):
    monkeypatch.setenv("PADDED", "  index  ")

    assert require_env("PADDED") == "index"


def test_require_env_names_the_variable(monkeypatch):
    """어느 환경변수인지 메시지에 있어야 한다. 없으면 원인을 못 찾는다."""
    monkeypatch.delenv("MISSING_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MISSING_KEY"):
        require_env("MISSING_KEY")


# ─── get_env / get_int_env — 미설정이 허용되는 쪽 ──────────────────────
#
# require_* 는 멈추고 get_* 는 None 을 낸다. 「없어도 되는 값」과 「없으면 안 되는 값」을
# 호출부가 고르는 구조이므로, 두 갈래가 실제로 다르게 도는지 잠근다.


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_get_env_returns_none_on_blank(monkeypatch, value: str):
    monkeypatch.setenv("OPTIONAL_KEY", value)

    assert get_env("OPTIONAL_KEY") is None


def test_get_env_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("OPTIONAL_KEY", raising=False)

    assert get_env("OPTIONAL_KEY") is None


def test_get_int_env_parses(monkeypatch):
    monkeypatch.setenv("SOME_INT", " 128 ")

    assert get_int_env("SOME_INT") == 128


def test_get_int_env_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_INT", raising=False)

    assert get_int_env("SOME_INT") is None


def test_get_int_env_raises_on_non_numeric(monkeypatch):
    """숫자가 아니면 None 으로 삼키지 않는다 — 오타가 「미설정」으로 위장하면 안 된다."""
    monkeypatch.setenv("SOME_INT", "백이십팔")

    with pytest.raises(ValueError):
        get_int_env("SOME_INT")


# ─── require_bool_env — "1" 만 참이다 ──────────────────────────────
@pytest.mark.parametrize(
    "value, expected",
    [("1", True), ("0", False), ("true", False), ("True", False), ("yes", False)],
)
def test_require_bool_env(monkeypatch, value: str, expected: bool):
    """「true」 를 참으로 읽으면 의도치 않은 재수집·재변환이 돈다."""
    monkeypatch.setenv("FLAG", value)

    assert require_bool_env("FLAG") is expected


def test_require_bool_env_rejects_blank(monkeypatch):
    """빈 값은 False 가 아니라 에러다. 미설정과 「끔」을 구분한다."""
    monkeypatch.setenv("FLAG", "")

    with pytest.raises(RuntimeError):
        require_bool_env("FLAG")


# ─── require_path — 프로젝트 밖을 가리키지 않는다 ──────────────────────
def test_require_path_resolves_under_root(monkeypatch):
    monkeypatch.setenv("CORPORA_DUNGEONWORLD_PATH", "corpora/dungeonworld/")

    assert require_path("CORPORA_DUNGEONWORLD_PATH", "raw") == CORPORA / "raw"


def test_require_path_rejects_escape(monkeypatch):
    """`../` 로 저장소 밖을 가리키면 거부한다.

    clear_dir 가 이 경로를 통째로 비우므로, 밖을 가리키면 남의 디렉터리를 지운다.
    """
    monkeypatch.setenv("ESCAPE_PATH", "../../..")

    with pytest.raises(RuntimeError):
        require_path("ESCAPE_PATH")


def test_require_path_rejects_absolute_outside_root(monkeypatch):
    monkeypatch.setenv("ABS_PATH", "/tmp")

    with pytest.raises(RuntimeError):
        require_path("ABS_PATH")


# ─── require_json_env — 파일명이 .json 경로 하나로 확정된다 ─────────────
def test_require_json_env_appends_suffix(monkeypatch):
    """`.json` 은 확장자다. 경로 한 칸(`index/.json`)이 되면 파일이 안 열린다.

    joinpath(".json") 은 디렉터리를 하나 더 만든다 — 파일이 없다는 에러가
    한참 뒤 read_text 에서 나므로 원인이 설정이라는 걸 알기 어렵다.
    """
    monkeypatch.setenv("CORPORA_DUNGEONWORLD_PATH", "corpora/dungeonworld/")
    monkeypatch.setenv("SOME_FILE", "index")

    path = require_json_env("SOME_FILE")

    assert path == CORPORA / "index.json"
    assert path.parent == CORPORA


def test_require_json_env_rejects_escape(monkeypatch):
    """파일명으로도 코퍼스 밖을 못 가리킨다 — require_path 의 검사를 그대로 탄다."""
    monkeypatch.setenv("CORPORA_DUNGEONWORLD_PATH", "corpora/dungeonworld/")
    monkeypatch.setenv("SOME_FILE", "../../../../etc/passwd")

    with pytest.raises(RuntimeError):
        require_json_env("SOME_FILE")


# ─── 조립 구조 — 필드가 늘어도 이 절은 안 바뀐다 ────────────────────────
@pytest.mark.parametrize("cls", CONFIG_CLASSES, ids=_ids)
def test_from_config_fills_every_declared_field(cls):
    """선언된 필드가 전부 채워진다.

    _extra_kwargs 에 키를 빠뜨리거나 오타를 내면 여기서 TypeError 로 죽는다.
    필드 이름을 적지 않으므로, 환경변수가 늘어도 이 테스트는 그대로다.
    """
    config = cls.from_config()

    assert isinstance(config, cls)
    assert {f.name for f in fields(cls)} == set(vars(config))


@pytest.mark.parametrize("cls", CONFIG_CLASSES, ids=_ids)
def test_extra_kwargs_keys_are_exactly_the_subclass_fields(cls):
    """_extra_kwargs 의 키 = 서브클래스가 추가한 필드.

    대소문자·오타를 이름 열거 없이 잡는다. 키 하나가 대문자였던 적이 실제로 있다.
    """
    added = {f.name for f in fields(cls)} - {f.name for f in fields(Config)}

    assert set(cls._extra_kwargs()) == added


@pytest.mark.parametrize("cls", CONFIG_CLASSES, ids=_ids)
def test_extra_kwargs_does_not_shadow_base_fields(cls):
    """서브클래스가 공통 필드를 다시 내면 안 된다.

    from_config() 은 cls(**base, **extra) 로 펼치므로 겹치면 TypeError 로 죽는다.
    죽는 게 맞는 동작이고, 그 전에 여기서 이유를 말해주는 편이 낫다.
    """
    assert set(cls._extra_kwargs()).isdisjoint(Config._base_kwargs())


@pytest.mark.parametrize("cls", CONFIG_CLASSES, ids=_ids)
def test_config_is_frozen(cls):
    """설정은 실행 중에 바뀌지 않는다. 바꾸려면 dataclasses.replace 로 새로 만든다."""
    config = cls.from_config()
    name = next(f.name for f in fields(cls))

    with pytest.raises(FrozenInstanceError):
        setattr(config, name, "other")


def test_json_outputs_are_distinct_files():
    """산출물 경로가 겹치면 뒤 단계가 앞 단계 결과를 덮어쓴다.

    load_config() 는 환경변수 「값」의 중복만 본다. _base_kwargs 가 같은 변수를
    두 번 읽으면 그 검사를 그냥 지나가므로 확정된 경로 쪽에서 한 번 더 본다.
    파일 개수를 세지 않고 .json 필드를 전부 모으므로 산출물이 늘어도 따라온다.
    """
    config = Config.from_config()
    json_paths = [
        value
        for f in fields(config)
        if (value := getattr(config, f.name)) is not None
        and str(value).endswith(".json")
    ]

    assert len(json_paths) >= 2
    assert len(set(json_paths)) == len(json_paths)


# ─── load_config — 파일명 중복을 멈춘다 ────────────────────────────
#
# load_config() 은 .env.shared 를 override=True 로 읽으므로, 그냥 monkeypatch 하면
# 파일 값이 되돌려 놓는다. 파일 읽기를 끄고 가드 자체만 태운다.


@pytest.fixture
def without_dotenv(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: None)
    return monkeypatch


def test_load_config_rejects_duplicate_file_names(without_dotenv):
    """META_FILE 이 INDEX_FILE 과 같으면 인덱스가 계측 결과에 덮인다."""
    without_dotenv.setenv("INDEX_FILE", "same")
    without_dotenv.setenv("META_FILE", "same")
    without_dotenv.setenv("META_RESULT_FILE", "diagnose")

    with pytest.raises(RuntimeError):
        load_config()


def test_load_config_passes_when_names_differ(without_dotenv):
    without_dotenv.setenv("INDEX_FILE", "index")
    without_dotenv.setenv("META_FILE", "meta")
    without_dotenv.setenv("META_RESULT_FILE", "diagnose")

    load_config()


def test_load_config_reports_missing_file_name(without_dotenv):
    """미설정은 AttributeError 가 아니라 RuntimeError 로 나와야 원인이 읽힌다."""
    without_dotenv.setenv("INDEX_FILE", "index")
    without_dotenv.setenv("META_FILE", "meta")
    without_dotenv.delenv("META_RESULT_FILE", raising=False)

    with pytest.raises(RuntimeError, match="META_RESULT_FILE"):
        load_config()


# ─── 값 규칙 — 필드 목록이 아니라 「변환 규칙」을 잠근다 ──────────────────
def test_site_url_drops_trailing_slash(monkeypatch):
    """site_url + link 로 URL 을 만들므로 끝 슬래시가 남으면 `//` 가 된다."""
    monkeypatch.setenv("DW_SITE", "https://sites.google.com/")

    assert CrawlConfig.from_config().site_url == "https://sites.google.com"


@pytest.mark.parametrize("value, expected", [("1", True), ("0", False)])
def test_flag_reaches_the_config(monkeypatch, value: str, expected: bool):
    """헬퍼 규칙이 실제 설정 객체까지 도달하는지 — 배선을 한 번만 확인한다."""
    monkeypatch.setenv("DO_CRAWL", value)

    assert CrawlConfig.from_config().do_crawl is expected


def test_blank_flag_stops_config(monkeypatch):
    """빈 플래그는 조용히 False 가 되지 않는다."""
    monkeypatch.setenv("DO_CRAWL", "")

    with pytest.raises(RuntimeError):
        CrawlConfig.from_config()
