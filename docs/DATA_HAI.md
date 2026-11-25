# HAI 23.05 데이터 확보 기록 (보안A 실험용)

- 원제공자: H.-K. Shin, W. Lee, S. Choi, J.-H. Yun, B.-G. Min, *HAI security datasets*. https://github.com/icsdataset/hai
- 버전: HAI 23.05, 원본 저장소 고정 commit `2a814cebc9a66b06c9e5cd545e2d72e65d383737` (팀원 실험과 동일)
- 확보 방법: 아래 주소에서 HTTP 다운로드 (curl), 2026-11-25
  `https://media.githubusercontent.com/media/icsdataset/hai/<commit>/hai-23.05/<파일명>`
- 저장 위치: `data/` (`.gitignore`로 저장소에서 제외. 재배포하지 않음)

| 파일 | bytes | SHA-256 |
|---|---:|---|
| hai-train1.csv | 162,418,984 | `53007b0ba604fbf338e7ac2e08cd81d874b5d1388f3aecb213ddcba5bf2bec4a` |
| hai-test1.csv | 31,255,559 | `78c7f1d4de1f2ab9ccc2f8c719f80f831033543adb0c81d0d78f84f40838d4be` |
| hai-test2.csv | 132,946,575 | `b2b8dd295aefd87e39260fe43cb4c73ee86d6264b0ac4b0761e7efb0c2b545c3` |
| label-test1.csv | 1,242,017 | `eaf69edb9c5834bc393afd7bf658b5e408d34fd7bfc3261f80516765fb818fbc` |
| label-test2.csv | 4,500,018 | `8090c44981176e39b0f01a7126a80248ac0b93355c00f9db4d4e2f2106452b92` |

다섯 파일의 SHA-256·크기가 팀원 기록(`results/data_manifest.json`)과 모두 일치함을 확인했다.

- 확인한 구조: test1 54,000행 × (timestamp + 86 변수), label-test1 54,000행 (timestamp, label). test1 공격 비율 5.52%.
- 실행 환경: Python 3.14.4, numpy 2.5.5, pandas 3.1.1
  (팀원 환경 numpy 2.3.5 / pandas 2.2.3 은 Python 3.14용 배포판이 없어 최신판 사용. 버전 차이를 보고서에 명시할 것.)

## 다운로드 재현 (PowerShell)
```
$c = "2a814cebc9a66b06c9e5cd545e2d72e65d383737"
foreach ($f in "hai-train1.csv","hai-test1.csv","hai-test2.csv","label-test1.csv","label-test2.csv") {
  curl.exe -sSfL -o "data\$f" "https://media.githubusercontent.com/media/icsdataset/hai/$c/hai-23.05/$f"
}
Get-FileHash data\*.csv -Algorithm SHA256
```
