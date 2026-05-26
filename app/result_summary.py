from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ResultArtifact:
    label: str
    path: Path
    exists: bool

    @property
    def uri(self) -> str:
        return self.path.resolve().as_uri()


@dataclass(frozen=True)
class BuildResultSummary:
    mesh_quality: dict[str, Any]
    output_files: tuple[ResultArtifact, ...]
    preview: ResultArtifact | None
    stl_download: ResultArtifact | None


def summarize_build_result(summary: Mapping[str, Any] | None) -> BuildResultSummary:
    data = summary or {}
    outputs = data.get("outputs")
    output_files: list[ResultArtifact] = []
    if isinstance(outputs, Mapping):
        for key, raw_path in outputs.items():
            artifact = _artifact(str(key), raw_path)
            if artifact is not None:
                output_files.append(artifact)

    preview = _artifact("preview", data.get("preview"))
    stl_download = _stl_artifact(data, output_files)
    mesh_quality = data.get("mesh_quality")
    if not isinstance(mesh_quality, dict):
        mesh_quality = {}
    return BuildResultSummary(
        mesh_quality=mesh_quality,
        output_files=tuple(output_files),
        preview=preview,
        stl_download=stl_download if stl_download is not None and stl_download.exists else None,
    )


def _stl_artifact(data: Mapping[str, Any], output_files: list[ResultArtifact]) -> ResultArtifact | None:
    outputs = data.get("outputs")
    if isinstance(outputs, Mapping):
        stl = _artifact("stl", outputs.get("stl"))
        if stl is not None:
            return stl
    output_value = data.get("output")
    output = _artifact("output", output_value)
    if output is not None and output.path.suffix.lower() == ".stl":
        return output
    for artifact in output_files:
        if artifact.path.suffix.lower() == ".stl":
            return artifact
    return None


def _artifact(label: str, raw_path: Any) -> ResultArtifact | None:
    if raw_path is None:
        return None
    text = str(raw_path).strip()
    if not text:
        return None
    path = Path(text)
    return ResultArtifact(label=label, path=path, exists=path.exists())
