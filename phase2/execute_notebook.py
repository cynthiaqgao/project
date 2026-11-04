"""Execute the project notebook with this interpreter in an isolated fresh kernel."""
import json
import os
from pathlib import Path
import sys
import tempfile
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

def execute():
    notebook_path = ROOT / 'phase2_traveler_clean_team_data.ipynb'
    notebook = nbformat.read(notebook_path, as_version=4)
    previous_path = os.environ.get('JUPYTER_PATH')
    try:
        with tempfile.TemporaryDirectory(prefix='phase2_traveler_kernel_') as temp:
            kernel = Path(temp) / 'kernels/phase2-traveler'
            kernel.mkdir(parents=True)
            (kernel / 'kernel.json').write_text(json.dumps({
                'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                'display_name': 'LA Airbnb Phase 2 Travelers', 'language': 'python'}))
            os.environ['JUPYTER_PATH'] = temp
            NotebookClient(notebook, timeout=180, kernel_name='phase2-traveler',
                           resources={'metadata': {'path': str(ROOT)}}).execute()
    finally:
        if previous_path is None:
            os.environ.pop('JUPYTER_PATH', None)
        else:
            os.environ['JUPYTER_PATH'] = previous_path
    errors = [o for c in notebook.cells for o in c.get('outputs', []) if o.get('output_type') == 'error']
    assert not errors
    nbformat.validate(notebook)
    nbformat.write(notebook, notebook_path)
    report = {'notebook': notebook_path.name, 'fresh_kernel': True, 'errors': len(errors),
              'executed_code_cells': sum(c.cell_type == 'code' for c in notebook.cells)}
    (ROOT / 'phase2/notebook_execution.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    execute()
