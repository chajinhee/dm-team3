"""HAI 23.05 데이터 확보와 검증.

원 코드: HAI_Project/run.py 11–22줄 (acquire), 92–108줄 (main 의 파일 읽기·검사)
         (최지혜 님 작성, BAZE Mindlogic 생성 코드).
정리: 차진희, Claude Code 지원 (2026-11-27). 검사 조건과 순서는 그대로 두고 풀어 쓰기·주석만 추가했다.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from common.config import HAI_COMMIT, HAI_FILES, N_VARIABLES

DOWNLOAD_URL = "https://media.githubusercontent.com/media/icsdataset/hai/{commit}/hai-23.05/{name}"
CHUNK_BYTES = 1048576  # 다운로드할 때 한 번에 쓰는 크기 (1 MiB)


def download_hai(folder: Path) -> None:
    """고정 commit 의 HAI 23.05 파일을 folder 에 받는다. 이미 있는 파일은 건너뛴다.

    원본 저장소는 Git LFS 를 쓰므로, 일반 raw 주소로 받으면 실제 데이터 대신 짧은 "포인터 파일" 이 온다.
    그래서 media.githubusercontent.com 주소를 쓰고, 받은 파일이 포인터가 아닌지 확인한다.
    """
    import requests  # 다운로드할 때만 필요하므로 여기서 불러온다

    folder.mkdir(parents=True, exist_ok=True)
    for name in HAI_FILES:
        path = folder / name
        if not path.exists():
            url = DOWNLOAD_URL.format(commit=HAI_COMMIT, name=name)
            with requests.get(url, stream=True, timeout=180) as response:
                response.raise_for_status()
                with path.open("wb") as f:
                    for chunk in response.iter_content(CHUNK_BYTES):
                        f.write(chunk)
        first_bytes = path.read_bytes()[:80]
        assert not first_bytes.startswith(b"version https://git-lfs"), "LFS pointer, not data"


def load_and_check(folder: Path) -> tuple[dict[str, pd.DataFrame], list[dict], list[dict], list[str]]:
    """다섯 파일을 읽고 무결성을 검사한다.

    반환:
        frames   : {파일 이름: DataFrame}. timestamp 열은 datetime 으로 변환됨
        manifest : 파일별 {file, bytes, sha256}  → results/data_manifest.json
        stats    : 파일별 {file, rows, columns, missing, gaps, start, end} → summary.json 의 data
        cols     : 86개 변수 이름 (timestamp 제외, train1 열 순서)

    검사 (하나라도 어기면 AssertionError 로 멈춤):
        - 모든 파일의 timestamp 가 증가 순서
        - 측정 파일과 label-test1 은 timestamp 중복이 없고 1초 간격이 끊기지 않음
          (label-test2 는 분 단위로만 기록돼 중복이 많으므로 이 검사에서 제외)
        - 변수가 정확히 86개
        - 측정 파일과 레이블 파일의 행 수가 같음
        - test1: 측정·레이블 timestamp 가 초 단위로 모두 같음
        - test2: 측정 시각을 분 단위로 내림한 값이 레이블 시각과 모두 같음 → 행 순서로 대응
        - 레이블 값은 0 또는 1, test 파일의 변수 이름·순서가 train1 과 같음
    """
    manifest = []
    frames = {}
    stats = []
    for name in HAI_FILES:
        path = folder / name
        # 원자료가 팀 기록과 같은 파일인지 확인할 수 있도록 크기와 SHA-256 을 남긴다
        manifest.append({
            "file": name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df.timestamp)
        assert df.timestamp.is_monotonic_increasing

        # 1초 간격이 아닌 곳의 수. 측정 파일은 0 이어야 한다.
        # label-test2 는 분 단위 표기라 이 값이 크게 나오지만 실제 수집 누락이 아니다.
        gaps = int((df.timestamp.diff().dropna().dt.total_seconds() != 1).sum())
        if name != "label-test2.csv":
            assert df.timestamp.is_unique and gaps == 0

        frames[name] = df
        stats.append({
            "file": name,
            "rows": len(df),
            "columns": len(df.columns),
            "missing": int(df.isna().sum().sum()),
            "gaps": gaps,
            "start": str(df.timestamp.iloc[0]),
            "end": str(df.timestamp.iloc[-1]),
        })

    train = frames["hai-train1.csv"]
    cols = list(train.columns[1:])  # 첫 열은 timestamp
    assert len(cols) == N_VARIABLES

    for n in (1, 2):
        measure = frames[f"hai-test{n}.csv"]
        label = frames[f"label-test{n}.csv"]
        assert len(measure) == len(label)
        if n == 1:
            assert measure.timestamp.equals(label.timestamp)
        else:
            # timestamp 로 merge 하면 안 된다 (분 단위 중복). 분 단위가 모든 행에서 같을 때만 행 순서 대응을 쓴다.
            # 분 안에서 초 단위 순서가 보존됐다는 가정은 남는다 (보고서 한계에 기재).
            assert measure.timestamp.dt.floor("min").equals(label.timestamp), "Row-aligned minute timestamps mismatch"
        assert set(label.label.unique()) <= {0, 1}
        assert list(measure.columns[1:]) == cols

    return frames, manifest, stats, cols
