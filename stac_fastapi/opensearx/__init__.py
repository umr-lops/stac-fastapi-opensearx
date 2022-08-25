from importlib.metadata import version

try:
    __version__ = version("stac-fastapi-opensearx")
except Exception:
    __version__ = "999"
