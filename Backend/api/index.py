"""Vercel serverless entrypoint.

Vercel's Python runtime looks for an ASGI app named `app` in this file and
builds the whole FastAPI application into a single function. Everything else
lives in app/ exactly as it does when running locally with uvicorn.
"""

import pathlib
import sys

# When Vercel invokes this file the project root is not necessarily on the
# import path, so `import app...` would fail.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app

__all__ = ["app"]
