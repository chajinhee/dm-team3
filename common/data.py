"""HAI 23.05 데이터 확보와 검증.

원 코드: HAI_Project/run.py 11–22줄 (acquire), 92–108줄 (main 의 파일 읽기·검사)
         (최지혜 님 작성, BAZE Mindlogic 생성 코드).
정리: 차진희, Claude Code 지원 (2026-11-27). 검사 조건과 순서는 그대로 두고 풀어 쓰기·주석만 추가했다.
2026-11-28: 필요한 파일만 읽는 load_split 추가 (PR #4 리뷰에서 나온 개선점).
            load_and_check 는 같은 검사 함수(_read_checked)를 쓰도록 바꿨고 동작은 그대로다.

두 가지 읽기 방법
  - load_split(folder, "test1")  : 요청한 파일만 읽는다. 개발 단계에서 test2 를 건드리지 않아야 할 때 쓴다.
                                   기본으로 SHA-256 을 팀 기록(common.config.HAI_SHA256)과 대조한다.
  - load_and_check(folder)       : 기본 5개 파일을 한꺼번에 읽는다 (원본 run.py 와 같은 동작, test2 포함).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from common.config import HAI_COMMIT, HAI_FILES, HAI_SHA256, N_VARIABLES

DOWNLOAD_URL = "https://media.githubusercontent.com/media/icsdataset/hai/{commit}/hai-23.05/{name}"
CHUNK_BYTES = 1048576  # 다운로드·해시 계산 때 한 번에 처리하는 크기 (1 MiB)

# label-test2 는 timestamp 가 분 단위로만 기록돼 중복이 많다 → 중복·1초 연속 검사에서 제외
MINUTE_LABEL_FILES = {"label-test2.csv"}


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


def sha256_of(path: Path) -> str:
    """파일 전체를 조금씩 읽어 SHA-256 을 계산한다 (큰 파일도 메모리를 적게 쓴다)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_checked(folder: Path, name: str, expected_sha256: str | None = None) -> tuple[pd.DataFrame, dict, dict]:
    """파일 하나를 읽고 시각 검사를 한다. (DataFrame, manifest 항목, stats 항목) 을 돌려준다.

    expected_sha256 을 주면 파일 해시가 다를 때 ValueError 로 멈춘다 (다른 버전 파일을 막기 위함).
    검사:
        - timestamp 가 증가 순서
        - 분 단위 레이블 파일(label-test2)이 아니면 timestamp 중복이 없고 1초 간격이 끊기지 않음
    """
    path = folder / name
    digest = sha256_of(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(f"{name}: SHA-256 이 팀 기록과 다르다 (다른 버전 파일일 수 있음)")
    manifest = {"file": name, "bytes": path.stat().st_size, "sha256": digest}

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df.timestamp)
    assert df.timestamp.is_monotonic_increasing

    # 1초 간격이 아닌 곳의 수. 측정 파일은 0 이어야 한다.
    # label-test2 는 분 단위 표기라 이 값이 크게 나오지만 실제 수집 누락이 아니다.
    gaps = int((df.timestamp.diff().dropna().dt.total_seconds() != 1).sum())
    if name not in MINUTE_LABEL_FILES:
        assert df.timestamp.is_unique and gaps == 0

    stats = {
        "file": name,
        "rows": len(df),
        "columns": len(df.columns),
        "missing": int(df.isna().sum().sum()),
        "gaps": gaps,
        "start": str(df.timestamp.iloc[0]),
        "end": str(df.timestamp.iloc[-1]),
    }
    return df, manifest, stats


def _check_labels(n: int, measure: pd.DataFrame, label: pd.DataFrame) -> None:
    """test{n} 측정 파일과 레이블 파일의 대응을 검사한다.

    - test1: 측정·레이블 timestamp 가 초 단위로 모두 같음
    - test2: 측정 시각을 분 단위로 내림한 값이 레이블 시각과 모두 같음 → 행 순서로 대응
      (timestamp 로 merge 하면 분 단위 중복 때문에 틀린다. 분 안에서 초 순서가 보존됐다는 가정은 남는다)
    - 레이블 값은 0 또는 1
    """
    assert len(measure) == len(label)
    if n == 1:
        assert measure.timestamp.equals(label.timestamp)
    else:
        assert measure.timestamp.dt.floor("min").equals(label.timestamp), "Row-aligned minute timestamps mismatch"
    assert set(label.label.unique()) <= {0, 1}


def load_and_check(folder: Path) -> tuple[dict[str, pd.DataFrame], list[dict], list[dict], list[str]]:
    """기본 5개 파일을 한꺼번에 읽고 무결성을 검사한다 (원본 run.py 와 같은 동작).

    주의: test2 까지 읽는다. 개발 단계에서 test2 를 건드리면 안 되면 load_split 을 쓴다.

    반환:
        frames   : {파일 이름: DataFrame}. timestamp 열은 datetime 으로 변환됨
        manifest : 파일별 {file, bytes, sha256}  → results/data_manifest.json
        stats    : 파일별 {file, rows, columns, missing, gaps, start, end} → summary.json 의 data
        cols     : 86개 변수 이름 (timestamp 제외, train1 열 순서)
    """
    manifest = []
    frames = {}
    stats = []
    for name in HAI_FILES:
        df, file_manifest, file_stats = _read_checked(folder, name)
        frames[name] = df
        manifest.append(file_manifest)
        stats.append(file_stats)

    cols = list(frames["hai-train1.csv"].columns[1:])  # 첫 열은 timestamp
    assert len(cols) == N_VARIABLES

    for n in (1, 2):
        measure = frames[f"hai-test{n}.csv"]
        _check_labels(n, measure, frames[f"label-test{n}.csv"])
        assert list(measure.columns[1:]) == cols

    return frames, manifest, stats, cols


@dataclass
class Split:
    """load_split 결과.

    name       : 요청한 이름 (예: "train1", "test1")
    values     : (초 수, 86) 측정값 (float)
    timestamps : 초 단위 시각 (pandas datetime Series)
    labels     : test 파일이면 행 순서에 맞춘 0/1 int 배열, train 파일이면 None
    columns    : 86개 변수 이름
    manifest   : 실제로 읽은 파일의 {file, bytes, sha256} 목록
    stats      : 실제로 읽은 파일의 기술 통계 목록
    """
    name: str
    values: np.ndarray
    timestamps: pd.Series
    labels: np.ndarray | None
    columns: list[str]
    manifest: list[dict]
    stats: list[dict]


def load_split(folder: Path, split: str, columns: list[str] | None = None, check_hash: bool = True) -> Split:
    """필요한 파일만 읽는다. split 은 "train1"~"train4", "test1", "test2" 중 하나.

    - train 이면 hai-{split}.csv 하나, test 면 hai-{split}.csv 와 label-{split}.csv 두 개만 읽는다.
      그래서 load_split(folder, "test1") 은 test2 파일을 열지 않는다 (개발 단계 누출 방지).
    - columns 를 주면 변수 이름·순서가 같은지 확인한다 (보통 train1 의 columns 를 넘긴다).
    - check_hash=True 면 common.config.HAI_SHA256 과 대조한다. 기록이 없는 파일은 check_hash=False 로 읽는다.
    """
    folder = Path(folder)
    measure_name = f"hai-{split}.csv"
    names = [measure_name] + ([f"label-{split}.csv"] if split.startswith("test") else [])

    loaded = {}
    manifest = []
    stats = []
    for name in names:
        expected = None
        if check_hash:
            if name not in HAI_SHA256:
                raise ValueError(f"{name}: 팀 해시 기록이 없다. 확인 후 check_hash=False 로 읽을 것")
            expected = HAI_SHA256[name]
        df, file_manifest, file_stats = _read_checked(folder, name, expected)
        loaded[name] = df
        manifest.append(file_manifest)
        stats.append(file_stats)

    measure = loaded[measure_name]
    cols = list(measure.columns[1:])
    assert len(cols) == N_VARIABLES
    if columns is not None:
        assert cols == list(columns), f"{measure_name}: 변수 이름·순서가 기준과 다르다"

    labels = None
    if split.startswith("test"):
        label = loaded[f"label-{split}.csv"]
        _check_labels(int(split[-1]), measure, label)
        labels = label.label.to_numpy(dtype=int)

    return Split(
        name=split,
        values=measure[cols].to_numpy(float),
        timestamps=measure.timestamp,
        labels=labels,
        columns=cols,
        manifest=manifest,
        stats=stats,
    )
