import os
from pathlib import Path
from tempfile import gettempdir
import shutil
import pytest
from pyontutils.core import log as _log

log = _log.getChild('test')

temp_path = Path(gettempdir(), f'.pyontutils-testing-base-{os.getpid()}')
temp_path_ap = temp_path.as_posix()


def ensure_temp_path():
    if temp_path.exists():
        shutil.rmtree(temp_path)

    temp_path.mkdir()


SKIP_NETWORK = ('SKIP_NETWORK' in os.environ or
                'FEATURES' in os.environ and 'network-sandbox' in os.environ['FEATURES'])
skipif_no_net = pytest.mark.skipif(SKIP_NETWORK, reason='Skipping due to network requirement')
