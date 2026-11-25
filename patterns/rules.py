"""연관 규칙 생성 (보안A 담당).

작성: Claude Code가 함수 본문과 주석을 작성했고 (본인 요청), 본인이 검토했다.
      docs/AI_USE_apriori_pcy.md 참고.

규칙 A -> B 의 뜻: "A 가 관측된 창에서는 B 도 함께 관측되는 경향이 있다" (인과가 아니라 동시 관측)
- support(A -> B)    = count(A ∪ B) / n
- confidence(A -> B) = count(A ∪ B) / count(A)          # A 가 있을 때 B 도 있을 확률
- lift(A -> B)       = confidence(A -> B) / (count(B) / n)  # 1 보다 크면 우연보다 자주 같이 나옴

입력 frequent 는 apriori() 의 반환값 {itemset: count} 이다.
Apriori 성질 때문에 빈발집합의 부분집합은 모두 frequent 안에 들어 있다.
"""

from __future__ import annotations

import itertools


def nonempty_proper_subsets(itemset: frozenset) -> list[frozenset]:
    """itemset 의 공집합도 아니고 자기 자신도 아닌 부분집합을 모두 반환한다.

    예: {a, b, c} -> {a}, {b}, {c}, {a, b}, {a, c}, {b, c}  (6개, 순서는 자유)
        {a}       -> []  (크기 1 짜리는 규칙을 만들 수 없다)
    """
    result = []
    # 크기 1 부터 len-1 까지. range 의 끝 숫자는 포함되지 않으므로
    # range(1, len(itemset)) 은 1, 2, ..., len-1 을 만든다.
    # 크기 0(공집합)과 크기 len(자기 자신)은 규칙의 한쪽이 비게 되므로 뺀다.
    for size in range(1, len(itemset)):
        # combinations 는 튜플을 주므로 frozenset 으로 바꿔 frequent 의 키와 형식을 맞춘다
        for combo in itertools.combinations(itemset, size):
            result.append(frozenset(combo))
    return result  # itemset 크기가 1 이면 range(1, 1) 이 비어 있어 빈 리스트가 된다


def rule_metrics(frequent: dict[frozenset, int], n_transactions: int,
                 antecedent: frozenset, consequent: frozenset) -> tuple[float, float, float]:
    """규칙 antecedent -> consequent 의 (support, confidence, lift) 를 계산한다.

    필요한 개수는 모두 frequent 에서 꺼낸다. 데이터를 다시 훑지 않는다.
    """
    # A ∪ B 가 빈발이면 그 부분집합 A, B 도 빈발이다 (Apriori 성질)
    # → 세 개수 모두 frequent 에 있으므로 KeyError 가 나지 않고, 데이터를 다시 셀 필요도 없다
    count_ab = frequent[antecedent | consequent]  # A 와 B 가 함께 나온 거래 수
    count_a = frequent[antecedent]                # A 가 나온 거래 수
    count_b = frequent[consequent]                # B 가 나온 거래 수

    support = count_ab / n_transactions  # 전체 중 A, B 가 함께 나온 비율
    confidence = count_ab / count_a      # A 가 나온 거래 중 B 도 나온 비율 = P(B | A)
    # B 가 원래 나오는 비율 P(B) 로 나눠, A 를 알았을 때 B 확률이 몇 배가 되는지 본다.
    # 기준 비율이 작은 B (예: 공격 창 약 5%) 도 공정하게 비교할 수 있다.
    lift = confidence / (count_b / n_transactions)
    return support, confidence, lift


def generate_rules(frequent: dict[frozenset, int], n_transactions: int,
                   min_confidence: float) -> list[dict]:
    """크기 2 이상인 빈발집합 I 마다, I 를 A 와 B = I - A 로 나눠 규칙 A -> B 를 만든다.

    confidence >= min_confidence 인 규칙만 남긴다.
    규칙 하나는 아래 키를 가진 dict 로 표현한다.
        {"antecedent": A, "consequent": B, "support": ..., "confidence": ..., "lift": ...}
    반환 순서는 자유.
    """
    rules = []
    for itemset in frequent:  # 빈발집합을 하나씩 본다 (dict 를 돌면 키가 나온다)
        # 크기 1 짜리는 nonempty_proper_subsets 가 빈 리스트를 주므로 따로 거르지 않아도 된다
        for antecedent in nonempty_proper_subsets(itemset):
            consequent = itemset - antecedent  # 집합 빼기: A 에 없는 나머지 항목이 B
            support, confidence, lift = rule_metrics(frequent, n_transactions, antecedent, consequent)
            if confidence >= min_confidence:  # confidence 기준을 넘는 규칙만 남긴다
                rules.append({
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "support": support,
                    "confidence": confidence,
                    "lift": lift,
                })
    # 참고: 크기 k 집합 하나에서 2^k - 2 개의 규칙 후보가 나온다.
    # "confidence-based pruning" (A -> B 가 기준 미달이면 A 를 더 줄인 규칙도 미달)
    # 으로 이 후보 수를 줄일 수 있다. 지금은 모든 후보를 직접 검사하는 단순한 방식이다.
    return rules
