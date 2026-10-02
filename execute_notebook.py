"""Execute the submitted notebook in a fresh kernel using this Python environment."""
import json
import os
from pathlib import Path
import sys
import tempfile
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='module6_kernel_') as tmp:
        kernel=Path(tmp)/'kernels/module6'; kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
            'display_name':'Module 6 verified environment','language':'python'}))
        os.environ['JUPYTER_PATH']=tmp
        n=nbformat.read(ROOT/'kyi_hw6.ipynb',as_version=4)
        NotebookClient(n,timeout=180,kernel_name='module6',resources={'metadata':{'path':str(ROOT)}}).execute()
        assert not any(o.get('output_type')=='error' for c in n.cells for o in c.get('outputs',[]))
        nbformat.write(n,ROOT/'kyi_hw6.ipynb')
    (ROOT/'outputs/notebook_execution.json').write_text(json.dumps({'fresh_kernel':True,'errors':0,
        'executed_code_cells':sum(c.cell_type=='code' for c in n.cells)},indent=2)+'\n')
    print('Notebook executed in a fresh kernel without errors.')
