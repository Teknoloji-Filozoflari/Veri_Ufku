import sys, json, os
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')

def main():
 import pytest,polars as pl,tempfile
 from PySide6.QtCore import QObject
 from test_import_gui import setup,spin,teardown
 with tempfile.TemporaryDirectory(prefix='phase39-mapping-') as temp,pytest.MonkeyPatch.context() as patch:
  root=Path(temp);app,window,_,projects,imports=setup(root,patch)
  try:
   engine=app._veri_ufku_resources[0];data=engine._dataset_resources;charts=engine._charts_resources;dashboard=engine._dashboard_resources
   sources=[]
   for filename,frame in [('a',pl.DataFrame({'key':['a','b',None],'x':[1,2,3],'y':[2,4,6]})),('b',pl.DataFrame({'client':['a','a','b',None],'value':[20,30,10,40]}))]:
    source=root/(filename+'.parquet');frame.write_parquet(source);sources.append((source,source.read_bytes()))
    imports.choose(str(source));spin(app,lambda:not imports.busy);imports.importData();spin(app,lambda:not imports.busy)
    assert not imports.errorText,imports.errorText
    d=projects.draft['datasets'][-1];data.selectDataset(d['dataset_id']);spin(app,lambda:not data.busy);columns={c['name']:c['id'] for c in d['import_metadata']['columns']};version=d['version_id']
    if filename=='a':
     av,ac=version,columns
     charts.create(json.dumps({'kind':'scatter','x':ac['x'],'y':ac['y'],'scope':'full'}));spin(app,lambda:not charts.busy);assert not charts.errorText,charts.errorText
     charts.save();spin(app,lambda:not charts.busy);assert not charts.errorText,charts.errorText
     chart=charts.savedCharts[-1]['id']
    else:bv,bc=version,columns
   dashboard.addWidget('chart',av,'',chart,'');dashboard.addWidget('table',av,ac['key'],'','');dashboard.addWidget('table',bv,bc['client'],'','');dashboard.addWidget('kpi',bv,bc['value'],'','')
   assert not dashboard.errorText,dashboard.errorText
   window.setProperty('selectedSection',3);window.findChild(QObject,'dashboardExpanded').setProperty('checked',True)
   def select(name,model,value):
    obj=window.findChild(QObject,name);assert obj is not None,name
    index=next(i for i,v in enumerate(model) if v['id']==value);obj.setProperty('currentIndex',index)
   select('dashboardDataset',dashboard.datasets,av)
   select('dashboardFilterColumn',next(v['columns'] for v in dashboard.datasets if v['id']==av),ac['key'])
   select('dashboardMappingDataset',dashboard.datasets,bv)
   select('dashboardMappingColumn',next(v['columns'] for v in dashboard.datasets if v['id']==bv),bc['client'])
   window.findChild(QObject,'dashboardMap').clicked.emit();assert not dashboard.errorText,dashboard.errorText
   assert len(dashboard.spec['filter_mappings'])==1
   dashboard.addFilter('',av,ac['key'],'eq','a')
   kpi=next(w for w in dashboard.spec['widgets'] if w['kind']=='kpi');dashboard.updateWidget(kpi['id'],json.dumps({'aggregation':'sum'}));dashboard.addFilter(kpi['id'],bv,bc['value'],'gte','20')
   dashboard.evaluate();spin(app,lambda:not dashboard.busy,timeout=40000);assert not dashboard.errorText,dashboard.errorText
   widgets=dashboard.result['widgets'];assert [w['n'] for w in widgets]==[1,1,2,2]
   assert widgets[-1]['kpi']['value']=='50'
   graph=widgets[0];metadata=graph['chart']['render'];point=metadata['pixels'][0];expected=graph['memberships'][str(point['point_id'])]
   x,y=point['x']/metadata['width'],point['y']/metadata['height'];dashboard.brush(graph['id'],x,y,x,y)
   spin(app,lambda:not dashboard.busy,timeout=40000);assert not dashboard.errorText,dashboard.errorText
   assert dashboard.spec['selection']['row_ids']==expected
   assert [w['linked_count'] for w in dashboard.result['widgets']]==[1,1,2,2]
   dashboard.drillDown(True);spin(app,lambda:not dashboard.busy,timeout=40000);assert not dashboard.errorText,dashboard.errorText
   assert [w['n'] for w in dashboard.result['widgets']]==[1,1,2,2]
   assert all(p.read_bytes()==original for p,original in sources)
   Path('docs/evidence/phase39/mapping-gui.json').write_text(json.dumps(dict(id='E39-MAPPING-GUI',environment='ENV-39',date='2026-10-11',passed=True,checks=['Actual QML explicit source/target ColumnId mapping button','Global source key predicate transfers only via chosen mapping','Local target KPI gte20 sum50 independent reference','Normalized real chart pixel brush selects exact source RowId','Duplicate target key links two rows and drilldown preserves them','Both source files byte-identical'],row_counts=[1,1,2,2],linked_counts=[1,1,2,2],kpi_reference=50),indent=2)+'\n')
   print('PASS actual QML source mapping + local KPI + chart pixel brush + drilldown')
  finally:teardown(app,window)
if __name__=='__main__':main()
