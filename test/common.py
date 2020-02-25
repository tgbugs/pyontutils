import os
from pathlib import Path
from tempfile import gettempdir
import pytest

temp_path = Path(gettempdir(), f'.pyontutils-testing-base-{os.getpid()}')
temp_path_ap = temp_path.as_posix()

SKIP_NETWORK = ('SKIP_NETWORK' in os.environ or
                'FEATURES' in os.environ and 'network-sandbox' in os.environ['FEATURES'])
skipif_no_net = pytest.mark.skipif(SKIP_NETWORK, reason='Skipping due to network requirement')
