from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import koreanize_matplotlib
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;R=ROOT/'results';F=ROOT/'figures';F.mkdir(exist_ok=True)
S=json.loads((R/'summary.json').read_text());C=['#1751D0','#E2661E','#0E9E8F','#C08A00'];INK='#1E2433'
plt.rcParams.update({'font.size':10,'text.color':INK,'axes.labelcolor':INK,'axes.titlecolor':INK,'figure.facecolor':'#FDFDFF','axes.facecolor':'#FDFDFF','axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#CDD3E0','grid.color':'#E2E6F0','axes.axisbelow':True})
def save(fig,name):fig.tight_layout();fig.savefig(F/name,dpi=180,bbox_inches='tight');plt.close(fig)
d=pd.read_csv(R/'detection_test2.csv');names=d.model.tolist();ix=np.arange(len(d));fig,ax=plt.subplots(figsize=(8.2,3.2))
for j,(col,label) in enumerate([('precision','Precision'),('recall','Recall'),('f1','F1')]):ax.bar(ix+(j-1)*.23,d[col],width=.23,label=label,color=C[j])
ax.set_xticks(ix,names);ax.set_ylim(0,1);ax.set_ylabel('점수 (0–1)');ax.set_title('test2 탐지 성능: PCA도 낮은 Recall을 해결하지 못함',loc='left');ax.grid(axis='y');ax.legend(ncol=3,frameon=False);save(fig,'01_detection.png')
grid=pd.read_csv(R/'development_grid.csv');fig,ax=plt.subplots(figsize=(8.2,3.1))
for j,model in enumerate(['PCA-0.99','K-means-16','Z-score']):
 a=grid[grid.model==model];ax.plot(a['quantile'],a.f1,marker='o',color=C[j],label=model)
ax.set_xlabel('정상 calibration 점수의 임계 분위수');ax.set_ylabel('test1 F1');ax.set_title('개발 데이터에서의 임계값 민감도 (test2 선택에 미사용)',loc='left');ax.grid();ax.legend(frameon=False);save(fig,'02_sensitivity.png')
p=pd.read_csv(R/'pair_mining.csv');fig,axs=plt.subplots(1,2,figsize=(8.2,3))
for j,alg in enumerate(['Apriori-pairs','PCY']):
 a=p[p.algorithm==alg];axs[0].plot(a.support,a.candidates,marker='o',label=alg,color=C[j]);axs[1].plot(a.support,a.median_ms,marker='o',label=alg,color=C[j])
for ax in axs:ax.set_xlabel('최소 지지도');ax.grid();ax.legend(frameon=False)
axs[0].set_ylabel('실제 집계 후보 수 (개)');axs[1].set_ylabel('5회 실행 중앙값 (ms)');fig.suptitle('PCY: 후보 감소가 실행시간 개선으로 이어지지는 않음');save(fig,'03_pcy.png')
q=pd.read_csv(R/'retrieval_queries.csv');fig,axs=plt.subplots(1,2,figsize=(8.2,3))
axs[0].bar(['MinHash','LSH'],[q.minhash_recall5.mean(),q.lsh_recall5.mean()],color=C[:2]);axs[0].set_ylim(0,1);axs[0].set_ylabel('정확 Top-5 대비 Recall@5')
axs[1].bar(['Exact','MinHash','LSH'],[q.exact_ms.mean(),q.minhash_ms.mean(),q.lsh_ms.mean()],color=C[:3]);axs[1].set_ylabel('질의당 평균 검색시간 (ms)')
for ax in axs:ax.grid(axis='y')
fig.suptitle('검색 속도–재현율 절충: 900개 갤러리 / 200개 질의');save(fig,'04_retrieval.png')
e=pd.read_csv(R/'PCA_events.csv');scores=pd.read_csv(R/'PCA_test2_scores.csv.gz');ys=scores.label.to_numpy();pred=scores.prediction.to_numpy();events=[(1563 if False else 0)]
# predeclared descriptive cases after evaluation; never used for tuning.
chosen=[2,6,32];fig,axs=plt.subplots(3,1,figsize=(8.2,5.1))
start=pd.Timestamp(S['data'][2]['start']);threshold=S['selected']['PCA']['threshold']
for ax,idx in zip(axs,chosen):
 row=e.iloc[idx];a=int((pd.Timestamp(row.start)-start).total_seconds());b=a+int(row.duration_s);lo=max(0,a-120);hi=min(len(scores),b+120);xx=np.arange(lo,hi)-a
 ax.plot(xx,scores.score.iloc[lo:hi],color=C[0],lw=.9,label='PCA score');ax.axhline(threshold,color=C[1],ls='--',lw=.9,label='threshold');ax.axvspan(0,b-a,color='#C2D3F4',label='attack label');ax.set_ylabel('재구성 MSE');ax.set_title(f'구간 {idx+1} | {row.start} | '+('탐지' if row.detected else '미탐'),loc='left',fontsize=9);ax.grid(axis='y')
axs[-1].set_xlabel('공격 시작 기준 경과시간 (초)');axs[0].legend(ncol=3,frameon=False,fontsize=8);save(fig,'05_cases.png')
(F/'versions.json').write_text(json.dumps({'matplotlib':matplotlib.__version__},indent=2))
print('Saved',len(list(F.glob('*.png'))),'figures')
