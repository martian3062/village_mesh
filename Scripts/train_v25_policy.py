"""Reproducible synthetic imitation experiment; no language model is deployed.

Held-out environment families and seeds, never random adjacent-row splits.
The teacher is authored code, not human/local validation or proof of benefit.
"""
from pathlib import Path
import hashlib,json,time
import numpy as np
import torch
from torch import nn
import onnx
import onnxruntime as ort
from v25_contracts import SCHEMA,valid_actions,baseline

ROOT=Path(__file__).resolve().parents[1]
class Policy(nn.Sequential):
    def __init__(self):super().__init__(nn.Linear(64,256),nn.ReLU(),nn.Linear(256,256),nn.ReLU(),nn.Linear(256,128),nn.ReLU(),nn.Linear(128,48))
class Intent(nn.Module):
    def __init__(self):
        super().__init__();self.embedding=nn.Embedding(259,96);self.gru=nn.GRU(96,192,batch_first=True);self.head=nn.Linear(192,32)
class RecurrentPolicy(nn.Module):
    def __init__(self):super().__init__();self.gru=nn.GRU(64,160,batch_first=True);self.head=nn.Linear(160,48)
class MicroDecoder(nn.Module):
    def __init__(self):
        super().__init__();self.token=nn.Embedding(259,128);self.position=nn.Embedding(256,128)
        self.blocks=nn.ModuleList([nn.TransformerEncoderLayer(128,4,256,batch_first=True,dropout=0) for _ in range(4)])
        self.norm=nn.LayerNorm(128);self.head=nn.Linear(128,259,bias=False);self.head.weight=self.token.weight

def dataset(seed,count,heldout=False):
    rng=np.random.default_rng(seed);x=rng.random((count,64),dtype=np.float32)
    binary=[2,5,16,19,24,25,26,27,28,30,31,32,33,34,36,38,39,48,53]
    x[:,binary]=(x[:,binary]>.5).astype(np.float32)
    # Separate route/weather combinations: hold out longer, wetter routes.
    x[:,35]=rng.uniform(.65,1,count) if heldout else rng.uniform(0,.65,count)
    x[:,3]=rng.uniform(.65,1,count) if heldout else rng.uniform(0,.65,count)
    masks=np.array([valid_actions(row.tolist()) for row in x],dtype=bool)
    y=np.array([baseline(row.tolist(),mask) for row,mask in zip(x,masks)],dtype=np.int64)
    return torch.from_numpy(x),torch.from_numpy(masks),torch.from_numpy(y)

def main():
    torch.set_num_threads(4);torch.manual_seed(3062);np.random.seed(3062)
    folder=ROOT/'Assets/Models';folder.mkdir(parents=True,exist_ok=True)
    docs=ROOT/'Docs/V25';docs.mkdir(parents=True,exist_ok=True)
    counts={name:sum(p.numel() for p in cls().parameters()) for name,cls in [('policy',Policy),('intent',Intent),('recurrent_policy',RecurrentPolicy),('micro_decoder',MicroDecoder)]}
    assert counts==dict(policy=121520,intent=198080,recurrent_policy=116208,micro_decoder=596096),counts
    model=Policy();train=dataset(3062,16000);test=dataset(9001,4000,True)
    opt=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.001);started=time.perf_counter()
    model.train()
    for epoch in range(36):
        order=torch.randperm(len(train[0]))
        for ids in order.split(256):
            x,m,y=[a[ids] for a in train];scores=model(x).masked_fill(~m,-1e9)
            loss=nn.functional.cross_entropy(scores,y);opt.zero_grad();loss.backward();opt.step()
        if epoch%6==0:print('epoch',epoch,'loss',float(loss.detach()),flush=True)
    model.eval();x,m,y=test
    with torch.no_grad():outputs=model(x);prediction=outputs.masked_fill(~m,-1e9).argmax(1)
    agreement=float((prediction==y).float().mean());invalid=int((~m[torch.arange(len(y)),prediction]).sum())
    path=folder/'npc_policy_v1.onnx'
    torch.onnx.export(model,torch.zeros(1,64),str(path),input_names=['state'],output_names=['logits'],opset_version=17,dynamo=False)
    exported=onnx.load(path);onnx.checker.check_model(exported)
    physical=sum(int(np.prod(t.dims)) for t in exported.graph.initializer)
    assert physical==121520
    session=ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
    vectors=[];errors=[];times=[]
    for i in range(64):
        value=x[i:i+1].numpy();t=time.perf_counter();out=session.run(None,{'state':value})[0];times.append((time.perf_counter()-t)*1000)
        errors.append(float(np.max(np.abs(out-outputs[i:i+1].numpy()))))
        vector=value[0].tolist();mask=valid_actions(vector)
        vectors.append({'input':vector,'output':out[0].tolist(),'valid_mask':mask,'baseline_action':baseline(vector,mask)})
    assert max(errors)<.0001
    matrix=np.zeros((48,48),dtype=int)
    for a,b in zip(y.tolist(),prediction.tolist()):matrix[a,b]+=1
    report={'training':'original synthetic deterministic-controller imitation; not locally reviewed human choices',
        'train_seed':3062,'heldout_seed':9001,'split':'disjoint seed and route-distance/wetness ranges; 16000 train, 4000 held-out',
        'teacher_agreement':agreement,'invalid_after_mask':invalid,'pytorch_ort_max_abs_error':max(errors),
        'ort_cpu_median_ms':float(np.median(times)),'ort_cpu_p95_ms':float(np.percentile(times,95)),
        'train_seconds':time.perf_counter()-started,'confusion_matrix':matrix.tolist(),
        'baseline_benefit_proven':False,'release_policy':'experimental learned mode; deterministic rules remain default',
        'torch_version':torch.__version__,'ort_version':ort.__version__,'onnx_version':onnx.__version__}
    (docs/'policy_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'policy_parity.json').write_text(json.dumps({'schema':SCHEMA,'vectors':vectors},indent=2)+'\n')
    manifest={'schema_version':1,'feature_schema':SCHEMA,'architecture':'MLP 64-256-256-128-48, biased linear and ReLU',
        'deployed_models':[{'id':'policy_v1','file':path.name,'unique_parameters':121520,'physical_initializer_values':physical,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'format':'ONNX','opset':17,'input':[1,64],'output':[1,48],'license':'MIT'}],
        'deployed_total_parameters':121520,'parameter_limit':1000000,'architecture_audit':counts,
        'intent_enabled':False,'micro_decoder_enabled':False,'runtime_compatibility':'pending Unreal editor and packaged parity',
        'data_version':'synthetic_teacher_v1','evaluation':'../../Docs/V25/policy_evaluation.json','default_mode':'rules',
        'reason':'Imitation correctness does not prove improvement over the deterministic baseline.'}
    (folder/'npc_model_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='confusion_matrix'}),flush=True)
if __name__=='__main__':main()
