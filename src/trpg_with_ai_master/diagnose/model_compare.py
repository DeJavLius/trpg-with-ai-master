import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from huggingface_hub import try_to_load_from_cache
from huggingface_hub.file_download import _CACHED_NO_EXIST
from transformers import AutoTokenizer

from trpg_with_ai_master.crawl.index_mapped import PageEntry
from trpg_with_ai_master.diagnose.config import DiagnoseConfig
from trpg_with_ai_master.diagnose.diagnos import missing_md_files
from trpg_with_ai_master.util import load_json, save_file

# 계열 판정용 고정 문자열 — 한글 산문·숫자+단위·영문·기호를 한 문장에 넣는다.
# 계열이 갈리는 지점이 거기라, 순한글 문장으로는 XLM-R 셋이 안 갈린다.
PROBE = "마법사가 15닢으로 할버드를 산다. Roll +INT, 10+ 성공!"
NYUP = "15닢"

POOLING_MODES: dict[str, str] = {
    "pooling_mode_cls_token": "cls",
    "pooling_mode_mean_tokens": "mean",
    "pooling_mode_max_tokens": "max",
    "pooling_mode_mean_sqrt_len_tokens": "mean_sqrt_len",
    "pooling_mode_weightedmean_tokens": "weightedmean",
    "pooling_mode_lasttoken": "lasttoken",
}


@dataclass(frozen=True, kw_only=True)
class ModelProfile:
    repo_id: str

    max_seq_length: int | None  # 축 ①. sentence_bert_config.json. None = 규약 밖
    family_fingerprint: str  # 축 ②. PROBE 의 input_ids 해시.
    prefix_source: str  # "config" | "model_card" | "unknown"
    prompts: dict[str, str]  # prefix_source 의 원자료. bool 이면 「없다」와 「모른다」가 겹친다

    embedding_dim: int | None  # 바뀌면 저장한 벡터 전량 무효 = 재인덱싱
    has_normalize_layer: bool  # 있으면 코드 정규화가 무해한 중복이 된다
    pooling_mode: str | None  # 「같은 1024인데 왜 값이 다른가」의 답
    unk_token: str | None  # None 이면 byte-level BPE = UNK 가 원리적으로 없다

    hidden_size: int | None  # embedding_dim 과 같은지 교차 확인
    has_dense: bool  # 위 두 차원이 갈리는 유일한 조건
    vocab_size: int  # ⚠️ 토크나이저 값. config.json 의 vocab_size 가 아니다
    tokenizer_class: str | None  # 참고용 — paraphrase 는 신뢰 불가

    unk_kinds: int
    unk_spans: int
    nyup_round_trip: bool  # decode(encode("15닢")) == "15닢"


def read_config(repo_id: str, filename: str) -> dict | None:
    """캐시의 설정 파일을 읽는다. 네트워크 0, 가중치 0.

    hf_hub_download(local_files_only=True) 를 쓰면 「repo 오타」·「캐시에 없음」·
    「허브에 파일이 없음」이 전부 LocalEntryNotFoundError 하나로 와서 구분이 안 된다.
    try_to_load_from_cache 는 그 셋을 세 값으로 돌려주므로, 판정을 예외에 맡기지 않는다.

    None 은 「허브에 그 파일이 없다」 — 규약 밖이라는 관측이지 에러가 아니다.
    """
    state = try_to_load_from_cache(repo_id, filename)

    if state is _CACHED_NO_EXIST:
        return None
    if state is None:
        raise FileNotFoundError(
            f"{repo_id} 의 {filename} 이 캐시에 없습니다. repo_id 의 조직 접두를 확인하거나"
            f" `uv run hf download {repo_id}` 로 먼저 받으세요."
        )

    return json.loads(Path(state).read_text(encoding="utf-8"))


def compare(config: DiagnoseConfig) -> None:
    print("[1] compare: markdown files & index load")
    corpus = load_corpus(config)

    print("[2] compare: profile collect (가중치 0)")
    profiles = [
        profile(repo_id, local_only=config.model_local_only, corpus=corpus)
        for repo_id in config.model_compare_repos
    ]

    print("[3] compare: result")
    print_profiles(profiles)
    save_file(
        config.model_compare_file.stem,
        config.model_compare_file,
        json.dumps([asdict(p) for p in profiles], ensure_ascii=False, indent=2),
    )


def load_corpus(config: DiagnoseConfig) -> list[str]:
    index_pages = load_json(PageEntry, config, "index_file")
    extract_pages = [page for page in index_pages if page.excluded is None]

    missing = missing_md_files(config.base_path, extract_pages)
    if missing:
        raise RuntimeError(
            f"인덱스가 가리키는 markdown {len(missing)}건이 없습니다: {', '.join(missing)}. "
            f"크롤을 다시 돌리거나 인덱스를 재생성하세요."
        )

    return [
        Path(config.base_path + page.md).read_text(encoding="utf-8")
        for page in extract_pages
    ]


def profile(repo_id: str, *, local_only: bool, corpus: list[str]) -> ModelProfile:
    """설정 6필드는 read_config 로, 토크나이저 4필드는 AutoTokenizer 로 읽는다.

    가중치는 받지 않는다 — 비교표의 모든 칸이 수 KB 짜리 JSON 과 토크나이저에서 나온다.
    """
    sbert = read_config(repo_id, "sentence_bert_config.json")
    pooling = read_config(repo_id, "1_Pooling/config.json")
    modules = read_config(repo_id, "modules.json") or []
    backbone = read_config(repo_id, "config.json") or {}
    st_config = read_config(repo_id, "config_sentence_transformers.json")

    module_types = [m["type"].rsplit(".", 1)[-1] for m in modules]
    # 파일이 없는 것(None)과 키가 없는 것을 여기서 같은 {} 로 접는다.
    # 둘의 구분은 read_config 가 이미 했고, 판정에 필요한 것은 「값이 있는가」뿐이다.
    prompts = (st_config or {}).get("prompts") or {}

    tokenizer = AutoTokenizer.from_pretrained(repo_id, local_files_only=local_only)
    unk_kinds, unk_spans = unk_analyze(tokenizer, corpus)

    return ModelProfile(
        repo_id=repo_id,
        max_seq_length=(sbert or {}).get("max_seq_length"),
        family_fingerprint=fingerprint(tokenizer),
        prefix_source="config" if any(prompts.values()) else "unknown",
        prompts=prompts,
        embedding_dim=(pooling or {}).get("word_embedding_dimension"),
        has_normalize_layer="Normalize" in module_types,
        pooling_mode=pooling_mode(pooling),
        unk_token=tokenizer.unk_token,
        hidden_size=backbone.get("hidden_size"),
        has_dense="Dense" in module_types,
        vocab_size=tokenizer.vocab_size,
        tokenizer_class=type(tokenizer).__name__,
        unk_kinds=unk_kinds,
        unk_spans=unk_spans,
        nyup_round_trip=round_trip(tokenizer, NYUP),
    )


def pooling_mode(pooling: dict | None) -> str | None:
    if pooling is None:
        return None

    for key, name in POOLING_MODES.items():
        if pooling.get(key) is True:
            return name

    return None


def fingerprint(tokenizer) -> str:
    """메타데이터가 아니라 동작으로 계열을 잰다 — D-18.

    tokenizer_config.json 의 tokenizer_class 를 믿으면 paraphrase 만
    PreTrainedTokenizerFast 로 나와 같은 계열인 bge-m3·e5-large 와 안 묶인다.
    """
    ids = tokenizer(PROBE, add_special_tokens=False)["input_ids"]
    return hashlib.sha256(str(ids).encode()).hexdigest()[:10]


def round_trip(tokenizer, text: str) -> bool:
    ids = tokenizer(text, add_special_tokens=False)["input_ids"]
    return tokenizer.decode(ids) == text


def unk_analyze(tokenizer, corpus: list[str]) -> tuple[int, int]:
    """UNK 를 offset 으로 되짚어 종류 수와 출현 수를 센다 — 축 ②.

    문자별 decode(encode(c)) == c 로 재면 공백·개행이 오탐으로 잡힌다.
    decode 가 공백만인 문자열을 빈 문자열로 돌려주기 때문이고, offset 판정은 그게 없다.
    """
    if tokenizer.unk_token_id is None:  # byte-level BPE — UNK 가 원리적으로 없다
        return 0, 0

    kinds: set[str] = set()
    spans = 0
    for text in corpus:
        encoded = tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            verbose=False,
        )
        for token_id, (start, end) in zip(
            encoded["input_ids"], encoded["offset_mapping"]
        ):
            if token_id == tokenizer.unk_token_id:
                kinds.add(text[start:end])
                spans += 1

    return len(kinds), spans


def print_profiles(profiles: list[ModelProfile]) -> None:
    """판정 3 + 파급 4 만 낸다. 검증 4필드는 덤프에만 남는다 — 읽는 비용이 그쪽이다."""
    rows: list[tuple[str, str, list[str]]] = [
        ("판정 ①", "max_seq_length", [str(p.max_seq_length) for p in profiles]),
        ("판정 ②", "계열 지문", [p.family_fingerprint for p in profiles]),
        ("판정", "프리픽스", [p.prefix_source for p in profiles]),
        ("파급", "문장 임베딩 차원", [str(p.embedding_dim) for p in profiles]),
        ("파급", "Normalize", ["O" if p.has_normalize_layer else "X" for p in profiles]),
        ("파급", "Pooling", [str(p.pooling_mode) for p in profiles]),
        ("파급", "unk_token", [str(p.unk_token) for p in profiles]),
        ("축 ②", "UNK 종류/출현", [f"{p.unk_kinds}/{p.unk_spans}" for p in profiles]),
        ("축 ②", "15닢 round-trip", ["O" if p.nyup_round_trip else "X" for p in profiles]),
    ]

    names = [p.repo_id.rsplit("/", 1)[-1][:22] for p in profiles]
    print(f"{'':<8}{'':<18}" + "".join(f"{n:<24}" for n in names))
    for tier, label, values in rows:
        print(f"{tier:<8}{label:<18}" + "".join(f"{v:<24}" for v in values))

    print(f"\n{family_summary(profiles)}")


def family_summary(profiles: list[ModelProfile]) -> str:
    """계열이 같으면 축 ② 도 같은지 — 완료 조건 3번. 가정이 아니라 실측으로 확인한다."""
    families: dict[str, list[ModelProfile]] = {}
    for p in profiles:
        families.setdefault(p.family_fingerprint, []).append(p)

    lines = []
    for fp, members in families.items():
        names = ", ".join(m.repo_id.rsplit("/", 1)[-1] for m in members)
        measures = {(m.unk_kinds, m.unk_spans) for m in members}
        verdict = "축 ② 동일" if len(measures) == 1 else f"⚠️ 축 ② 불일치: {measures}"
        lines.append(f"계열 {fp} ({len(members)}종): {names} — {verdict}")

    return "\n".join(lines)
