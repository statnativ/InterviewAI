import uuid
from pathlib import Path

from app.config import settings


def save_upload(file_bytes: bytes, filename: str, candidate_id: uuid.UUID) -> Path:
    safe_name = Path(filename).name  # strip any directory components
    candidate_dir = Path(settings.resume_storage_dir) / str(candidate_id)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    dest = candidate_dir / f"{uuid.uuid4()}_{safe_name}"
    dest.write_bytes(file_bytes)
    return dest


def save_interview_audio(file_bytes: bytes, filename: str, session_id: uuid.UUID) -> Path:
    """M4: same unencrypted-local-disk pattern as save_upload above — a deliberate,
    risk-accepted extension of R-006 to interview audio, not a new pattern. See ADR-008."""
    safe_name = Path(filename).name
    session_dir = Path(settings.interview_audio_storage_dir) / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    dest = session_dir / f"{uuid.uuid4()}_{safe_name}"
    dest.write_bytes(file_bytes)
    return dest
