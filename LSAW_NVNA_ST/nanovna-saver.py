
from contextlib import suppress

# noinspection PyUnresolvedReferences
with suppress(ImportError):
    # pylint: disable=no-name-in-module,import-error,unused-import
    # pyright: reportMissingImports=false
    import pkg_resources.py2_warn

from NanoVNASaver.__main__ import main

if __name__ == '__main__':
    main()
