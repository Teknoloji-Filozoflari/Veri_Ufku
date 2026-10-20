"""Independent file shards; merge original JUnit cases with exact coverage checks."""
import os,sys,time,json,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,UTC
root=Path('/home/s-oktay/Belgeler/Veri_Ufku');out=root/'docs/evidence/phase39';started=time.monotonic();stamp=datetime.now(UTC).isoformat()
original=ET.parse(out/'full-before-catalog-count-fix.xml').getroot();expected={(c.get('classname'),c.get('name')) for c in original.iter('testcase')};weights={}
for c in original.iter('testcase'):
 name=next(n for n in c.get('classname').split('.') if n.startswith('test_'));filename='tests/'+name+'.py';assert (root/filename).is_file(),filename
 weights[filename]=weights.get(filename,0)+float(c.get('time','0'))
shards=[[] for _ in range(4)];loads=[0.0]*4
for name,weight in sorted(weights.items(),key=lambda p:-p[1]):
 target=min(range(4),key=lambda i:loads[i]);shards[target].append(name);loads[target]+=weight
inputs={}
for directory in ('src','tests','scripts'):
 for p in (root/directory).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.qml','.js','.json','.ts','.qm'):
   inputs[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
for filename in ('pyproject.toml','uv.lock'):inputs[filename]=hashlib.sha256((root/filename).read_bytes()).hexdigest()
(out/'run-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
env={**os.environ,'PYTHONUNBUFFERED':'1','QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'};processes=[];records=[]
for i,files in enumerate(shards):
 xml=out/f'full-shard-{i+1}.xml';log=out/f'full-shard-{i+1}.txt';cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*files,'--junitxml='+str(xml),'-o',f'cache_dir=/tmp/phase39-delivery-cache-{i+1}','--basetemp='+f'/tmp/phase39-delivery-tests-{i+1}']
 stream=log.open('w');process=subprocess.Popen(cmd,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT);processes.append((process,stream));records.append(dict(shard=i+1,files=files,command=cmd,xml=xml.name,log=log.name,estimated_seconds=loads[i]))
(out/'full-shards.json').write_text(json.dumps(dict(id='E39-FULL-SHARDS',date=stamp,shards=records,state='running'),indent=2)+'\n')
print('START four independent pytest file shards, coverage',len(expected),'cases; expected balanced seconds',loads,flush=True)
remaining=set(range(4))
while remaining:
 for i in list(remaining):
  code=processes[i][0].poll()
  if code is not None:
   processes[i][1].close();records[i]['exit_code']=code;remaining.remove(i);print('FINISHED',i+1,'exit',code,flush=True)
 time.sleep(1)
wall=time.monotonic()-started
all_cases=[];seen=set();suites=[]
for rec in records:
 tree=ET.parse(out/rec['xml']).getroot();suite=tree.find('testsuite');suites.append(suite)
 for c in tree.iter('testcase'):
  key=(c.get('classname'),c.get('name'));assert key not in seen,key;seen.add(key);all_cases.append(c)
assert seen==expected,(expected-seen,seen-expected)
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in inputs.items())
attrs=dict(name='pytest-complete-four-independent-file-shards',tests=str(len(all_cases)),errors=str(sum(int(s.get('errors')) for s in suites)),failures=str(sum(int(s.get('failures')) for s in suites)),skipped=str(sum(int(s.get('skipped')) for s in suites)),time=f'{wall:.3f}',timestamp=stamp,hostname='s-oktay')
merged=ET.Element('testsuites');suite=ET.SubElement(merged,'testsuite',attrs)
for case in sorted(all_cases,key=lambda c:(c.get('classname'),c.get('name'))):suite.append(case)
ET.ElementTree(merged).write(out/'full-regression.xml',encoding='utf-8',xml_declaration=True)
report=dict(id='E39-FULL-SHARDS',date=stamp,completed=datetime.now(UTC).isoformat(),wall_seconds=wall,aggregate_shard_seconds=sum(float(s.get('time')) for s in suites),coverage_exact=True,coverage_cases=len(seen),state='passed' if all(r['exit_code']==0 for r in records) else 'failed',shards=records)
(out/'full-shards.json').write_text(json.dumps(report,indent=2)+'\n')
summary=f"Full suite via4 independent file shards: {len(all_cases)-int(attrs['skipped'])-int(attrs['failures'])-int(attrs['errors'])} passed, {attrs['skipped']} skipped, {attrs['failures']} failed, {attrs['errors']} errors, {wall:.2f}s wall; exact coverage {len(seen)} cases.\n"
Path('/tmp/phase39-full.log').write_text(summary+'Original shard logs and JUnit files are retained in docs/evidence/phase39.\n');print(summary,flush=True)
raise SystemExit(any(r['exit_code'] for r in records))
