"""Thin-leaf conversion is limited to the documented managed shader topology."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_adapter_rejects_unknown_nodes_links_and_opt_out(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import botanical_foliage as f,textures as t
mat=f.material('Leaf');tree=mat.node_tree
try:t.material_signature(mat)
except ValueError as e:assert 'FRONT_PBR' in str(e)
else:raise AssertionError('Default opt-out ignored')
state=t.material_signature(mat,thin_foliage_mode='FRONT_PBR');assert state['bake_adapter']['omitted_features']
# A managed marker does not qualify an arbitrary mixed shader.
link=tree.nodes['Output'].inputs['Surface'].links[0];old=link.from_socket;tree.links.remove(link)
tree.links.new(tree.nodes['Optical Mix'].outputs[0],tree.nodes['Output'].inputs['Surface'])
try:t.material_signature(mat,thin_foliage_mode='FRONT_PBR')
except ValueError as e:assert 'link' in str(e)
else:raise AssertionError('Unknown shader topology accepted')
tree.links.new(old,tree.nodes['Output'].inputs['Surface'])
extra=tree.nodes.new('ShaderNodeNewGeometry');extra.name='Foreign Geometry'
try:t.material_signature(mat,thin_foliage_mode='FRONT_PBR')
except ValueError as e:assert 'Unsupported bake material node' in str(e)
else:raise AssertionError('Unqualified geometry node accepted')
tree.nodes.remove(extra)
# Existing direct Principled graphs have identical material fingerprints across modes.
plain=bpy.data.materials.new('Ordinary');plain.use_nodes=True
assert t.material_signature(plain)==t.material_signature(plain,thin_foliage_mode='FRONT_PBR')
print('THIN_ADAPTER_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'THIN_ADAPTER_NATIVE_OK' in result.stdout
