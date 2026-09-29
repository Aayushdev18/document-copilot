import sys
from pathlib import Path

from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

DIST = ROOT / "frontend" / "dist"
INDEX = DIST / "index.html"
mount_frontend = getattr(app, "frontend", None)
if mount_frontend is not None and DIST.is_dir():
    mount_frontend("/", directory=str(DIST), fallback="index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend(full_path: str) -> FileResponse:
    if not INDEX.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Frontend build is missing.")
    candidate = (DIST / full_path).resolve()
    if full_path and candidate.is_file() and DIST.resolve() in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(INDEX)
