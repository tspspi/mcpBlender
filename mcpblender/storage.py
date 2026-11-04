"""Available-space reporting and output admission checks (stdlib only)."""
import math
import os
import shutil
import time
from pathlib import Path

DEFAULT_RESERVE = 256 * 1024 * 1024


def snapshot(path, estimated_bytes=0, reserve_bytes=DEFAULT_RESERVE, warn_below_bytes=2 * 1024**3, estimate_kind="unknown"):
    path = Path(path).expanduser().resolve()
    existing = path
    while True:
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        if existing.is_file():
            existing = existing.parent
        try:
            usage = shutil.disk_usage(existing)
            device = existing.stat().st_dev
            break
        except FileNotFoundError:
            # Owned cleanup may remove this directory after the existence check
            # or disk-usage read. Continue on a surviving ancestor filesystem.
            if existing == existing.parent:
                raise
            existing = existing.parent
    available = max(0, usage.free - reserve_bytes)
    return {"path": str(path), "filesystem_path": str(existing), "device": device,
            "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free,
            "reserve_bytes": reserve_bytes, "available_after_reserve_bytes": available,
            "estimated_output_bytes": estimated_bytes, "estimate_kind": estimate_kind,
            "enough_space": available >= estimated_bytes and usage.free >= reserve_bytes,
            "warning": "Low available storage" if usage.free < warn_below_bytes else None,
            "checked_at": time.time()}


def require_space(path, estimated_bytes=0, **policy):
    report = snapshot(path, estimated_bytes, **policy)
    if not report["enough_space"]:
        raise OSError(f"Insufficient storage: free_bytes={report['free_bytes']}, reserve_bytes={report['reserve_bytes']}, "
                      f"estimated_output_bytes={estimated_bytes}, estimate_kind={report['estimate_kind']}")
    return report


def estimate(command, params):
    if command in {"bake_rigid_bodies","bake_simulation","bake_fluid","bake_textures","build_texture_atlas","render_camera_batch"}:
        return 16*1024**2, "initial_project_heuristic_worker_refines_with_body_count_and_range"
    if command in {"create_botanical_tree", "regenerate_botanical_tree", "create_asset_assembly","create_botanical_wind_preview", "create_botanical_lods"}:
        return 16*1024**2, "initial_native_graph_transfer_heuristic_worker_refines_mesh_and_image_size"
    if command in {"export_lod_chain", "export_asset_package", "export_attribute_bundle", "export_botanical_bundle", "export_botanical_lods"}:
        return 16*1024**2, "initial_lod_bundle_heuristic_worker_refines_geometry_and_texture_estimate"
    if command == "run_action":
        return sum(s["storage"]["estimated_bytes"] for s in params["steps"]), "sum_known_action_outputs_some_steps_may_be_unknown"
    if command == "render_animation_preview":
        frames, _ = estimate("render_animation", params)
        video, _ = estimate("render_video", params) if params.get("make_video", True) else (0, "")
        return frames + video, "png_pixel_bound_plus_uncompressed_video_heuristic"
    if command in ("render_still", "capture_viewport", "render_animation"):
        count = 1
        if command == "render_animation":
            count = (params["frame_end"] - params["frame_start"]) // params.get("frame_step", 1) + 1
        # PNG may be RGBA16. Include modest compression overhead, not an assumed ratio.
        return math.ceil(params.get("width", 800) * params.get("height", 600) * 8 * 1.1) * count, "conservative_pixel_bound"
    if command == "download_asset":
        return params.get("max_bytes", 0), "configured_download_limit"
    if command == "render_video":
        count = params["frame_end"] - params["frame_start"] + 1
        return params.get("width", 640) * params.get("height", 360) * 4 * count, "uncompressed_video_heuristic"
    if command == "save_blend":
        path = Path(params["path"])
        return max(16 * 1024**2, path.stat().st_size * 2 if path.is_file() else 0), "project_size_heuristic"
    return 0, "unknown"
