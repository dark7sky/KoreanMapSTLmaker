import json
import base64
from pathlib import Path
from typing import Any

import trimesh


def export_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mesh.is_empty:
        raise ValueError("Cannot export an empty mesh.")
    mesh.export(path)


def export_summary(summary: dict[str, Any], out_path: Path) -> Path:
    summary_path = out_path.with_name(f"{out_path.stem}_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def export_preview_html(stl_path: Path, summary: dict[str, Any]) -> Path:
    preview_path = stl_path.with_name(f"{stl_path.stem}_preview.html")
    stl_base64 = base64.b64encode(stl_path.read_bytes()).decode("ascii")
    summary_json = json.dumps(summary, indent=2)
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
      white-space: pre-wrap;
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

    document.getElementById("panel").textContent =
      `Model: ${{summary.output}}\\n` +
      `Buildings: ${{summary.building_count}}\\n` +
      `Vertices: ${{summary.vertices}}\\n` +
      `Faces: ${{summary.faces}}\\n` +
      `Min elevation: ${{summary.min_elevation_m.toFixed(2)}} m\\n` +
      `Terrain resolution: ${{summary.terrain_resolution_m}} m`;

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
