import json
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from transformers import AutoTokenizer, SentencePieceBackend, TokenizersBackend

from trpg_with_ai_master.crawl.convert import extract
from trpg_with_ai_master.crawl.index_mapped import PageEntry
from trpg_with_ai_master.diagnose.config import DiagnoseConfig
from trpg_with_ai_master.util import header_counting, load_json, save_file


@dataclass(kw_only=True)
class DiagnoseMeta:
    title: str
    chars: int
    headings: list[int]
    tokens: int = 0
    chars_per_token: float = 0.0
    unk_tokens: dict[str, int] | None = None


@dataclass(kw_only=True)
class DiagnoseResult:
    max_sequence_length: int = 0
    count: int = 0
    average_cpt: float = 0.0
    max_cpt: float = 0.0
    min_cpt: float = 0.0
    lower_ten_percent_cpt: float = 0.0
    upper_ten_percent_cpt: float = 0.0
    safe_chars: float = 0.0
    cpt_ranking_by_worst: list[str] = field(default_factory=list)

    def print_result(self) -> None:
        print(
            f"[결과 출력]: 총 {self.count} 페이지\n"
            + f"페이지별 자/토큰(page size / token size) 비율 > 평균: {self.average_cpt} | 최소: {self.min_cpt} | 최대: {self.max_cpt}\n"
            + f"상위/하위 10% 비율 > 상위 10%: {self.upper_ten_percent_cpt} | 하위 10%: {self.lower_ten_percent_cpt}\n"
            + f"모델 사이즈({self.max_sequence_length})에 따른 안전 토큰: {self.safe_chars}\n"
            + f"토큰화가 불리한 페이지 순위: \n{"\n".join([f"{i + 1}. {v}" for i, v in enumerate(self.cpt_ranking_by_worst)])}"
        )


def diagnose(config: DiagnoseConfig):
    # local_only 를 안 넘기면 「로컬만 쓴다」가 조용히 무시되고 매번 허브 리비전을 확인한다.
    tokenizer: TokenizersBackend | SentencePieceBackend = AutoTokenizer.from_pretrained(
        config.embed_test_model, local_files_only=config.model_local_only
    )

    print("[1] diagnose: markdown files & index load")
    index_pages = load_json(PageEntry, config, "index_file")
    extract_pages = list(filter(lambda x: x.excluded is None, index_pages))

    # 재기 전에 입력을 검사한다 — D-35 6항목의 5번 (D-34 「가드」).
    # meta_analyze 가 md 를 전부 읽으므로, 뒤에 두면 여기 도달하기 전에
    # FileNotFoundError 로 죽어 「어느 것이 몇 건 없는지」를 못 본다.
    missing = missing_md_files(config.base_path, extract_pages)
    if missing:
        raise RuntimeError(
            f"인덱스가 가리키는 markdown {len(missing)}건이 없습니다: {', '.join(missing)}. "
            f"크롤을 다시 돌리거나 인덱스를 재생성하세요."
        )

    print("[2] diagnose: start round-trip check")
    meta_list = meta_analyze(config, tokenizer, extract_pages)
    save_file(
        config.meta_file.stem,
        config.meta_file,
        json.dumps([asdict(e) for e in meta_list], ensure_ascii=False, indent=2),
    )

    print("[3] diagnose: start analys meta result")
    cpt_ratios = [meta.chars_per_token for meta in meta_list]
    result = DiagnoseResult(
        max_sequence_length=config.embed_test_max_seq,
        count=len(meta_list),
        average_cpt=statistics.fmean(cpt_ratios),
        min_cpt=min(cpt_ratios),
        max_cpt=max(cpt_ratios),
        lower_ten_percent_cpt=statistics.quantiles(cpt_ratios, n=10)[0],
        upper_ten_percent_cpt=statistics.quantiles(cpt_ratios, n=10)[-1],
        safe_chars=config.embed_test_max_seq * min(cpt_ratios),
        cpt_ranking_by_worst=[
            ms.title for ms in sorted(meta_list, key=lambda m: m.chars_per_token)
        ],
    )
    save_file(
        config.meta_result_file.stem,
        config.meta_result_file,
        json.dumps(asdict(result), ensure_ascii=False, indent=2),
    )

    print("[4] diagnose: final result")
    index_md_result = index_file_diagnose(config.base_path, index_pages)
    print(
        f"[정보 출력]: 엔트리 {len(index_pages)}건, excluded {len(index_pages) - len(extract_pages)}건\n"
        + f"markdown {len(extract_pages)}건, slug 고유 여부: {slug_check(index_pages)} \n"
        + f"markdown 누락: {len(missing)}건 \n"
        + f"제외 건 markdown 상세: \n{print_index_md(index_md_result)} \n"
    )
    result.print_result()


def slug_check(index_pages: list[PageEntry]) -> int:
    result_set = set()
    for index_page in index_pages:
        result_set.add(index_page.slug)
    return len(index_pages) == len(result_set)


def missing_md_files(base_path: str, extract_pages: list[PageEntry]) -> list[str]:
    """인덱스가 가리키는 md 중 실제로 없는 것들 — D-35 6항목의 5번.

    bool 이 아니라 목록을 돌려준다. 「하나라도 없다」만 알면 38건 중 어느 것인지
    다시 뒤져야 하고, 그 추적 비용 때문에 결국 아무도 안 보게 된다.

    page.md 가 None 인 엔트리(제외 건)는 여기 오면 안 된다 — 호출부가 거르지만
    가정을 함수 밖에 두면 호출부가 하나 늘 때 조용히 TypeError 가 된다.
    """
    return [
        page.md
        for page in extract_pages
        if page.md is None or not Path(base_path + page.md).is_file()
    ]


def index_file_diagnose(
    base_path: str, index_pages: list[PageEntry]
) -> list[DiagnoseMeta]:
    index_meta_list = []
    for index_page in index_pages:
        if index_page.excluded == "index":
            raw_file = Path(base_path + index_page.raw)
            html = raw_file.read_text(encoding="utf-8")
            title, content = extract(html)
            md_total, md_head_count = header_counting(content)
            index_meta_list.append(
                DiagnoseMeta(title=title, chars=md_total, headings=md_head_count)
            )
        else:
            continue
    return index_meta_list


def print_index_md(index_meta_list: list[DiagnoseMeta]) -> str:
    return "\n".join(
        [
            f"title: {meta.title} - chars: {meta.chars}, headings: {meta.headings}"
            for meta in index_meta_list
        ]
    )


def meta_analyze(
    config: DiagnoseConfig,
    tokenizer: TokenizersBackend | SentencePieceBackend,
    index_pages: list[PageEntry],
) -> list[DiagnoseMeta]:

    meta_list: list[DiagnoseMeta] = []
    for i, index_page in enumerate(index_pages):
        meta = DiagnoseMeta(
            title=index_page.title, chars=index_page.chars, headings=index_page.headings
        )
        markdown_path = Path(config.base_path + index_page.md)
        markdown_file = markdown_path.read_text(encoding="utf-8")

        unk_text_dict: dict[str, int] = {}
        encode_token = tokenizer(
            markdown_file,
            add_special_tokens=False,
            return_offsets_mapping=True,
            verbose=False,
        )
        for index_id, (start, end) in zip(
            encode_token["input_ids"], encode_token["offset_mapping"]
        ):
            if index_id == tokenizer.unk_token_id:
                if unk_text_dict.get(markdown_file[start:end]) is None:
                    unk_text_dict[markdown_file[start:end]] = 1
                else:
                    unk_text_dict[markdown_file[start:end]] += 1

        if len(unk_text_dict.items()) == 0:
            print(f"round-check({i}): {index_page.title} - no unk tokens")
            meta.unk_tokens = None
        else:
            print(
                f"round-check({i}): {index_page.title} - 글자 {", ".join(unk_text_dict.keys())} unk 발견, 총 {sum(map(lambda v: v, unk_text_dict.values()))}개"
            )
            meta.unk_tokens = unk_text_dict

        meta.tokens = len(encode_token.tokens())
        meta.chars_per_token = meta.chars / meta.tokens

        meta_list.append(meta)

    return meta_list
