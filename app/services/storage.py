import uuid
from pathlib import Path

from app.core.config import settings


def save_upload(claim_id: int, filename: str, content: bytes) -> Path:
    claim_dir = settings.storage_dir / str(claim_id)
    claim_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = claim_dir / safe_name
    dest.write_bytes(content)
    return dest


def read_file(path: str) -> bytes:
    return Path(path).read_bytes()
