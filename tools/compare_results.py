"""리팩터링 전후 결과 폴더를 비교한다. 실행 시간 열은 무시하고, 나머지 값이 같은지 확인한다.

작성: Claude Code (본인 요청). docs/REFACTOR_GUIDE.md 의 검증 단계에서 사용한다.

사용법 (dm-team3 폴더에서):
    python -m tools.compare_results <수정 전 결과 폴더> <수정 후 결과 폴더>
    예) python -m tools.compare_results results_before results

- 두 폴더에 같은 이름으로 있는 .csv / .csv.gz / .json 파일을 비교한다.
- 실행 시간 열(키)은 아래 TIMING_COLUMNS 에 적힌 것만 무시한다.
  (delay_s, delay_median_s 처럼 이름이 _s 로 끝나도 탐지 지연 "지표" 는 비교한다.)
  추가로 무시할 열이 있으면 세 번째 인자로 쉼표로 구분해 준다: ... results_before results run_ms,foo_ms
- 숫자는 상대 오차 1e-9 까지 같다고 본다 (부동소수점 마지막 자리 차이 허용).
- 한쪽에만 있는 파일, 다른 열, 다른 값을 모두 출력하고, 하나라도 다르면 종료 코드 1 을 낸다.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

# 팀원 run.py 와 보안A 실험이 기록하는 실행 시간 열 (재실행마다 달라지는 값)
TIMING_COLUMNS = {
    "median_ms", "exact_ms", "minhash_ms", "lsh_ms", "runtime_s", "index_build_s",  # run.py
    "mine_s", "apriori_median_s", "pcy_median_s",                                   # 보안A
}
EXTRA_IGNORED: set[str] = set()


def is_timing(name: str) -> bool:
    """열/키 이름이 실행 시간이면 True."""
    return name in TIMING_COLUMNS or name in EXTRA_IGNORED


def same_number(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def compare_json(a, b, path="") -> list[str]:
    """JSON 을 재귀적으로 비교해 다른 위치 목록을 돌려준다. 시간 키와 버전 정보는 건너뛴다."""
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if is_timing(key) or key in {"python", "numpy", "pandas", "platform", "run_at"}:
                continue
            if key not in a or key not in b:
                diffs.append(f"{path}.{key}: 한쪽에만 있음")
            else:
                diffs += compare_json(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: 길이 {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diffs += compare_json(x, y, f"{path}[{i}]")
    elif not same_number(a, b):
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs


def compare_csv(pa: Path, pb: Path) -> list[str]:
    a, b = pd.read_csv(pa), pd.read_csv(pb)
    diffs = []
    if list(a.columns) != list(b.columns):
        diffs.append(f"열이 다름: 전 {list(a.columns)} / 후 {list(b.columns)}")
    if len(a) != len(b):
        return diffs + [f"행 수 {len(a)} != {len(b)}"]
    for col in [c for c in a.columns if c in b.columns and not is_timing(c)]:
        for i, (x, y) in enumerate(zip(a[col].tolist(), b[col].tolist())):
            if not same_number(x, y) and not (pd.isna(x) and pd.isna(y)):
                diffs.append(f"{col} 행 {i}: {x!r} != {y!r}")
                break  # 열마다 첫 차이만 보여준다
    return diffs


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        return 2
    before, after = Path(sys.argv[1]), Path(sys.argv[2])
    if len(sys.argv) == 4:
        EXTRA_IGNORED.update(c.strip() for c in sys.argv[3].split(",") if c.strip())
    pattern = ("*.csv", "*.csv.gz", "*.json")
    files_a = {p.relative_to(before) for pat in pattern for p in before.rglob(pat)}
    files_b = {p.relative_to(after) for pat in pattern for p in after.rglob(pat)}
    problems = 0
    for rel in sorted(files_a ^ files_b):
        print(f"[한쪽에만 있음] {rel}")
        problems += 1
    for rel in sorted(files_a & files_b):
        pa, pb = before / rel, after / rel
        if rel.suffix == ".json":
            diffs = compare_json(json.loads(pa.read_text(encoding="utf-8")), json.loads(pb.read_text(encoding="utf-8")))
        else:
            diffs = compare_csv(pa, pb)
        print(f"[{'같음' if not diffs else '다름'}] {rel}")
        for d in diffs[:10]:
            print("    ", d)
        problems += bool(diffs)
    print("\n결과:", "모두 같음 (실행 시간 제외)" if problems == 0 else f"{problems}개 파일에서 차이 발견")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
