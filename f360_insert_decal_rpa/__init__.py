__version_info__ = (0, 2, 1)
__version__ = '.'.join(map(str, __version_info__))


try:
    from .insert_decal_rpa import start, InsertDecalParameter, FALLBACK_MODE  # noqa: F401
except ImportError:
    pass
