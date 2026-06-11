#!/usr/bin/env python3
"""AFM-Lite Validation Runner v0.2"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2'), exist_ok=True)

import torch, numpy as np, json, time
from ablation_models import get_model, compute_loss
from validation_data import get_mnist, get_fashion_mnist, get_kmnist, get_cifar10, get_synthetic, get_split_mnist, get_permuted_mnist
from scipy import stats
import torch.nn as nn
from ablation_models import AFMWithQR, AFMWithRIB, BaselineLTask
from stiefel import stiefel_project_qr

BS = 1024
EP = 8
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2')

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

def train_eval(config, beta, train_l, test_l, seed, epochs=EP):
    torch.manual_seed(seed); np.random.seed(seed)
    m = get_model(config); opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    best = 0
    for ep in range(epochs):
        m.train()
        for X, y in train_l:
            opt.zero_grad()
            if config in ['afm_qr', 'afm_rib']:
                o, _, mu, lv, kl = m(X); loss = compute_loss(m, config, o, y, mu, lv, kl, beta)
            else:
                o, _, mu, lv = m(X); loss = compute_loss(m, config, o, y, mu, lv, None, beta)
            loss.backward(); opt.step()
        m.eval(); c, t = 0, 0
        with torch.no_grad():
            for X, y in test_l:
                if config in ['afm_qr', 'afm_rib']: o, _, _, _, _ = m(X)
                else: o, _, _, _ = m(X)
                c += (o.argmax(1) == y).sum().item(); t += y.size(0)
        best = max(best, c / t)
    return best

print("=== AFM-Lite Validation Program v0.2 ===", flush=True)
t0 = time.time()

# PHASE 1
print("\n--- PHASE 1: 10-seed replication ---", flush=True)
train_l, test_l, _, _ = get_mnist(batch_size=BS)
p1 = {}
for config, beta in [('baseline_task', 0.0), ('afm_qr', 0.0), ('afm_rib', 1e-3)]:
    accs = [train_eval(config, beta, train_l, test_l, si*42) for si in range(10)]
    m, s = np.mean(accs), np.std(accs, ddof=1)
    ci = stats.t.ppf(0.975, 9) * s / np.sqrt(10)
    p1[config] = {'accs': accs, 'mean': float(m), 'std': float(s), 'ci_95': float(ci)}
    print(f"  {config}: {m:.4f}±{s:.4f} CI:[{m-ci:.4f},{m+ci:.4f}]", flush=True)
bt, ar = p1['baseline_task']['accs'], p1['afm_rib']['accs']
t, p = stats.ttest_rel(ar, bt)
d = np.mean(np.array(ar)-np.array(bt))/np.sqrt((np.std(bt)**2+np.std(ar)**2)/2)
p1['paired'] = {'t': float(t), 'p': float(p), 'd': float(d), 'sig': bool(p<0.05)}
print(f"  Paired: t={t:.3f} p={p:.4f} d={d:.3f}", flush=True)
save('phase1', p1)

# PHASE 2
print("\n--- PHASE 2: Multi-dataset ---", flush=True)
p2 = {}
for ds_name, ds_fn in [('fashion', lambda: get_fashion_mnist(batch_size=BS, max_samples=30000)),
                         ('kmnist', lambda: get_kmnist(batch_size=BS, max_samples=30000)),
                         ('cifar10', lambda: get_cifar10(batch_size=BS, max_samples=30000)),
                         ('synthetic', lambda: get_synthetic(n_samples=20000, batch_size=BS))]:
    try:
        train_l, test_l, in_dim, nc = ds_fn()
        print(f"  {ds_name}: {in_dim}d, {nc}c", flush=True)
        p2[ds_name] = {'input_dim': in_dim, 'num_classes': nc}
        for config, beta in [('baseline_task', 0.0), ('afm_qr', 0.0), ('afm_rib', 1e-3)]:
            accs = [train_eval(config, beta, train_l, test_l, si*42) for si in range(5)]
            p2[ds_name][config] = {'accs': accs, 'mean': float(np.mean(accs)), 'std': float(np.std(accs, ddof=1))}
            print(f"    {config}: {np.mean(accs):.4f}±{np.std(accs):.4f}", flush=True)
    except Exception as e:
        print(f"  {ds_name}: FAILED - {e}", flush=True)
        p2[ds_name] = {'error': str(e)}
save('phase2', p2)

# PHASE 3
print("\n--- PHASE 3: Ablation ---", flush=True)
train_l, test_l, _, _ = get_mnist(batch_size=BS)
p3 = {}
for config, beta in [('baseline_task',0.0),('baseline_vae',1e-3),('afm_no_qr',0.0),
                       ('afm_no_qr',1e-3),('afm_qr',0.0),('afm_rib',1e-3)]:
    key = f"{config}_b{beta}" if beta > 0 else config
    accs = [train_eval(config, beta, train_l, test_l, si*42) for si in range(10)]
    p3[key] = {'config': config, 'beta': beta, 'accs': accs, 'mean': float(np.mean(accs)), 'std': float(np.std(accs, ddof=1))}
    print(f"  {key}: {np.mean(accs):.4f}±{np.std(accs):.4f}", flush=True)
save('phase3', p3)

# PHASE 4
print("\n--- PHASE 4: KL Collapse ---", flush=True)
train_l, test_l, _, _ = get_mnist(batch_size=BS)
p4 = {}
betas = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]
for config in ['baseline_task', 'afm_rib']:
    for beta in betas:
        acc = train_eval(config, beta, train_l, test_l, 42, 8)
        p4[f"{config}_b{beta}"] = {'config': config, 'beta': beta, 'acc': float(acc)}
        print(f"  {config}_b{beta}: {acc:.4f} {'COLLAPSED' if acc<0.5 else ''}", flush=True)
# Norms at high beta
for config, beta in [('baseline_task',1e-2),('afm_rib',1e-2)]:
    torch.manual_seed(42); np.random.seed(42)
    m=get_model(config); opt=torch.optim.Adam(m.parameters(),lr=1e-3)
    norms=[]
    for ep in range(8):
        m.train()
        for X,y in train_l:
            opt.zero_grad()
            if config=='afm_rib': o,_,mu,lv,kl=m(X); loss=compute_loss(m,config,o,y,mu,lv,kl,beta)
            else: o,_,mu,lv=m(X); loss=compute_loss(m,config,o,y,mu,lv,None,beta)
            loss.backward(); opt.step()
        m.eval()
        with torch.no_grad():
            Xs,_=next(iter(test_l))[0],None
            if config=='afm_rib': _,_,mu,lv,_=m(Xs); S,_=m.stiefel(mu,lv); norms.append(float(S.norm().item()))
            else: _,_,mu,lv=m(Xs); norms.append(float(mu.norm().item()))
    p4[f"{config}_norms_b{beta}"]={'norms':norms}
    print(f"  {config} norms: {norms}", flush=True)
# QR test
for d_val in [32]:
    for K_val in [4]:
        Q=stiefel_project_qr(torch.randn(1,d_val,K_val)*1e-10)
        p4['qr_test']={'norm':float(Q.norm().item()),'expected':float(np.sqrt(d_val*K_val))}
save('phase4', p4)

# PHASE 5
print("\n--- PHASE 5: Continual Learning ---", flush=True)
p5 = {}
try:
    split_tasks = get_split_mnist(batch_size=BS)
    tc = [nc for _,_,_,nc in split_tasks]
    class MTLB(BaselineLTask):
        def __init__(self): super().__init__(784,256,128,2); self.heads=nn.ModuleList([nn.Sequential(nn.Linear(128,64),nn.ReLU(),nn.Linear(64,2)) for _ in range(5)])
        def forward(self,x,task_id=0): h=self.encoder(x); mu,lv=self.fc_mu(h),self.fc_logvar(h); z=mu+(torch.exp(0.5*lv)*torch.randn_like(mu) if self.training else 0); return self.heads[task_id](z),mu,lv
    class MTLA(AFMWithRIB):
        def __init__(self): super().__init__(784,256,32,4,2); self.heads=nn.ModuleList([nn.Sequential(nn.Linear(128,64),nn.ReLU(),nn.Linear(64,2)) for _ in range(5)])
        def forward(self,x,task_id=0): h=self.encoder(x); mu,lv=self.fc_mu(h),self.fc_logvar(h); S,kl=self.stiefel(mu,lv); return self.heads[task_id](S.reshape(S.shape[0],-1)),mu,lv,kl
    
    for name,fn,mtype,beta in [('baseline',MTLB,'baseline',0.0),('afm_rib',MTLA,'afm',1e-3)]:
        torch.manual_seed(42); model=fn(); nt=len(split_tasks); am=np.zeros((nt,nt))
        for tid in range(nt):
            tl,tel,_,_=split_tasks[tid]; opt=torch.optim.Adam(model.parameters(),lr=1e-3)
            for ep in range(8):
                model.train()
                for X,y in tl:
                    opt.zero_grad()
                    if mtype=='baseline': o,mu,lv=model(X,tid); ce=F.cross_entropy(o,y); loss=ce+(beta*(-0.5*torch.sum(1+lv-mu.pow(2)-lv.exp(),dim=-1).mean()) if beta>0 else 0)
                    else: o,mu,lv,kl=model(X,tid); ce=F.cross_entropy(o,y); loss=ce+(beta*kl if kl is not None else 0)
                    loss.backward(); opt.step()
            model.eval()
            for eid in range(nt):
                _,el,_,_=split_tasks[eid]; c,t=0,0
                with torch.no_grad():
                    for X,y in el:
                        if mtype=='baseline': o,_,_=model(X,eid)
                        else: o,_,_,_=model(X,eid)
                        c+=(o.argmax(1)==y).sum().item(); t+=y.size(0)
                am[tid,eid]=c/t
        fg=[am[i,i]-am[nt-1,i] for i in range(nt-1)]
        p5[f'split_{name}']={'acc_matrix':am.tolist(),'avg_forgetting':float(np.mean(fg)),'bwt':float(np.mean([am[-1,i]-am[i,i] for i in range(nt-1)])),'avg_acc':float(np.mean([am[-1,i] for i in range(nt)]))}
        print(f"  split_{name}: fg={np.mean(fg):.4f}", flush=True)
except Exception as e:
    print(f"  Split-MNIST FAILED: {e}", flush=True)
    p5['split_error'] = str(e)

try:
    perm_tasks = get_permuted_mnist(n_tasks=5, batch_size=BS)
    for name,Model,mtype,beta in [('baseline',lambda:BaselineLTask(784,256,128,10),'baseline',0.0),('afm_rib',lambda:AFMWithQR(784,256,32,4,10),'afm',1e-3)]:
        torch.manual_seed(42); model=Model(); nt=len(perm_tasks); am=np.zeros((nt,nt))
        for tid in range(nt):
            tl,tel,_,_=perm_tasks[tid]; opt=torch.optim.Adam(model.parameters(),lr=1e-3)
            for ep in range(8):
                model.train()
                for X,y in tl:
                    opt.zero_grad()
                    if mtype=='baseline': o,_,mu,lv=model(X); ce=F.cross_entropy(o,y); loss=ce
                    else: o,_,mu,lv,kl=model(X); ce=F.cross_entropy(o,y); loss=ce+(beta*kl if kl is not None else 0)
                    loss.backward(); opt.step()
            model.eval()
            for eid in range(nt):
                _,el,_,_=perm_tasks[eid]; c,t=0,0
                with torch.no_grad():
                    for X,y in el:
                        if mtype=='baseline': o,_,_,_=model(X)
                        else: o,_,_,_,_=model(X)
                        c+=(o.argmax(1)==y).sum().item(); t+=y.size(0)
                am[tid,eid]=c/t
        fg=[am[i,i]-am[nt-1,i] for i in range(nt-1)]
        p5[f'permuted_{name}']={'acc_matrix':am.tolist(),'avg_forgetting':float(np.mean(fg)),'bwt':float(np.mean([am[-1,i]-am[i,i] for i in range(nt-1)])),'avg_acc':float(np.mean([am[-1,i] for i in range(nt)]))}
        print(f"  permuted_{name}: fg={np.mean(fg):.4f}", flush=True)
except Exception as e:
    print(f"  Permuted-MNIST FAILED: {e}", flush=True)
save('phase5', p5)

# PHASE 6
print("\n--- PHASE 6: Representation ---", flush=True)
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
            if config in ['afm_qr','afm_rib']:
                _,_,mu,lv,_=m(X); S,_=m.stiefel(mu,lv); lats.append(S.reshape(S.shape[0],-1).numpy())
            else: _,_,mu,lv=m(X); lats.append(mu.numpy())
            labs.append(y.numpy())
    lat=np.concatenate(lats); lab=np.concatenate(labs)
    pca=PCA(n_components=min(10,lat.shape[1])).fit(lat); ev=pca.explained_variance_ratio_
    sil=silhouette_score(lat,lab,sample_size=min(5000,len(lab)))
    ti={}
    if config in ['afm_qr','afm_rib']:
        with torch.no_grad():
            ss=[]
            for i,(X,y) in enumerate(test_l):
                if i>=10: break
                mu,lv=m.fc_mu(m.encoder(X)),m.fc_logvar(m.encoder(X)); S,_=m.stiefel(mu,lv); ss.append(S.numpy())
        sd=np.concatenate(ss); K=sd.shape[2]
        ti={'tc':[float(abs(np.corrcoef(sd[:,0,k],lab[:len(sd)])[0,1])) for k in range(K)],
            'dots':[float(np.mean(np.sum(sd[:,:,k1]*sd[:,:,k2],axis=1))) for k1 in range(K) for k2 in range(k1+1,K)]}
    p6[config]={'pca_ev':ev.tolist(),'pca_cum':float(ev.sum()),'sil':float(sil),'thread_info':ti}
    print(f"  {config}: sil={sil:.4f}", flush=True)
save('phase6', p6)

# PHASE 7
print("\n--- PHASE 7: Failure Analysis ---", flush=True)
p7 = {'failures':[], 'warnings':[]}
if not p1.get('paired',{}).get('sig',False):
    p7['failures'].append(f"P1: Not significant (p={p1['paired']['p']:.4f})")
else:
    p7['warnings'].append(f"P1: Significant p={p1['paired']['p']:.4f}")
for ds,dd in p2.items():
    if isinstance(dd,dict) and 'error' in dd: p7['failures'].append(f"P2: {ds} failed")
    elif isinstance(dd,dict):
        bt=dd.get('baseline_task',{}).get('mean',0); ar=dd.get('afm_rib',{}).get('mean',0)
        if ar<bt: p7['failures'].append(f"P2: AFM worse on {ds}")
save('phase7', p7)

print(f"\n=== DONE in {time.time()-t0:.0f}s ===", flush=True)
