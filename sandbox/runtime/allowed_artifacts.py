from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path


SAFE_ARTIFACT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
APPROVED_ARTIFACT_TYPES = {
    ".csv": "csv",
    ".json": "json",
    ".png": "png",
    ".txt": "txt",
}


class ArtifactPolicyError(RuntimeError):
    pass


class ArtifactSizeLimitExceeded(ArtifactPolicyError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Artifact '{filename}' exceeded the reviewed file-size limit.")


class ArtifactCountLimitExceeded(ArtifactPolicyError):
    def __init__(self, max_artifacts: int) -> None:
        super().__init__(f"Execution created more than {max_artifacts} reviewed artifacts.")


@dataclass(frozen=True)
class ReviewedArtifact:
    artifact_id: str
    name: str
    artifact_type: str
    size_bytes: int
    sha256: str
    content_base64: str

    def as_payload(self) -> dict[str, str | int]:
        return asdict(self)


def collect_reviewed_artifacts(
    artifact_root: Path,
    *,
    max_artifacts: int,
    max_bytes: int,
) -> list[ReviewedArtifact]:
    if not artifact_root.exists():
        return []

    reviewed_artifacts: list[ReviewedArtifact] = []
    for path in sorted(artifact_root.iterdir()):
        if not path.is_file():
            continue
        if not SAFE_ARTIFACT_NAME_RE.fullmatch(path.name):
            continue
        artifact_type = APPROVED_ARTIFACT_TYPES.get(path.suffix.lower())
        if artifact_type is None:
            continue
        payload = path.read_bytes()
        if len(payload) > max_bytes:
            raise ArtifactSizeLimitExceeded(path.name)
        digest = hashlib.sha256(payload).hexdigest()
        reviewed_artifacts.append(
            ReviewedArtifact(
                artifact_id=digest[:16],
                name=path.name,
                artifact_type=artifact_type,
                size_bytes=len(payload),
                sha256=digest,
                content_base64=base64.b64encode(payload).decode("ascii"),
            )
        )
        if len(reviewed_artifacts) > max_artifacts:
            raise ArtifactCountLimitExceeded(max_artifacts)
    return reviewed_artifacts
