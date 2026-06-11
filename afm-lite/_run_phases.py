#!/usr/bin/env python3
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2'), exist_ok=True)

import torch, numpy as np
from ablation_models import get_model, compute_loss
from validation_data import get_mnist, get_fashion_mnist, get_synthetic, get_split_mnist, get_permuted_mnist
from scipy import stats
import torch.nn as nn
from ablation_models import AFMWithQR, AFMWithRIB, BaselineLTask
from stiefel import stiefel_project_qr

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2')
BS = 1024

def save(name, data):
    def conv(obj):
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, dict): return {k: conv(v) for k, v in obj.items()}
        if isinstance(obj, list): return [conv(v) for v in obj]
        if isinstance(obj, torch.Tensor): return obj.detach().cpu().numpy().tolist()
        return obj
    with open(os.path.join(DIR, f'{name}.json'), 'w') as f:
        json.dump(conv(data), f, indent=2)

def te(config, beta, train_l, test_l, seed, epochs=8):
    torch.manual_seed(seed); np.random.seed(seed)
    m=get_model(config); opt=torch.optim.Adam(m.parameters(),lr=1e-3); best=0
    for ep in range(epochs):
        m.train()
        for X,y in train_l:
            opt.zero_grad()
            if config in ['afm_qr','afm_rib']: o,_,mu,lv,kl=m(X); loss=compute_loss(m,config,o,y,mu,lv,kl,beta)
            else: o,_,mu,lv=m(X); loss=compute_loss(m,config,o,y,mu,lv,None,beta)
            loss.backward(); opt.step()
        m.eval(); c,t=0,0
        with torch.no_grad():
            for X,y in test_l:
                if config in ['afm_qr','afm_rib']: o,_,_,_,_=m(X)
                else: o,_,_,_=m(X)
                c+=(o.argmax(1)==y).sum().item(); t+=y.size(0)
        best=max(best,c/t)
    return best

print("Starting remaining phases...", flush=True)

# Phase 3: Ablation (5 seeds, MNIST)
print("\nPhase 3: Ablation", flush=True)
train_l, test_l, _, _ = get_mnist(batch_size=BS)
p3 = {}
for config, beta in [('baseline_task',0.0),('baseline_vae',1e-3),('afm_no_qr',0.0),('afm_no_qr',1e-3),('afm_qr',0.0),('afm_rib',1e-3)]:
    key=f'{config}_b{beta}' if beta>0 else config
    accs=[te(config,beta,train_l,test_l,si*42) for si in range(5)]
    p3[key]={'accs':accs,'mean':float(np.mean(accs))}
    print(f"  {key}: {np.mean(accs):.4f}", flush=True)
save('phase3', p3)

# Phase 4: KL Collapse
print("\nPhase 4: KL Collapse", flush=True)
p4 = {}
betas = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]
for config in ['baseline_task', 'afm_rib']:
    for beta in betas:
        acc = te(config, beta, train_l, test_l, 42)
        p4[f"{config}_b{beta}"] = {'config': config, 'beta': beta, 'acc': float(acc)}
        st = 'COLLAPSED' if acc < 0.5 else ''
        print(f"  {config}_b{beta}: {acc:.4f} {st}", flush=True)

# Latent norms
for config, beta in [('baseline_task',1e-2),('afm_rib',1e-2)]:
    torch.manual_seed(42); np.random.seed(42)
    m=get_model(config); opt=torch.optim.Adam(m.parameters(),lr=1e-3); norms=[]
    for ep in range(8):
        m.train()
        for X,y in train_l:
            opt.zero_grad()
            if config=='afm_rib': o,_,mu,lv,kl=m(X); loss=compute_loss(m,config,o,y,mu,lv,kl,beta)
            else: o,_,mu,lv=m(X); loss=compute_loss(m,config,o,y,mu,lv,None,beta)
            loss.backward(); opt.step()
        m.eval()
        with torch.no_grad():
            Xs=next(iter(test_l))[0]
            if config=='afm_rib': _,_,mu,lv,_=m(Xs); S,_=m.stiefel(mu,lv); norms.append(float(S.norm().item()))
            else: _,_,mu,lv=m(Xs); norms.append(float(mu.norm().item()))
    p4[f'{config}_norms_b{beta}']={'norms':norms}
    print(f"  {config} norms: {norms[0]:.2f}→{norms[-1]:.2f}", flush=True)

# QR test
Q=stiefel_project_qr(torch.randn(1,32,4)*1e-10)
p4['qr_test']={'norm':float(Q.norm().item()),'expected':float(np.sqrt(128))}
print(f"  QR(eps) norm: {Q.norm().item():.4f} (expected≈11.31)", flush=True)
save('phase4', p4)

# Phase 5: Continual Learning
print("\nPhase 5: Continual Learning", flush=True)
p5 = {}
try:
    split_tasks = get_split_mnist(batch_size=BS)
    tc = [nc for _,_,_,nc in split_tasks]
    class MTLB(BaselineLTask):
        def __init__(self): super().__init__(784,256,128,2); self.heads=nn.ModuleList([nn.Sequential(nn.Linear(128,64),nn.ReLU(),nn.Linear(64,2)) for _ in range(5)])
        def forward(self,x,tid=0): h=self.encoder(x); mu,lv=self.fc_mu(h),self.fc_logvar(h); z=mu+(torch.exp(0.5*lv)*torch.randn_like(mu) if self.training else 0); return self.heads[tid](z),mu,lv
    class MTLA(AFMWithRIB):
        def __init__(self): super().__init__(784,256,32,4,2); self.heads=nn.ModuleList([nn.Sequential(nn.Linear(128,64),nn.ReLU(),nn.Linear(64,2)) for _ in range(5)])
        def forward(self,x,tid=0): h=self.encoder(x); mu,lv=self.fc_mu(h),self.fc_logvar(h); S,kl=self.stiefel(mu,lv); return self.heads[tid](S.reshape(S.shape[0],-1)),mu,lv,kl
    
    for name,fn,beta in [('baseline',MTLB,0.0),('afm_rib',MTLA,1e-3)]:
        torch.manual_seed(42); model=fn(); nt=len(split_tasks); am=np.zeros((nt,nt))
        for tid in range(nt):
            tl,tel,_,_=split_tasks[tid]; opt=torch.optim.Adam(model.parameters(),lr=1e-3)
            for ep in range(8):
                model.train()
                for X,y in tl:
                    opt.zero_grad()
                    if name=='baseline': o,mu,lv=model(X,tid); ce=nn.functional.cross_entropy(o,y); loss=ce+(beta*(-0.5*torch.sum(1+lv-mu.pow(2)-lv.exp(),dim=-1).mean()) if beta>0 else 0)
                    else: o,mu,lv,kl=model(X,tid); ce=nn.functional.cross_entropy(o,y); loss=ce+(beta*kl if kl is not None else 0)
                    loss.backward(); opt.step()
            model.eval()
            for eid in range(nt):
                _,el,_,_=split_tasks[eid]; c,t=0,0
                with torch.no_grad():
                    for X,y in el:
                        if name=='baseline': o,_,_=model(X,eid)
                        else: o,_,_,_=model(X,eid)
                        c+=(o.argmax(1)==y).sum().item(); t+=y.size(0)
                am[tid,eid]=c/t
        fg=[am[i,i]-am[nt-1,i] for i in range(nt-1)]
        p5[f'split_{name}']={'acc_matrix':am.tolist(),'avg_forgetting':float(np.mean(fg)),'avg_acc':float(np.mean([am[-1,i] for i in range(nt)]))}
        print(f"  split_{name}: fg={np.mean(fg):.4f} avg={np.mean([am[-1,i] for i in range(nt)]):.4f}", flush=True)
except Exception as e:
    print(f"  Split-MNIST FAILED: {e}", flush=True)
    p5['split_error'] = str(e)

try:
    perm_tasks = get_permuted_mnist(n_tasks=5, batch_size=BS)
    for name,Model,beta in [('baseline',lambda:BaselineLTask(784,256,128,10),0.0),('afm_rib',lambda:AFMWithQR(784,256,32,4,10),1e-3)]:
        torch.manual_seed(42); model=Model(); nt=len(perm_tasks); am=np.zeros((nt,nt))
        for tid in range(nt):
            tl,tel,_,_=perm_tasks[tid]; opt=torch.optim.Adam(model.parameters(),lr=1e-3)
            for ep in range(8):
                model.train()
                for X,y in tl:
                    opt.zero_grad()
                    if name=='baseline': o,_,mu,lv=model(X); ce=nn.functional.cross_entropy(o,y); loss=ce
                    else: o,_,mu,lv,kl=model(X); ce=nn.functional.cross_entropy(o,y); loss=ce+(beta*kl if kl is not None else 0)
                    loss.backward(); opt.step()
            model.eval()
            for eid in range(nt):
                _,el,_,_=perm_tasks[eid]; c,t=0,0
                with torch.no_grad():
                    for X,y in el:
                        if name=='baseline': o,_,_,_=model(X)
                        else: o,_,_,_,_=model(X)
                        c+=(o.argmax(1)==y).sum().item(); t+=y.size(0)
                am[tid,eid]=c/t
        fg=[am[i,i]-am[nt-1,i] for i in range(nt-1)]
        p5[f'permuted_{name}']={'acc_matrix':am.tolist(),'avg_forgetting':float(np.mean(fg)),'avg_acc':float(np.mean([am[-1,i] for i in range(nt)]))}
        print(f"  permuted_{name}: fg={np.mean(fg):.4f} avg={np.mean([am[-1,i] for i in range(nt)]):.4f}", flush=True)
except Exception as e:
    print(f"  Permuted-MNIST FAILED: {e}", flush=True)
save('phase5', p5)

# Phase 6: Representation Analysis
print("\nPhase 6: Representation", flush=True)
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
train_l, test_l, _, _ = get_mnist(batch_size=BS)
p6 = {}
for config in ['baseline_task','afm_qr','afm_rib']:
    beta = 1e-3 if config=='afm_rib' else 0.0
    torch.manual_seed(42); m=get_model(config); opt=torch.optim.Adam(m.parameters(),lr=1e-3)
    for ep in range(8):
        m.train()
        for X,y in train_l:
            opt.zero_grad()
            if config in ['afm_qr','afm_rib']: o,_,mu,lv,kl=m(X); loss=compute_loss(m,config,o,y,mu,lv,kl,beta)
            else: o,_,mu,lv=m(X); loss=compute_loss(m,config,o,y)
            loss.backward(); opt.step()
    m.eval(); lats,labs=[],[]
    with torch.no_grad():
        for i,(X,y) in enumerate(test_l):
            if i>=10: break
            if config in ['afm_qr','afm_rib']: _,_,mu,lv,_=m(X); S,_=m.stiefel(mu,lv); lats.append(S.reshape(S.shape[0],-1).numpy())
            else: _,_,mu,lv=m(X); lats.append(mu.numpy())
            labs.append(y.numpy())
    lat=np.concatenate(lats); lab=np.concatenate(labs)
    pca=PCA(n_components=min(10,lat.shape[1])).fit(lat); ev=pca.explained_variance_ratio_
    sil=silhouette_score(lat,lab,sample_size=min(5000,len(lab)))
    p6[config]={'pca_ev':ev.tolist(),'pca_cum':float(ev.sum()),'sil':float(sil)}
    print(f"  {config}: sil={sil:.4f}", flush=True)
save('phase6', p6)

# Phase 7: Failure Analysis
print("\nPhase 7: Failure Analysis", flush=True)
p7 = {'failures':[], 'warnings':[]}

# Load all results
with open(os.path.join(DIR,'phase1.json')) as f: p1=json.load(f)
with open(os.path.join(DIR,'phase2.json')) as f: p2=json.load(f)

if p1.get('paired',{}).get('sig',False):
    p7['warnings'].append(f"P1: Significant p={p1['paired']['p']:.6f}")
else:
    p7['failures'].append(f"P1: NOT significant p={p1.get('paired',{}).get('p','N/A')}")

for ds,dd in p2.items():
    if isinstance(dd,dict) and 'error' in dd:
        p7['failures'].append(f"P2: {ds} failed")
    elif isinstance(dd,dict):
        bt=dd.get('baseline_task',{}).get('mean',0); ar=dd.get('afm_rib',{}).get('mean',0)
        if ar<bt: p7['failures'].append(f"P2: AFM worse on {ds} ({ar:.4f} vs {bt:.4f})")

# Check ablation
if 'afm_qr' in p3 and 'baseline_task' in p3:
    qr_diff = p3['afm_qr']['mean'] - p3['baseline_task']['mean']
    if qr_diff < 0:
        p7['warnings'].append(f"P3: QR alone hurts (Δ={qr_diff:.4f})")

# KL collapse check
for k,v in p4.items():
    if isinstance(v,dict) and 'acc' in v and v['acc']<0.5:
        p7['warnings'].append(f"P4: {k} collapsed")

save('phase7', p7)
print("\n=== ALL PHASES COMPLETE ===", flush=True)
