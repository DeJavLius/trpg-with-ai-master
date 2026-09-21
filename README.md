# rag-with-dw-trpg

AI 에이전트에게 TRPG 문서를 RAG화 하여 게임 마스터 역할을 수행할 수 있도록 제공하고자 함

프레임워크(LangChain / LlamaIndex) 없이 RAG 파이프라인을 직접 구현하며,
각 설계 결정의 근거를 `DECISIONS.md`에 남기는 것을 목표로 한다.

## 실행

```bash
uv sync
uv run trpg-with-ai-master
```

## 라이선스

이 저장소는 **두 라이선스가 섞여 있습니다.**

| 대상 | 라이선스 | 파일 |
|:--|:--|:--|
| 코드 (`src/`, `tests/`) | MIT | [LICENSE](LICENSE) |
| 코퍼스 (`corpora/`) | CC BY | [corpora/LICENSE-CORPUS.md](corpora/LICENSE-CORPUS.md) |

`corpora/` 아래 문서는 제3자 저작물이며 **MIT가 적용되지 않습니다.**

### 저작자 표시

**던전월드 한국어 공개판** — CC BY 3.0 Unported

> 이 저작물은 Sage LaTorra, Adam Koebel의 Dungeon World를 김성일(도서출판 초여명)이 번역한 「던전월드 한국어 공개판」의 내용을 포함하며, 크리에이티브 커먼즈 저작자표시 3.0 Unported 라이선스에 따라 이용합니다. 원문을 크롤링하여 마크다운으로 변환·분할 가공했습니다.

**D&D SRD 5.2.1** — CC BY 4.0 · *Phase 2부터 사용 예정*

> This work includes material from the System Reference Document 5.2.1 ("SRD 5.2.1") by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.

### 상표

CC BY는 상표권을 licensing하지 않습니다. "Dungeons & Dragons", "D&D", 관련 로고를 서비스명·도메인·브랜딩에 사용하지 않습니다.
