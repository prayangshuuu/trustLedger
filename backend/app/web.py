"""Serves the built lender dashboard (apps/dashboard/dist) from the API, so one Heroku app hosts both.

API routes are registered first and always win. The fallback below only answers GET/HEAD for files that
exist in the build, the docs site under /docs, and the dashboard's client-side routes; everything else
is a JSON 404 as before.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# Keep in sync with the <Route> paths in apps/dashboard/src/App.tsx.
SPA_ROUTES = ("distribution", "fairness", "map", "feed", "applicant", "reports")


def mount_dashboard(application: FastAPI, dist: Path) -> bool:
    """Attach the dashboard catch-all if a build exists. Returns whether it was mounted."""
    dist = dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        return False

    def no_cache(path: Path) -> FileResponse:
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    @application.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def dashboard(full_path: str) -> FileResponse:
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_relative_to(dist):
            if candidate.is_file():
                immutable = full_path.startswith("assets/")  # Vite hashes these file names
                headers = (
                    {"Cache-Control": "public, max-age=31536000, immutable"} if immutable else {}
                )
                return FileResponse(candidate, headers=headers)
            if candidate.is_dir() and (candidate / "index.html").is_file():
                return no_cache(candidate / "index.html")  # /docs -> docs/index.html
        first = full_path.split("/", 1)[0]
        if full_path == "" or first in SPA_ROUTES:
            return no_cache(index)
        raise HTTPException(status_code=404, detail="Not Found")

    return True
