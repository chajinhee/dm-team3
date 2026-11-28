"""지정 단계에서 필요한 HAI 파일만 읽는 탐지용 데이터 어댑터.

작성 지원: OpenAI Codex. common.config의 고정 버전과 변수 수를 사용한다.
common.data.load_and_check는 test2까지 한꺼번에 읽으므로 개발 단계의 분리를 위해
여기서는 동일한 시각·스키마 검사와 고정 해시 검사를 파일별로 수행한다.
"""
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from common.config import HAI_COMMIT, N_VARIABLES

HASH_FILE = Path(__file__).with_name("data_hashes.json")


def sha256(path):
    """파일 내용을 SHA-256으로 읽는다."""
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def download(folder):
    """탐지 실험에 필요한 공식 파일을 임시 경로로 받아 해시 확인 후 교체한다."""
    import requests

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    hashes = json.loads(HASH_FILE.read_text())
    for name, expected in hashes.items():
        target = folder / name
        if target.exists():
            if sha256(target) != expected:
                raise ValueError(f"기존 파일 해시 불일치: {target}")
            continue
        url = f"https://media.githubusercontent.com/media/icsdataset/hai/{HAI_COMMIT}/hai-23.05/{name}"
        with tempfile.TemporaryDirectory(dir=folder) as temp:
            staged = Path(temp) / name
            with requests.get(url, stream=True, timeout=180) as response:
                response.raise_for_status()
                with staged.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 1024):
                        handle.write(chunk)
            if sha256(staged) != expected:
                raise ValueError(f"다운로드 파일 해시 불일치: {name}")
            staged.replace(target)


class Dataset:
    """폴더와 센서 열 순서를 고정하고 각 파일의 무결성을 확인한다."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.hashes = json.loads(HASH_FILE.read_text())
        self.manifest = {}
        # 열 이름만 읽는다. 모델 적합에 쓰는 값은 read에서 검증한 후 받는다.
        self.columns = pd.read_csv(self.folder / "hai-train1.csv", nrows=0).columns[1:].tolist()
        if len(self.columns) != N_VARIABLES:
            raise ValueError("예상하지 못한 센서 변수 수")

    def _frame(self, name):
        """실제로 읽은 파일만 manifest에 남기고 고정 해시를 검사한다."""
        path = self.folder / name
        digest = sha256(path)
        if digest != self.hashes[name]:
            raise ValueError(f"고정 HAI 파일 해시 불일치: {name}")
        self.manifest[name] = digest
        return pd.read_csv(path)

    def read(self, split):
        """센서값, 초 단위 시각, 행 대응 레이블을 반환한다. 정상 파일은 모두 0이다."""
        frame = self._frame(f"hai-{split}.csv")
        if frame.columns.tolist() != ["timestamp", *self.columns]:
            raise ValueError(f"센서 열 순서 불일치: {split}")
        times = pd.to_datetime(frame.timestamp)
        if not times.diff().iloc[1:].eq(pd.Timedelta(seconds=1)).all():
            raise ValueError(f"초 단위 시각 연속성 오류: {split}")
        values = frame[self.columns].to_numpy(float)
        if not np.isfinite(values).all():
            raise ValueError(f"유한하지 않은 센서값: {split}")
        if split.startswith("train"):
            return values, times, np.zeros(len(values), dtype=bool)
        labels = self._frame(f"label-{split}.csv")
        expected = times if split == "test1" else times.dt.floor("min")
        if not expected.equals(pd.to_datetime(labels.timestamp)):
            raise ValueError(f"측정과 레이블 시각 대응 오류: {split}")
        if not labels.label.isin([0, 1]).all():
            raise ValueError("0/1 이외 레이블")
        return values, times, labels.label.to_numpy(bool)
