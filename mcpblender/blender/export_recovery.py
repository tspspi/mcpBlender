"""Bind native exporters to durable filesystem journals without nesting jobs."""
from mcpblender.export_jobs import ExportJob


def run(command,p):
    from .bridge import _bridge,report_progress,check_cancelled
    from . import card_family_export,lods,asset_packages,attribute_export,vegetation_export,vegetation_lod_export
    active=_bridge.active if _bridge and _bridge.active else {}
    if active and 'owner' not in active:raise RuntimeError('Export journaling requires broker owner metadata; update/restart the broker before exporting')
    owner=active.get('owner','stdio')
    if command=='export_attribute_bundle':
        kind='NUMERIC';binding={'export_sha256':p['expected_export']};assets=[];function=attribute_export.export
    elif command=='export_botanical_bundle':
        kind='BOTANICAL';binding={'export_sha256':p['expected_export']};assets=[];function=vegetation_export.export
    elif command=='export_foliage_card_family':
        kind='CARD_FAMILY';binding={'family_guard':p['expected_family']};assets=[];function=card_family_export.export
    elif command=='export_botanical_lods':
        kind='VEGETATION_LOD';binding={'profile_guard':p['expected_lods'],'placement_mode':p['placement'],'materials_sha256':p.get('expected_materials')};assets=[];function=vegetation_lod_export.export
    elif command=='export_asset_package':
        kind='PACKAGE';binding={'source_sha256':p['expected_source']};assets=[a['id'] for a in p['assets']];function=asset_packages.export
    else:
        kind='LOD';binding={'chain_sha256':p['expected_chain'],'animation_sha256':p.get('expected_animation')};assets=[];function=lods.export
    with ExportJob(p['directory'],owner,kind,binding,operation_id=active.get('operation_id'),asset_ids=assets) as job:
        report_progress({'phase':'registered recoverable export','directory':p['directory'],'job_directory':str(job.root),'export_job_id':job.record['id']})
        check_cancelled();return function(p|{'_export_job':job})
