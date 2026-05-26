import json
import base64
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh.visual import ColorVisuals


def export_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mesh.is_empty:
        raise ValueError("Cannot export an empty mesh.")
    mesh.export(path)


def export_obj(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mesh.is_empty:
        raise ValueError("Cannot export an empty mesh.")
    mesh.export(path)


def export_glb(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mesh.is_empty:
        raise ValueError("Cannot export an empty mesh.")
    mesh.export(path, file_type="glb")


def export_gltf(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mesh.is_empty:
        raise ValueError("Cannot export an empty mesh.")
    mesh.export(path, file_type="gltf")


def make_visual_scene(
    terrain_mesh: trimesh.Trimesh,
    buildings_mesh: trimesh.Trimesh,
) -> trimesh.Scene:
    terrain_node = _scene_mesh(terrain_mesh, rgba=(175, 148, 120, 255))
    building_node = _scene_mesh(buildings_mesh, rgba=(190, 190, 195, 255))
    if terrain_node is None and building_node is None:
        raise ValueError("Cannot export an empty scene.")
    scene = trimesh.Scene()
    if terrain_node is not None:
        scene.add_geometry(terrain_node, geom_name="terrain")
    if building_node is not None:
        scene.add_geometry(building_node, geom_name="buildings")
    return scene


def export_obj_scene(scene: trimesh.Scene, path: Path) -> None:
    _export_scene(scene, path)


def export_glb_scene(scene: trimesh.Scene, path: Path) -> None:
    _export_scene(scene, path, file_type="glb")


def export_gltf_scene(scene: trimesh.Scene, path: Path) -> None:
    _export_scene(scene, path, file_type="gltf")


def _scene_mesh(mesh: trimesh.Trimesh, rgba: tuple[int, int, int, int]) -> trimesh.Trimesh | None:
    if mesh.is_empty:
        return None
    node = mesh.copy()
    colors = np.tile(np.array(rgba, dtype=np.uint8), (len(node.vertices), 1))
    node.visual = ColorVisuals(mesh=node, vertex_colors=colors)
    return node


def _export_scene(scene: trimesh.Scene, path: Path, file_type: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not scene.geometry:
        raise ValueError("Cannot export an empty scene.")
    if file_type is None:
        scene.export(path)
        return
    scene.export(path, file_type=file_type)


def cleanup_normals(mesh: trimesh.Trimesh) -> bool:
    fixer = getattr(mesh, "fix_normals", None)
    if callable(fixer):
        try:
            fixer()
            return True
        except Exception:
            pass
    repair_module = getattr(trimesh, "repair", None)
    fixer = getattr(repair_module, "fix_normals", None) if repair_module is not None else None
    if callable(fixer):
        try:
            fixer(mesh)
            return True
        except Exception:
            pass
    return _lightweight_normal_cleanup(mesh)


def _lightweight_normal_cleanup(mesh: trimesh.Trimesh) -> bool:
    try:
        remover = getattr(mesh, "remove_unreferenced_vertices", None)
        if callable(remover):
            remover()
        merger = getattr(mesh, "merge_vertices", None)
        if callable(merger):
            merger()
        _ = mesh.face_normals
        return True
    except Exception:
        return False


def export_summary(summary: dict[str, Any], out_path: Path) -> Path:
    summary_path = out_path.with_name(f"{out_path.stem}_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def export_preview_html(stl_path: Path, summary: dict[str, Any]) -> Path:
    preview_path = stl_path.with_name(f"{stl_path.stem}_preview.html")
    stl_base64 = base64.b64encode(stl_path.read_bytes()).decode("ascii")
    summary_json = (
        json.dumps(summary, indent=2)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    title = stl_path.name
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} preview</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: Arial, sans-serif;
      background: #111;
      color: #eee;
    }}
    #viewport {{
      position: fixed;
      inset: 0;
    }}
    #panel {{
      position: fixed;
      top: 16px;
      left: 16px;
      max-width: 360px;
      padding: 12px 14px;
      background: rgba(20, 20, 20, 0.82);
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: 8px;
      font-size: 13px;
      line-height: 1.45;
    }}
    #panel h2 {{
      margin: 0 0 10px;
      font-size: 14px;
      font-weight: 600;
      color: #f2f2f2;
    }}
    #panel dl {{
      margin: 0;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 10px;
    }}
    #panel dt {{
      color: #b4b4b4;
    }}
    #panel dd {{
      margin: 0;
      color: #efefef;
      word-break: break-word;
    }}
    #panel .outputs {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
    }}
    #panel .outputs ul {{
      margin: 6px 0 0;
      padding-left: 16px;
    }}
    #panel a {{
      color: #9fcbff;
    }}
  </style>
</head>
<body>
  <div id="viewport"></div>
  <div id="panel"></div>
  <script type="module">
    import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.181.2/build/three.module.js";
    import {{ OrbitControls }} from "https://cdn.jsdelivr.net/npm/three@0.181.2/examples/jsm/controls/OrbitControls.js";
    import {{ STLLoader }} from "https://cdn.jsdelivr.net/npm/three@0.181.2/examples/jsm/loaders/STLLoader.js";

    const summary = {summary_json};
    const stlBase64 = "{stl_base64}";

    function base64ToArrayBuffer(value) {{
      const binary = atob(value);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
      return bytes.buffer;
    }}

    const container = document.getElementById("viewport");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x333333, 2.4));
    const light = new THREE.DirectionalLight(0xffffff, 1.5);
    light.position.set(1, -1, 2);
    scene.add(light);

    const loader = new STLLoader();
    const geometry = loader.parse(base64ToArrayBuffer(stlBase64));
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({{
      color: 0xd8d2c4,
      roughness: 0.85,
      metalness: 0.0,
    }});
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const box = new THREE.Box3().setFromObject(mesh);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    mesh.position.sub(center);

    const maxDim = Math.max(size.x, size.y, size.z);
    camera.position.set(maxDim * 0.8, -maxDim * 1.4, maxDim * 0.8);
    camera.near = Math.max(0.1, maxDim / 1000);
    camera.far = maxDim * 20;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();

    const grid = new THREE.GridHelper(maxDim * 1.3, 20, 0x444444, 0x252525);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -size.z / 2;
    scene.add(grid);

    function toFileHref(pathValue) {{
      if (/^[a-zA-Z]:[\\\\/]/.test(pathValue)) {{
        return `file:///${{pathValue.replace(/\\\\/g, "/")}}`;
      }}
      if (pathValue.startsWith("/") || pathValue.startsWith("\\\\")) {{
        return `file://${{pathValue.replace(/\\\\/g, "/")}}`;
      }}
      return pathValue.replace(/\\\\/g, "/");
    }}

    function fileName(pathValue) {{
      return pathValue.split(/[\\\\/]/).pop();
    }}

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    function escapeAttribute(value) {{
      return escapeHtml(value).replace(/'/g, "&#39;");
    }}

    const panel = document.getElementById("panel");
    const lines = [
      ["Model", summary.output || ""],
      ["Buildings", summary.building_count ?? 0],
      ["Vertices", summary.vertices ?? 0],
      ["Faces", summary.faces ?? 0],
      ["Min elevation", `${{Number(summary.min_elevation_m ?? 0).toFixed(2)}} m`],
      ["Terrain resolution", `${{summary.terrain_resolution_m ?? 0}} m`],
    ];
    const outputs = Object.entries(summary.outputs || {{}})
      .filter(([key]) => key === "obj" || key === "glb" || key === "gltf" || key.endsWith("_stl"));
    const rowsHtml = lines
      .map(([label, value]) => `<dt>${{escapeHtml(label)}}</dt><dd>${{escapeHtml(value)}}</dd>`)
      .join("");
    const outputsHtml = outputs.length
      ? `<div class="outputs"><strong>Output files</strong><ul>${{
          outputs
            .map(([, pathValue]) => `<li><a href="${{escapeAttribute(toFileHref(String(pathValue)))}}">${{escapeHtml(fileName(String(pathValue)))}}</a></li>`)
            .join("")
        }}</ul></div>`
      : "";
    panel.innerHTML = `<h2>Preview Summary</h2><dl>${{rowsHtml}}</dl>${{outputsHtml}}`;

    window.addEventListener("resize", () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    function animate() {{
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }}
    animate();
  </script>
</body>
</html>
"""
    preview_path.write_text(html, encoding="utf-8")
    return preview_path
