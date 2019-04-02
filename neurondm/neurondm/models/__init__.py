import pkgutil
from pathlib import Path

# __path__ fails in nosetests for reasons I do not understand
thispath = [Path(__file__).parent.as_posix()]
__all__ = [mod for _, mod, is_pkg in pkgutil.walk_packages(thispath)]
