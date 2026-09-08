"""Helper for turning an absolute on-disk path (inside settings.data_dir)
into a URL the frontend can load, served by the /media StaticFiles mount
registered in main.py.
"""
import os

from .config import settings


def media_url(abs_path: str | None) -> str:
    if not abs_path:
        return ""
    try:
        rel = os.path.relpath(abs_path, settings.data_dir)
    except ValueError:
        return ""
    return f"/media/{rel}".replace(os.sep, "/")
