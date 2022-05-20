__version_info__ = (0, 1, 3)
__version__ = '.'.join(map(str, __version_info__))


try:
    from .insert_decal_rpa import start, InsertDecalParameter  # noqa: F401
except ImportError:
    pass
