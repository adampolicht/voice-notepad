"""`python -m app`: run the server on HOST/PORT from .env (what the launchers use).

`python -m app --print-port` just prints the configured port, so shell/Swift launchers
can build the URL without duplicating the .env parsing.
"""

from __future__ import annotations

import sys

import uvicorn

from app.config import settings

if __name__ == "__main__":
    if "--print-port" in sys.argv[1:]:
        print(settings.port)
    else:
        uvicorn.run("app.main:app", host=settings.host, port=settings.port)
