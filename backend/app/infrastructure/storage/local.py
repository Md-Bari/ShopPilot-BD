from pathlib import Path


class LocalFileStorage:
    """Stores uploads on local disk (a Docker volume). Swap for S3-compatible storage later."""

    def __init__(self, root: str, url_prefix: str):
        self.root = Path(root)
        self.url_prefix = url_prefix.rstrip("/")

    def save(self, *, folder: str, filename: str, data: bytes) -> str:
        target_dir = self.root / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / filename).write_bytes(data)
        return f"{folder}/{filename}"

    def delete(self, path: str) -> None:
        target = (self.root / path).resolve()
        if self.root.resolve() in target.parents and target.exists():
            target.unlink()

    def url_for(self, path: str | None) -> str | None:
        return f"{self.url_prefix}/{path}" if path else None
