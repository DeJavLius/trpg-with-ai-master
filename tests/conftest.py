import os
import shutil
from dataclasses import fields, replace
from pathlib import Path

import pytest

from rag_with_trpg.config import ROOT, Config, load_config
from rag_with_trpg.crawl.config import CrawlConfig

"""
title: claude 작성 python script
content: 테스트 픽스처(보일러플레이트)만 정의한다. 실제 검증(assert)은 각 test_*.py 에서 직접 작성한다.

         ♻️ 09-09 — 설정을 손으로 조립하지 않는다.
         필드를 하나하나 적어두면 Config 에 필드가 늘 때마다 여기가 먼저 깨진다
         (chunk_result_file 추가 때 실제로 그랬다). from_config() 으로 만들고
         「테스트가 건드리면 안 되는 것」만 tmp 로 돌린다.
"""


@pytest.fixture(scope="session", autouse=True)
def env() -> None:
    """실제 .env* 를 한 번 읽는다. 테스트가 환경변수 목록을 복제하지 않는다.

    USER_AGENT 만 기본값을 채운다 — .env(비커밋)에만 있어서 새 클론에는 없다.
    """
    load_config()
    os.environ.setdefault("USER_AGENT", "rag-with-trpg-test")


def sandboxed(config: Config, root: Path, *, raw_path: Path) -> Config:
    """Path 필드를 전부 `root` 밑으로 옮긴 사본. 실제 corpora/ 를 건드리지 않는다.

    필드 이름을 열거하지 않고 타입으로 고르므로, Config 에 Path 필드가 늘어도
    자동으로 따라온다. raw_path 만 인자로 받는다 — 읽기 전용 픽스처라
    실제 코퍼스를 가리켜야 하는 경우와 tmp 사본을 쓰는 경우가 갈린다.
    """
    moved = {
        f.name: root / getattr(config, f.name).name
        for f in fields(config)
        if isinstance(getattr(config, f.name), Path)
    }
    moved["raw_path"] = raw_path
    return replace(config, **moved, base_path=f"{root}/")


# 판정 경계에 쓰이는 페이지 3종 (D-04 / D-28 / D-29)
INDEX_PAGE = "직업.html"  # 인덱스 — strip 적용 175자
HOME_PAGE = "홈.html"  # 홈 — 972자. <title> 에 " - " 가 없는 유일한 페이지
BODY_PAGE = "액션.html"  # 본문 — 헤딩 24개

# 기대값 — 근거는 [[decisions phase 1]] / [[phase 1 log]] §2. 숫자를 여기 한 곳에만 둔다.
URL_KEYWORD = "/view/dwtemporary/"
SITE_URL = "https://sites.google.com"
EXPECTED_PAGES = 39  # 홈에서 긁히는 내부 링크 = raw HTML 개수
EXPECTED_MD = 38  # 39 − 인덱스 1건 (D-04)
EXPECTED_EXCLUDED = 1  # D-04. 코퍼스가 바뀌면 D-04 를 재판정한 뒤에 고친다
INDEX_TITLE = "직업"  # 제외되는 유일한 페이지의 <title> 파생 제목 (D-28)

INDEX_MD = "직업.md"
HOME_MD = "던전월드 한국어 공개판 임시 웹페이지.md"
BODY_MD = "액션.md"


@pytest.fixture(scope="session")
def raw_dir() -> Path:
    """크롤링 원본 HTML 디렉터리. 읽기 전용으로만 쓴다."""
    return ROOT / "corpora" / "dungeonworld" / "raw"


@pytest.fixture(scope="session")
def raw_files(raw_dir: Path) -> list[Path]:
    """raw/ 의 HTML 전체. 하위 디렉터리를 포함한다."""
    return sorted(raw_dir.rglob("*.html"))


@pytest.fixture(scope="session")
def read_raw(raw_dir: Path):
    """raw/ 에서 파일 하나를 이름으로 읽는 헬퍼를 돌려준다."""

    def _read(name: str) -> str:
        return (raw_dir / name).read_text(encoding="utf-8")

    return _read


@pytest.fixture(scope="session")
def index_html(read_raw) -> str:
    return read_raw(INDEX_PAGE)


@pytest.fixture(scope="session")
def home_html(read_raw) -> str:
    return read_raw(HOME_PAGE)


@pytest.fixture(scope="session")
def body_html(read_raw) -> str:
    return read_raw(BODY_PAGE)


@pytest.fixture
def make_config(tmp_path: Path, raw_dir: Path):
    """CrawlConfig 를 만들어 주는 팩토리. 호출 시점에 인자를 넣는다.

    fixture 는 인자를 직접 못 받으므로, 인자가 필요한 설정은 팩토리로 감싼다.
    raw_path 는 실제 코퍼스(읽기 전용)를 가리키고 나머지 경로는 tmp 로 간다.
    site_url 은 실제 사이트를 때리지 않도록 무효 호스트로 바꾼다.
    """

    def _make(**overrides) -> CrawlConfig:
        config = sandboxed(CrawlConfig.from_config(), tmp_path, raw_path=raw_dir)
        defaults = {
            "site_url": "https://example.invalid",
            "user_agent": "rag-with-trpg-test",
            "do_crawl": False,
            "do_create": False,
        }
        return replace(config, **(defaults | overrides))

    return _make


@pytest.fixture
def tmp_config(make_config) -> CrawlConfig:
    """플래그 기본값(False/False) 설정. 플래그만 바꿀 땐 dataclasses.replace 를 쓴다."""
    return make_config()


# ─── 축소 코퍼스 — 메타 경로 계산을 실제와 같은 모양으로 태운다 ──────────────
#
# meta_mapped 는 base_path 를 기준으로 raw/md 경로를 잘라낸다.
# raw_path 가 실제 corpora 이고 base_path 만 tmp 면 그 절단이 안 일어나므로,
# 메타 계열 테스트는 raw 까지 tmp 로 복사한 축소 코퍼스에서 돌린다.


@pytest.fixture
def corpus(tmp_path: Path, raw_dir: Path) -> Path:
    """3종 페이지만 담은 축소 코퍼스 루트. 실제 corpora/ 를 건드리지 않는다."""
    base = tmp_path / "corpus"
    (base / "raw").mkdir(parents=True)

    for name in (INDEX_PAGE, HOME_PAGE, BODY_PAGE):
        shutil.copy(raw_dir / name, base / "raw" / name)

    return base


@pytest.fixture
def corpus_config(corpus: Path) -> CrawlConfig:
    """축소 코퍼스를 가리키는 설정. raw 까지 tmp 사본이다.

    base_path 끝의 슬래시는 .env.shared 의 CORPORA_DUNGEONWORLD_PATH 와 같은 형태이고,
    PageEntry.from_page 가 base_path 를 문자열로 잘라내므로 이 형태를 맞춘다.
    """
    config = sandboxed(CrawlConfig.from_config(), corpus, raw_path=corpus / "raw")
    return replace(
        config,
        site_url=SITE_URL,
        user_agent="rag-with-trpg-test",
        do_crawl=False,
        do_create=False,
    )


# ─── 실제 산출물 — D-35 정합성 검증용. 읽기 전용 ──────────────────────────


@pytest.fixture(scope="session")
def corpora_root() -> Path:
    return ROOT / "corpora" / "dungeonworld"


@pytest.fixture(scope="session")
def md_files(corpora_root: Path) -> list[Path]:
    return sorted((corpora_root / "md").rglob("*.md"))


@pytest.fixture(scope="session")
def index_path() -> Path:
    """실제 인덱스 파일. 경로는 .env.shared 의 INDEX_FILE 에서 나온다 (D-35).

    파일명을 여기서 조립하지 않고 Config 에게 물어본다 — 조립을 두 곳에 두면
    09-07 의 파일명 드리프트가 테스트에서 안 잡힌다.
    """
    return Config.from_config().index_file
