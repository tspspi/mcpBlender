"""Actual geometry must recover lighting that flat shader normals lose."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from test_botanical_native import pytestmark


def test_geometric_reconstruction_world_and_sun(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    run = subprocess.run(['blender', '--background', '--factory-startup',
        '--disable-autoexec', '--threads', '2', '--python-exit-code', '1',
        '--python', str(Path(__file__).with_name('native_projected_microfacets.py')),
        '--', str(repo), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + '\n' + run.stderr
    proof = json.loads((tmp_path / 'transport-proof.json').read_text())
    for lighting in ('world', 'sun'):
        entry = proof['facets-' + lighting]
        assert abs(entry['relative_red_bias']) < 1e-5
        assert entry['rgba'][3] == entry['reference'][3] == 1
        assert entry['triangles'] == 128  # Reference uses 1024 triangles.
        assert entry['bump_correction']
        assert len(entry['geometry']) == 32
        for piece in entry['geometry']:
            assert piece['max_component_residual'] <= 1e-5
            assert 0 < piece['omitted_mass'] < 1e-6
    assert proof['flat_default-world']['relative_red_bias'] < -.1
    assert proof['flat_no_bump_correction-world']['relative_red_bias'] < -.1
    assert not proof['flat_no_bump_correction-world']['bump_correction']
    assert abs(proof['flat_default-sun']['relative_red_bias']) < 1e-5
    if destination := os.environ.get('MCPBLENDER_MICROFACET_EVIDENCE'):
        out = Path(destination)
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_path / 'transport-proof.json', out / 'native-proof.json')
        for path in tmp_path.glob('*.exr'):
            shutil.copy2(path, out / path.name)
