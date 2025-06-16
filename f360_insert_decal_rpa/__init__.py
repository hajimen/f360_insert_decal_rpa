__version_info__ = (0, 3, 1)
__version__ = '.'.join(map(str, __version_info__))


FALLBACK_MODE = False


try:
    from .insert_decal_rpa2 import start_batch, InsertDecalParameter, start  # noqa: F401
except ImportError:
    pass
