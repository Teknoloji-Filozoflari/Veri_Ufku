"""Four independent file shards, exact collected/JUnit coverage and immutable inputs."""
import hashlib,json,os,subprocess,time,xml.etree.ElementTree as ET
from datetime import UTC,datetime
from pathlib import Path
root=Path('/home/s-oktay/Belgeler/Veri_Ufku');out=root/'docs/evidence/phase40';started=time.monotonic();stamp=datetime.now(UTC).isoformat()
env={**os.environ,'PYTHONUNBUFFERED':'1','QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'}
collected=subprocess.run([str(root/'.venv/bin/python'),'-m','pytest','--collect-only','-q'],cwd=root,env=env,capture_output=True,text=True);(out/'collection.log').write_text(collected.stdout+collected.stderr);assert collected.returncode==0
nodeids=[l for l in collected.stdout.splitlines() if l.startswith('tests/') and '::' in l];expected=set();files=set()
for node in nodeids:
 parts=node.split('::');files.add(parts[0]);expected.add(('.'.join([parts[0][:-3].replace('/','.')]+parts[1:-1]),parts[-1]))
assert len(expected)==len(nodeids) and len(expected)>1132
weights={f:1. for f in files}
for c in ET.parse(root/'docs/evidence/phase39/full-regression.xml').getroot().iter('testcase'):
 f='tests/'+next(n for n in c.get('classname').split('.') if n.startswith('test_'))+'.py';weights[f]+=float(c.get('time','0'))
weights['tests/test_statistical_models.py']=12.;weights['tests/test_statistical_models_gui.py']=72.
shards=[[] for _ in range(4)];loads=[0.]*4
for f,w in sorted(weights.items(),key=lambda p:-p[1]):
 i=min(range(4),key=lambda k:loads[k]);shards[i].append(f);loads[i]+=w
inputs={}
for directory in ('src','tests','scripts'):
 for p in (root/directory).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.qml','.js','.json','.ts','.qm'):inputs[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
for f in ('pyproject.toml','uv.lock'):inputs[f]=hashlib.sha256((root/f).read_bytes()).hexdigest()
(out/'run-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');processes=[];records=[]
for i,fs in enumerate(shards):
 xml=out/f'full-shard-{i+1}.xml';log=out/f'full-shard-{i+1}.log';cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*fs,'--junitxml='+str(xml),'-o',f'cache_dir=/tmp/phase40-cache-{i+1}','--basetemp='+f'/tmp/phase40-tests-{i+1}'];stream=log.open('w');proc=subprocess.Popen(cmd,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT);processes.append((proc,stream));records.append(dict(shard=i+1,files=fs,command=cmd,xml=xml.name,log=log.name))
print('START',len(expected),'collected cases, four independent file shards',loads,flush=True)
remaining=set(range(4))
while remaining:
 for i in list(remaining):
  code=processes[i][0].poll()
  if code is not None:processes[i][1].close();records[i]['exit_code']=code;remaining.remove(i);print('FINISHED',i+1,'exit',code,flush=True)
 time.sleep(1)
seen=set();cases=[];suites=[]
for rec in records:
 tree=ET.parse(out/rec['xml']).getroot();suites.append(tree.find('testsuite'))
 for c in tree.iter('testcase'):
  key=(c.get('classname'),c.get('name'));assert key not in seen;seen.add(key);cases.append(c)
assert seen==expected,(expected-seen,seen-expected)
assert all(hashlib.sha256((root/f).read_bytes()).hexdigest()==h for f,h in inputs.items())
attrs=dict(name='pytest-four-independent-file-shards',tests=str(len(cases)),errors=str(sum(int(s.get('errors')) for s in suites)),failures=str(sum(int(s.get('failures')) for s in suites)),skipped=str(sum(int(s.get('skipped')) for s in suites)),time=str(time.monotonic()-started),timestamp=stamp)
merged=ET.Element('testsuites');suite=ET.SubElement(merged,'testsuite',attrs)
for c in sorted(cases,key=lambda c:(c.get('classname'),c.get('name'))):suite.append(c)
ET.ElementTree(merged).write(out/'full-regression.xml',encoding='utf-8',xml_declaration=True)
report=dict(id='E40-FULL',date=stamp,finished=datetime.now(UTC).isoformat(),coverage_exact=True,cases=len(cases),inputs_unchanged=len(inputs),result=attrs,shards=records);(out/'full-shards.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['result']),flush=True)
raise SystemExit(any(r['exit_code'] for r in records))
