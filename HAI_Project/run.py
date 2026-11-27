"""HAI 23.05 reproducible experiments. No label enters detector input."""
import argparse, hashlib, json, time, itertools, sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

SEED=331
COMMIT='2a814cebc9a66b06c9e5cd545e2d72e65d383737'
FILES=['hai-train1.csv','hai-test1.csv','hai-test2.csv','label-test1.csv','label-test2.csv']
def acquire(folder):
 import requests
 folder.mkdir(parents=True,exist_ok=True)
 for name in FILES:
  p=folder/name
  if not p.exists():
   u=f'https://media.githubusercontent.com/media/icsdataset/hai/{COMMIT}/hai-23.05/{name}'
   with requests.get(u,stream=True,timeout=180) as r:
    r.raise_for_status()
    with p.open('wb') as f:
     for b in r.iter_content(1048576): f.write(b)
  assert not p.read_bytes()[:80].startswith(b'version https://git-lfs'), 'LFS pointer, not data'

def intervals(y):
 a=np.asarray(y,dtype=bool);d=np.diff(np.r_[False,a,False].astype(int))
 return list(zip(np.where(d==1)[0],np.where(d==-1)[0]))
def metrics(y,p):
 y=np.asarray(y,dtype=bool);p=np.asarray(p,dtype=bool)
 tp=int((y&p).sum());fp=int((~y&p).sum());fn=int((y&~p).sum());tn=int((~y&~p).sum())
 precision=tp/max(tp+fp,1);recall=tp/max(tp+fn,1)
 delays=[int(np.flatnonzero(p[a:b])[0]) for a,b in intervals(y) if p[a:b].any()]
 false_runs=len(intervals(p&~y))
 return dict(precision=precision,recall=recall,f1=2*precision*recall/max(precision+recall,1e-15),accuracy=(tp+tn)/len(y),tp=tp,fp=fp,fn=fn,tn=tn,event_recall=len(delays)/max(len(intervals(y)),1),detected_events=len(delays),events=len(intervals(y)),delay_median_s=float(np.median(delays)) if delays else None,false_alarms_per_normal_hour=false_runs/max((~y).sum()/3600,1e-15),false_positive_seconds_per_normal_hour=fp/max((~y).sum()/3600,1e-15))
def sqdist(x,c):
 return np.maximum((x*x).sum(1)[:,None]+(c*c).sum(1)[None,:]-2*x@c.T,0)
def kfit(x,k):
 rng=np.random.default_rng(SEED);x=x[rng.choice(len(x),min(30000,len(x)),replace=False)]
 c=x[rng.choice(len(x),k,replace=False)].copy()
 for _ in range(40):
  lab=sqdist(x,c).argmin(1);new=np.array([x[lab==j].mean(0) if (lab==j).any() else c[j] for j in range(k)])
  if np.max(np.abs(new-c))<1e-5:break
  c=new
 return c

def transactions(z):
 # Non-overlapping 60-second windows; signed mean z, max 8 items.
 out=[]
 for a in range(0,len(z)-59,60):
  m=z[a:a+60].mean(0);idx=np.argsort(-np.abs(m),kind='stable')[:8]
  out.append(frozenset(int(2*j+(m[j]>0)) for j in idx if abs(m[j])>=1.5))
 return out

def mine_pairs(tx,support=.02,buckets=1024,pcy=False):
 # Apriori k<=2, PCY two-pass hashed bucket pruning, exact verification.
 threshold=int(np.ceil(support*len(tx)));single=Counter(i for t in tx for i in t)
 frequent={i for i,n in single.items() if n>=threshold};bc=np.zeros(buckets,dtype=int)
 if pcy:
  for t in tx:
   for a,b in itertools.combinations(sorted(t),2):bc[(a*1009+b*9176)%buckets]+=1
 candidates=set();counts=Counter()
 for t in tx:
  for a,b in itertools.combinations(sorted(t&frequent),2):
   if not pcy or bc[(a*1009+b*9176)%buckets]>=threshold:
    candidates.add((a,b));counts[(a,b)]+=1
 return {k:v for k,v in counts.items() if v>=threshold},len(candidates),len(frequent)

def signature(tx,a,b):
 prime=2147483647
 return np.array([np.min((a[:,None]*np.array(sorted(t),dtype=np.int64)[None,:]+b[:,None])%prime,axis=1) if t else np.full(len(a),prime,dtype=np.int64) for t in tx])
def jacc(a,b):
 return len(a&b)/len(a|b) if a|b else 1.
def topk(scores,k=5):return np.lexsort((np.arange(len(scores)),-np.asarray(scores)))[:k]
def retrieval(gallery,queries):
 rng=np.random.default_rng(SEED);a=rng.integers(1,2147483647,64);b=rng.integers(0,2147483647,64)
 t=time.perf_counter();gs=signature(gallery,a,b);index=defaultdict(set)
 for i,s in enumerate(gs):
  for band in range(16):index[(band,tuple(s[4*band:4*band+4]))].add(i)
 build=time.perf_counter()-t
 rows=[]
 for qi,q in queries:
  t=time.perf_counter();exact=np.array([jacc(q,g) for g in gallery]);truth=set(topk(exact));te=time.perf_counter()-t
  t=time.perf_counter();qs=signature([q],a,b)[0];approx=(gs==qs).mean(1);pred=set(topk(approx));tm=time.perf_counter()-t
  t=time.perf_counter();qs2=signature([q],a,b)[0];cand=set()
  for band in range(16):cand.update(index.get((band,tuple(qs2[4*band:4*band+4])),set()))
  ranked=sorted(cand,key=lambda i:(-jacc(q,gallery[i]),i))[:5];tl=time.perf_counter()-t
  rows.append(dict(query_window=qi,minhash_recall5=len(pred&truth)/5,lsh_recall5=len(set(ranked)&truth)/5,exact_ms=te*1000,minhash_ms=tm*1000,lsh_ms=tl*1000,candidates=len(cand),best_exact=float(exact.max()),best_lsh=float(exact[ranked[0]]) if ranked else None,top5_exact=','.join(map(str,sorted(truth))),top5_lsh=','.join(map(str,ranked))))
 return pd.DataFrame(rows),build

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data',default='data');ap.add_argument('--out',default='results');ap.add_argument('--download',action='store_true');args=ap.parse_args()
 data=Path(args.data);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 if args.download:acquire(data)
 started=time.perf_counter();manifest=[];frames={};stats=[]
 for n in FILES:
  p=data/n;manifest.append(dict(file=n,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  df=pd.read_csv(p);df['timestamp']=pd.to_datetime(df.timestamp)
  assert df.timestamp.is_monotonic_increasing
  gaps=int((df.timestamp.diff().dropna().dt.total_seconds()!=1).sum())
  if n!='label-test2.csv':
   assert df.timestamp.is_unique and gaps==0
  frames[n]=df;stats.append(dict(file=n,rows=len(df),columns=len(df.columns),missing=int(df.isna().sum().sum()),gaps=gaps,start=str(df.timestamp.iloc[0]),end=str(df.timestamp.iloc[-1])))
 train=frames['hai-train1.csv'];cols=list(train.columns[1:]);assert len(cols)==86
 for n in (1,2):
  x=frames[f'hai-test{n}.csv'];l=frames[f'label-test{n}.csv']
  assert len(x)==len(l)
  if n==1: assert x.timestamp.equals(l.timestamp)
  else: assert x.timestamp.dt.floor('min').equals(l.timestamp), 'Row-aligned minute timestamps mismatch'
  assert set(l.label.unique())<={0,1};assert list(x.columns[1:])==cols
 x=train[cols].to_numpy(float);cut=int(len(x)*.6);fit=x[:cut];med=np.nanmedian(fit,axis=0)
 # No missing values in observed inputs. Fill future missing values with fit medians only.
 fit=np.where(np.isfinite(fit),fit,med);mu=fit.mean(0);sd=fit.std(0);constant=sd<1e-10;sd[constant]=1
 def transform(arr):return (np.where(np.isfinite(arr),arr,med)-mu)/sd
 z=transform(x);cal=z[cut:];zf=z[:cut]
 dev=transform(frames['hai-test1.csv'][cols].to_numpy(float));test=transform(frames['hai-test2.csv'][cols].to_numpy(float))
 yd=frames['label-test1.csv'].label.to_numpy(int);yt=frames['label-test2.csv'].label.to_numpy(int)
 pd.DataFrame({'feature':cols,'fit_mean':mu,'fit_std_used':sd,'constant_in_fit':constant,'fit_median':med}).to_csv(out/'features.csv',index=False)
 # Models trained only on first 60% train1. Normal threshold calibration on last 40%.
 ev,evec=np.linalg.eigh(np.cov(zf,rowvar=False));order=np.argsort(ev)[::-1];ev=ev[order];evec=evec[:,order]
 model_scores={};grid=[];final=[];chosen={}
 model_scores['Z-score']=(np.max(abs(cal),1),np.max(abs(dev),1),np.max(abs(test),1),{'kind':'max_abs_z'})
 for ratio in [.90,.95,.99]:
  r=int(np.searchsorted(np.cumsum(ev)/ev.sum(),ratio)+1);v=evec[:,:r]
  def score(a):return np.maximum((a*a).sum(1)-((a@v)**2).sum(1),0)/a.shape[1]
  model_scores[f'PCA-{ratio}']=(score(cal),score(dev),score(test),{'variance':ratio,'rank':r})
 for k in [4,8,16]:
  c=kfit(zf,k)
  def score(a):return np.concatenate([sqdist(a[i:i+10000],c).min(1) for i in range(0,len(a),10000)])
  model_scores[f'K-means-{k}']=(score(cal),score(dev),score(test),{'k':k})
 for name,(sc,ds,ts,params) in model_scores.items():
  for q in [.95,.975,.99,.995,.999]:
   th=float(np.quantile(sc,q));m=metrics(yd,ds>th)
   grid.append(dict(model=name,quantile=q,threshold=th,**params,**m))
 for family,prefix in [('Z-score','Z-score'),('PCA','PCA-'),('K-means','K-means-')]:
  candidates=[r for r in grid if r['model'].startswith(prefix)]
  best=sorted(candidates,key=lambda r:(-r['f1'],r['model'],r['quantile']))[0];name=best['model'];th=best['threshold']
  chosen[family]=best;sc,ds,ts,params=model_scores[name]
  final.append(dict(model=family,setting=name,threshold=th,**metrics(yt,ts>th)))
  # timeline summary at 60-sec bins retains maximum score and any attack.
  pd.DataFrame({'second':np.arange(len(yt)),'score':ts,'prediction':(ts>th).astype(int),'label':yt}).to_csv(out/(family.replace('-','')+'_test2_scores.csv.gz'),index=False,compression='gzip')
  events=[]
  for a,b in intervals(yt):
   hits=np.flatnonzero(ts[a:b]>th);events.append(dict(start=str(frames['hai-test2.csv'].timestamp.iloc[a]),end=str(frames['hai-test2.csv'].timestamp.iloc[b-1]),duration_s=b-a,detected=bool(len(hits)),delay_s=int(hits[0]) if len(hits) else None))
  pd.DataFrame(events).to_csv(out/(family.replace('-','')+'_events.csv'),index=False)
 final.append(dict(model='Always normal',setting='constant zero',threshold=None,**metrics(yt,np.zeros_like(yt))))
 pd.DataFrame(grid).to_csv(out/'development_grid.csv',index=False);pd.DataFrame(final).to_csv(out/'detection_test2.csv',index=False)
 # Fit-state discretization only, no test2 tuning; patterns mined on development.
 td=transactions(dev);tt=transactions(test);wd=np.array([yd[i:i+60].max() for i in range(0,len(yd)-59,60)]);wt=np.array([yt[i:i+60].max() for i in range(0,len(yt)-59,60)])
 timings=[];apairs=None
 for support in [.01,.02,.05]:
  for pcy in [False,True]:
   times=[]
   for rep in range(5):
    t=time.perf_counter();pairs,nc,nf=mine_pairs(td,support,pcy=pcy);times.append(time.perf_counter()-t)
   timings.append(dict(algorithm='PCY' if pcy else 'Apriori-pairs',support=support,median_ms=np.median(times)*1000,candidates=nc,frequent_pairs=len(pairs),frequent_items=nf))
   if not pcy:apairs=pairs
   else:assert pairs==apairs
 pd.DataFrame(timings).to_csv(out/'pair_mining.csv',index=False)
 pairs,_,_=mine_pairs(td,.02);rules=[]
 for pair,count in pairs.items():
  mask=np.array([set(pair)<=t for t in td]);conf=float(wd[mask].mean());lift=conf/max(wd.mean(),1e-15)
  tm=np.array([set(pair)<=t for t in tt]);conf_t=float(wt[tm].mean()) if tm.any() else None
  itemnames=[cols[i//2]+('=HIGH' if i%2 else '=LOW') for i in pair]
  rules.append(dict(items=' & '.join(itemnames),dev_count=int(mask.sum()),dev_support=float(mask.mean()),dev_confidence=conf,dev_lift=lift,test_count=int(tm.sum()),test_support=float(tm.mean()),test_confidence=conf_t,test_lift=conf_t/max(wt.mean(),1e-15) if conf_t is not None else None))
 rules=sorted(rules,key=lambda r:(-r['dev_lift'],-r['dev_count'],r['items']))[:10]
 pd.DataFrame(rules).to_csv(out/'frozen_rules.csv',index=False)
 # gallery dev=test1, queries test2. Nonoverlap, chronological separation.
 eligible=[i for i,t in enumerate(tt) if t];rng=np.random.default_rng(SEED);qi=sorted(rng.choice(eligible,min(200,len(eligible)),replace=False).tolist())
 rr,build=retrieval(td,[(i,tt[i]) for i in qi]);rr.to_csv(out/'retrieval_queries.csv',index=False)
 desc=[]
 for name,lab in [('test1',yd),('test2',yt)]:desc.append(dict(split=name,rows=len(lab),attack_seconds=int(lab.sum()),attack_rate=float(lab.mean()),attack_intervals=len(intervals(lab))))
 summary=dict(seed=SEED,source_commit=COMMIT,access_date='2026-11-16',fit_rows=cut,calibration_rows=len(x)-cut,constant_fit_features=int(constant.sum()),data=stats,labels=desc,selected=chosen,detection=final,patterns=timings,rule_count=len(rules),window_seconds=60,dev_windows=len(td),test_windows=len(tt),empty_dev_windows=sum(not t for t in td),empty_test_windows=sum(not t for t in tt),retrieval={**rr[['minhash_recall5','lsh_recall5','exact_ms','minhash_ms','lsh_ms','candidates']].mean().to_dict(),'queries':len(rr),'gallery':len(td),'index_build_s':build},runtime_s=time.perf_counter()-started,python=sys.version.split()[0],numpy=np.__version__,pandas=pd.__version__)
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(out/'data_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
