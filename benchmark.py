"""Sequential local service measurements; fixtures are not camera accuracy."""
import json
import platform
import statistics
import time
from pathlib import Path
from service import dispatch
from vision import POLICY

rows=[]
for fixture in ['clean','blur','clipped','glare','blank','missing']:
    payload=json.dumps({'fixture':fixture}).encode()
    dispatch('POST','/api/analyze',payload)
    timings=[];sizes=[]
    for _ in range(20):
        started=time.perf_counter();status,headers,data=dispatch('POST','/api/analyze',payload)
        timings.append((time.perf_counter()-started)*1000);sizes.append(len(data))
        if status!=200:raise RuntimeError('Service benchmark failed')
    ordered=sorted(timings)
    rows.append({'fixture':fixture,'runs':20,'median_ms':round(statistics.median(timings),2),
                 'p95_ms':round(ordered[18],2),'max_response_bytes':max(sizes)})
result={'policy':POLICY,'runtime':platform.python_version(),'platform':platform.system(),
        'method':'One warmup then 20 sequential full dispatcher calls per fixture; wall time includes preview and alignment encoding. Local machine, no network latency.',
        'cases':rows,'total_measured_calls':120,'accuracy_claim':False,
        'cost_claim':False,'limitations':'Generated 640x480 fixtures. Local timing is machine-specific, not AWS latency, invoice cost or real-photo throughput.'}
Path('evidence/local-performance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
