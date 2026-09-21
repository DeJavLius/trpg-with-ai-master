import numpy as np
from sentence_transformers import SentenceTransformer

# from google import genai
# client = genai.Client()

# 1. Load a pretrained Sentence Transformer model
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
model_max_size: int = model.max_seq_length
over_max_size: int = 0

# 던전월드 액션 페이지 3개 문단
DOCS: list[str] = [
    """
마법사
이 세계는 법칙으로 움직입니다. 그 법칙은 사람의 법률도 아니고, 어느 좀스러운 폭군의 변덕도 아닙니다. 그보다 더 크고, 더 좋은 법칙입니다. 잡고 있던 물건을 놓으면 떨어지고, 무에서 유를 만들 수는 없으며, 죽은 것은 도로 살아나지 않습니다. 맞지요?

그렇게라도 믿지 않으면 무서워서 잠을 잘 수가 없을 것입니다.

당신은 고서에 얼굴을 파묻고 오랜 시간을 보냈습니다. 실험 때문에 미칠 뻔한 적도 많고, 소환 의식이 잘못되어 영혼이 날아갈 뻔 한 적도 있습니다. 그 모든 것은 무엇을 위해서 한 것입니까? 당연히 힘을 위해 한 것입니다. 달리 추구할 것이 세상에 어디 있단 말입니까? 산 사람의 혈관에 흐르는 피를 삽시간에 끓어오르게 만드는 힘, 하늘에서 천둥을 부르고 땅을 흔드는 힘. 세상 사람들이 그렇게나 믿고 싶어하는 법칙들을 벗어던지는 힘. 그것이 마법입니다.

남들은 당신을 백안시합니다. 등 뒤에서 “흑마술사”니 “악마소환사”니 수군대며 손가락질을 합니다. 물론 그것은 우주의 비밀을 알지 못하는 자들의 질투일 뿐입니다.

이름

엘프: 갈라디르, 릴리아스트르, 엔키라쉬, 펜파릴, 피로살, 할위르.

인간: 라스, 모르간, 비투스, 아본, 알다라, 오비드, 이솔데, 유리, 제노.

외모

항목별로 하나씩 고릅니다:

뭔가에 씐 듯한 눈, 날카로운 눈, 미친 듯한 눈.

다듬지 않은 머리, 모양을 낸 머리, 뾰족 모자.

괴상하게 생긴 로브, 멋을 낸 로브, 낡은 로브.

마른 몸매, 통통한 몸매, 기이한 체형.

수치

최대 HP는 4+체력입니다.

기본 피해는 d4입니다.
""",
    """
핵심 액션

종족을 선택하면 그에 따른 액션을 얻습니다.

엘프

마법을 마치 숨 쉬는 것처럼 자연스럽게 느낍니다. 마법 탐지가 간편주문이 됩니다.

인간

사제 주문을 하나 선택하십시오. 이 주문은 마치 마법사 주문인 것처럼 사용할 수 있습니다.

다음은 마법사가 처음에 갖고 시작하는 액션들입니다.

주문서

주문서에는 마법사가 익힌 주문이 모두 기록되어 있습니다. 처음에는 간편주문 전부와 1레벨 주문 3개를 갖고 시작합니다 레벨이 오를 때마다 주문서에 자기 레벨 이하의 새로운 주문을 하나 추가하십시오. 주문서의 무게는 1입니다.

주문 준비

1시간 정도 방해를 받지 않고 주문서를 조용히 정독하면 다음과 같은 효과가 일어납니다:

• 현재 준비된 주문을 모두 잃습니다.

• 자기가 선택하는 주문이 하나 이상 준비됩니다. 주문 레벨의 합은 자기 레벨 +1을 넘을 수 없고, 자기 레벨보다 높은 주문은 선택할 수 없습니다.

• 간편주문이 모두 준비됩니다. 간편주문은 주문 레벨 제한에 해당되지 않습니다.

주문 시전

준비된 주문을 사용하면 +지 판정을 합니다. 10+이면 주문이 부작용 없이 성공적으로 시전됩니다. 원하면 다음에 또 걸 수도 있습니다. 7~9가 나오면 주문은 시전되지만 다음의 부작용 중 하나가 일어납니다:

• 곤란한 상황에 처하거나 원치 않는 주의를 끌게 됩니다. 마스터가 정합니다.

• 주문이 현실의 구조를 어지럽힙니다. 다시 주문 준비를 할 때까지 주문 시전 판정에 계속 -1을 받습니다.

• 주문을 잊어 버립니다. 주문 준비를 할 때까지, 이 주문은 사용할 수 없습니다.

지속적인 효과를 가진 주문은 작용하는 동안 주문 시전에 페널티를 주는 일도 있으니 참고하십시오.

주문 방어

지속되는 주문 하나를 중단하면 그 소멸 에너지를 사용하여 자기에게 닥치는 공격을 방어할 수 있습니다. 주문은 끝나고, 공격의 피해가 주문의 레벨만큼 줄어듭니다. 간편주문은 레벨 0으로 간주합니다.

마법 의식

힘이 서린 장소에서 마력을 끌어다가 마법적 효과를 만들 때, 마스터에게 무엇을 하려고 하는지 말하십시오. 마법 의식에 의한 효과는 무엇이건 실현 가능하지만, 마스터는 다음 조건 중에서 1~4가지를 골라 제시할 것입니다:

• 며칠/몇 주/몇 개월이 걸립니다.

• 그 전에 _________를 해야 합니다.

• _________의 도움을 받아야 합니다.

• 돈이 많이 듭니다.

• 제한되고 신뢰성 낮은 약화판으로 밖에 할 수 없습니다.

• 자신과 동료들이 _________ 때문에 위험에 처하게 됩니다.

• _________ (특정 마법 물품)에 걸린 마법을 깨야 의식을 할 수 있습니다.

가치관

가치관을 하나 선택합니다:

선

마법을 이용하여 다른 사람을 직접적으로 돕습니다.

중립

마법적 수수께끼에 관한 사실을 밝혀냅니다.

악

마법을 이용하여 공포와 혼란을 일으킵니다.

장비

하중은 7+근입니다. 갖고 있는 물건은 다음과 같습니다:

• 주문서 (무게 1), 던전용 식량 (5회분, 무게 1).

다음 중 하나 선택:

• 가죽 갑옷 (장갑 1, 무게 1).

• 책 자루 (5회분, 무게 2), 치료약 3병.

무기 선택:

• 단검 (반걸음, 무게 1).

• 지팡이 (한걸음, 양손, 무게 1).

다음 중 하나 선택:

• 치료약 (무게 0).

• 해독제 3병 (무게 0).

인연

다음 중 최소한 하나에 동료 모험가의 이름을 기입하십시오:

내가 예언하건대, _________는 다가오는 미래에 중요한 역할을 하게 될 것이다!

_________는 내게서 중요한 비밀을 감추고 있다.

_________는 세상에 대해 몰라도 너무 모른다. 내가 가르칠 수 있는 것은 다 가르쳐야겠다.
""",
    """
고급 액션

레벨이 2~5에 달할 때마다 다음 액션 중 하나를 선택하십시오.

천재

주문 하나를 고르십시오. 그 주문은 마치 1레벨 낮은 것처럼 다룹니다. 이로써 0레벨이 된 주문은 간편주문으로 간주합니다.

주문 강화

주문을 시전할 때, 10+가 나오더라도 원하면 7~9의 부작용을 하나 택하고 다음의 두 효과 중 하나를 택할 수 있습니다:

• 주문의 효과가 2배 됩니다.

• 주문의 대상이 2배 됩니다.

지식의 샘

다른 누구도 전혀 감을 잡지 못하는 것에 대해 지식 더듬기를 사용하면 판정에 +1을 받습니다.

만물박사

다른 플레이어 캐릭터가 조언을 구하고 마법사가 이에 솔직하게 대답하는 경우, 상대가 그 조언을 따르면 상대는 다음 판정에 +1을 받고, 마법사는 경험치를 얻습니다.

증보

직업에 관계 없이 주문을 하나 골라 주문서에 추가합니다.

물품 분석

시간이 충분하고 안전한 상황에서 마법 물품을 분석하면 마스터가 그 물품의 마법적 기능을 사실대로 밝힙니다.

논리적

엄정한 추리를 통해 주변을 분석하면, 상황 파악을 +혜 대신 +지로 할 수 있습니다.

마력의 방패

1레벨 이상의 주문을 하나 이상 준비한 상태이면 장갑에 +2를 받습니다.

주문 차단

자기에게 영향을 줄 주문을 차단하려 할 때, 준비된 주문을 하나 걸고 +지 판정을 합니다. 10+이면 상대의 주문은 차단되고 자신에게는 아무 일도 일어나지 않습니다. 7~9이면 상대의 주문은 자단되고, 자신은 걸었던 주문을 잊습니다. 주문 차단은 자신만을 보호합니다. 그 주문이 다른 대상에게도 영향을 주는 경우, 다른 대상들에 대한 효과는 원래대로 일어납니다. 마법사, 음유시인 등이 쓰는 세속 마법에 대해서만 사용할 수 있으며, 신성 마법 계통의 주문에는 통하지 않습니다.

주문 추리

주문의 효과를 목격했을 때, 마스터에게 주문의 이름과 효과를 물을 수 있습니다. 그 대답에 의거하여 행동하면 다음 판정에 +1을 받습니다. 마법사, 음유시인 등이 쓰는 세속 마법에 대해서만 사용할 수 있으며, 신성 마법 계통의 주문에는 통하지 않습니다.

레벨이 6~10에 달할 때마다 아래 액션들이나 앞의 2~5레벨 액션들 중에서 하나를 선택하십시오.

대가

필요: 천재.

천재로 고르지 않은 주문을 하나 고르십시오. 그 주문은 마치 1레벨 낮은 것처럼 다룹니다. 이로써 0레벨이 된 주문은 간편주문으로 간주합니다.

상급 주문 강화

대체: 주문 강화.

주문을 시전할 때, 10~11이면 원할 경우 7~9의 부작용을 하나 고르고 다음의 두 효과 중 하나를 택할 수 있습니다. 12가 나오면 부작용을 고르지 않고 효과를 하나 선택합니다:

• 주문의 효과가 2배 됩니다.

• 주문의 대상이 2배 됩니다.

물품 강화

필요: 물품 분석.

힘이 서린 장소에 있을 때, 안전한 상황에서 시간을 들여 마법 물품에 힘을 불어 넣으면 다음 번에 사용할 때 효과가 증폭됩니다. 어떻게 증폭될지는 마스터가 설명할 것입니다.

매우 논리적

대체: 논리적.

엄정한 추리를 통해 주변을 분석하면, 상황 파악을 +혜 대신 +지로 할 수 있습니다. 12+이면 목록에 구애 받지 않고 아무 질문이나 세 가지를 할 수 있습니다.

마력의 갑옷

대체: 마력의 방패.

1레벨 이상의 주문을 하나 이상 준비한 상태이면 장갑에 +4를 받습니다.

마법 차폐

필요: 주문 차단.

자기 시야 내에 있는 우리 편이 주문에 영향을 받으려 할 때, 마치 자기에게 그 주문이 닥친 것처럼 주문을 차단할 수 있습니다. 절차는 주문 차단과 같습니다. 주문이 둘 이상에 대해 영향을 주는 경우 대상마다 따로 차단을 해야 합니다. 마법사나 음유시인의 세속적인 마법에 대해서만 사용할 수 있으며, 신성 마법 계통의 주문에는 통하지 않습니다.

에테르의 끈

보이지 않는 끈으로 자신과 다른 사람을 연결할 수 있습니다. 대상은 연결에 동의하거나, 저항할 수단이 없어야 합니다 (묶여 있다거나). 이렇게 연결되면 거리에 관계 없이 대상이 보고 듣는 것을 자신도 보고 들을 수 있게 되고, 대상이나 그 주변에 대해 상황 파악을 할 수 있게 됩니다. 동의해서 연결된 사람은, 마법사와 마치 곁에 있는 것처럼 대화할 수 있습니다.

꼭두각시

마법을 사용하여 사람을 조종한 경우, 대상들은 조종 당한 동안의 기억이 없고, 자기가 조종 당했다는 사실도 알지 못합니다.

주문 접지

자신이 피해를 줄 때, 지속 중인 주문의 에너지를 그리로 돌릴 수 있습니다. 지속 중인 주문을 하나 종료하면 그 주문의 레벨이 피해에 추가됩니다.

마력 응집

시간과 재료, 그리고 안전한 공간이 있으면 그 장소에 마력을 깃들게 하여 힘이 서린 장소를 만들 수 있습니다. 어떤 종류의 힘을 어떻게 불어 넣을 것인지 마스터에게 말하십시오. 마스터는 이 작업에 (괴물이건 사람이건) 어떤 존재가 관심을 가질 만한지 정해서 가르쳐 줄 것입니다.
""",
]


# 단순 size 글자 slice
### 개선 ###
# fixed / recursive / semantic 3종 구현, 비교
def chunk(text: str, size: int = 200, overlap: int = 0) -> list[str]:
    chunk_size: int = size - overlap
    text_length: int = len(text)
    result: list[str] = []

    if text_length <= size:
        result.append(text)
    else:
        times: int = text_length // chunk_size + 1
        i, j, c = 0, 0, 0
        while j < times:
            c = min(i + size, text_length)
            sentence = text[i:c]

            if len(sentence) > 0:
                result.append(sentence)

            i = i + chunk_size
            j += 1

    return result


# 각 청크가 모델 입력 한계 안에 들어가는지 확인한다.
# tokenizer는 model.tokenizer로 꺼낼 수 있다.
# 출력: 청크별 토큰 수, 모델 max_seq_length, 초과한 청크의 비율
# (n, d) 배열 리턴. SentenceTransformer 로드는 함수 밖에서 1회
### 개선 ###
# 한국어 모델 3종 비교, 차원, 정규화 이해
def embed(texts: list[str], log_flag: bool = False) -> np.ndarray:
    _over_max_size: int = 0

    embedded_data = model.encode(texts)
    tok = model.tokenizer
    if log_flag:
        print(embedded_data)

    for text in texts:
        token = tok.encode(text)
        token_size = len(token)
        size = len(text)

        # 실측 level
        print(
            f"토큰 크기: {token_size}, 원문 크기: {size}, 자/토큰 비율: {size / token_size}"
        )
        if token_size > model_max_size:
            _over_max_size += 1

    if log_flag:
        print(f"{_over_max_size}, {len(texts)}, 초과율: {_over_max_size / len(texts)}")
    return embedded_data


# 코사인 유사도 상위 k개. DB 없이 정규화 후 행렬 곱 한줄
### 개선 ###
# numpy > pgvector / Qdrant, HNSW 파라미터 실측
def search(query: str, mat: np.ndarray, chunks: list[str], k: int = 3) -> list[str]:
    v_query = embed([query]).flatten()
    n_query = v_query / np.linalg.norm(v_query)
    n_mat = mat / np.linalg.norm(mat, axis=1)[:, np.newaxis]
    mat_result = n_mat @ n_query
    print(f"similarity result: {mat_result}")
    top_ranks = np.argsort(-mat_result)[:k]
    return [str(chunks[i]) for i in top_ranks]


def search_by_model(
    query: str, mat: np.ndarray, chunks: list[str], k: int = 3
) -> list[str]:
    v_query = embed([query])
    scores = model.similarity(v_query, mat)
    score = np.array(scores)[0]
    top_index = np.argsort(-score)[:k]
    return [str(chunks[i]) for i in top_index]


def search_test(query: str, mat: np.ndarray, k: int = 3):
    _query = embed([query])
    v_query = _query.flatten()
    n_query = v_query / np.linalg.norm(v_query)
    n_mat = mat / np.linalg.norm(mat, axis=1)[:, np.newaxis]
    mat_result = n_mat @ n_query
    v_ranks = np.argsort(-mat_result)

    scores = model.similarity(_query, mat)
    print(mat_result, scores)
    print(np.allclose(mat_result, scores))
    f_scores = np.asarray(scores)[0]
    ranks = np.argsort(-f_scores)

    print(v_ranks, ranks)


# 컨텍스트를 프롬프트에 넣고 LLM 호출
# 비용으로 일단 정지
### 개선 ###
# 프롬프트 설계, top-k 근거, 출처 표시
# def answer(query: str, ctx: list[str]) -> str:
#     context_text = "\n\n".join(ctx)
#     interaction = client.interactions.create(
#         model="gemini-3.6-flash",
#         system_instruction="주어진 컨텍스트만 근거로 답하십시오. 컨텍스트에 없으면 모른다고 답하십시오.",
#         input=f"컨텍스트:\n{context_text}\n\n질문: {query}",
#     )
#     return interaction.output_text


# 질문 입력 > 검색 > 답변 출력
### 개선 ###
# FastAPI로 노출
def execute():
    print(f"모델 토큰 길이: {model_max_size}")

    question = "마법사가 사용하는 주문은?"
    t1 = chunk(DOCS[1], size=220)
    t2 = chunk(DOCS[1], size=240)
    t3 = chunk(DOCS[1], size=260)
    eb1 = embed(t1, True)
    eb2 = embed(t2, True)
    eb3 = embed(t3, True)
    print(search(question, eb1, t1))
    print(search(question, eb2, t2))
    print(search(question, eb3, t3))
    search_test(question, eb1)
    search_test(question, eb2)
    search_test(question, eb3)
    # print(answer(question, result))
