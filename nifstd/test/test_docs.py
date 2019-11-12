import unittest
from pathlib import Path
from pyontutils.utils import get_working_dir
from nifstd_tools.docs import FixLinks

working_dir = get_working_dir(__file__)
if working_dir is None:
    name = 'pyontutils'
else:
    name = working_dir.name

base = ('/' + name + '/nifstd/test' + '/')
gitbase = 'https://github.com/tgbugs/pyontutils/blob/master/nifstd/test/'


class TestFixLinks(unittest.TestCase):
    path_nasty_good = (
        (Path(__file__), '[[http://example.org/test][text\ntext]]', '[[http://example.org/test][text\ntext]]'),
        (Path(__file__), '[[][text]]', '[[][text]]'),

        (Path(__file__), '[[file:a-code-file.py][text]]', '[[' + gitbase + 'a-code-file.py][text]]'),
        (Path(__file__), '[[./a-code-file.py][text]]', '[[' + gitbase + 'a-code-file.py][text]]'),
        (Path(__file__), '[[file:a-ttl-file.ttl][text]]', '[[' + gitbase + 'a-ttl-file.ttl][text]]'),

        (Path(__file__), '[[file:a-docs-file.md][text]]', '[[' + base + 'a-docs-file.html][text]]'),
        (Path(__file__), '[[./a-docs-file.md][text]]', '[[' + base + 'a-docs-file.html][text]]'),

        (Path(__file__), '[[./../a-docs-file.md][text]]', '[[/pyontutils/nifstd/a-docs-file.html][text]]'),
        (Path(__file__), '[[file:../a-docs-file.md][text]]', '[[/pyontutils/nifstd/a-docs-file.html][text]]'),

        (Path(__file__), '[[file:a-docs-file.md#section][text]]', '[[' + base + 'a-docs-file.html#section][text]]'),
        (Path(__file__), '[[file:a-docs%20file.md#section][text]]', '[[' + base + 'a-docs%20file.html#section][text]]'),

        #(Path(__file__), '[[../a-docs-file.md#section][text]]', '[[../a-docs-file.md#section][text]]'),  # FIXME warn error or what?
    )

    def test_all(self):
        bads = ['\n' + '\n'.join((good, actual.decode()))
                for path, nasty, good in self.path_nasty_good
                for actual in (FixLinks(path)(nasty.encode()),)
                if actual.decode() != good]
        lb = '\n\n'
        assert not bads, f'{f"{lb}".join(bads)}'
