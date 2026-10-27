import importlib.abc
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,'/tmp/veri-ufku-f72-wheel')
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'cryptography','keyring'}:
            raise ImportError('optional privacy extra deliberately unavailable')
sys.meta_path.insert(0,Missing())
import importlib.util
original_find_spec=importlib.util.find_spec
importlib.util.find_spec=lambda name,*args,**kwargs:None if name.split(".")[0] in {"cryptography","keyring"} else original_find_spec(name,*args,**kwargs)
with tempfile.TemporaryDirectory(prefix='vu-f72-optional-') as d:
    for k in ('CONFIG','STATE','CACHE'):os.environ['XDG_'+k+'_HOME']=str(Path(d)/k.lower())
    from veri_ufku.app import create_application
    app,window,bridge=create_application()
    try:
        from veri_ufku.exports.privacy_keys import generate
        from veri_ufku.storage.project_model import ProjectError
        try:generate('fernet','unavailable-test')
        except ProjectError as e:assert 'Optional privacy extra' in str(e)
        else:raise AssertionError('Missing dependency must reject crypto')
        assert 'cryptography' not in sys.modules and 'keyring' not in sys.modules
        print('OPTIONAL_PRIVACY_ABSENT_GUI PASS; no live keyring/no cryptography imports')
    finally:
        app._veri_ufku_resources[-1]()
        window.deleteLater();app.processEvents()
