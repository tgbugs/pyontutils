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
        (Path(__file__), '[[http://example.org/test-1][text\ntext]]', '[[http://example.org/test-1][text text]]'),
        (Path(__file__), '[[][text-2]]', '[[][text-2]]'),

        (Path(__file__), '[[file:a-code-file.py][text-3]]', '[[' + gitbase + 'a-code-file.py][text-3]]'),
        (Path(__file__), '[[./a-code-file.py][text-4]]', '[[' + gitbase + 'a-code-file.py][text-4]]'),
        (Path(__file__), '[[file:a-ttl-file.ttl][text-5]]', '[[' + gitbase + 'a-ttl-file.ttl][text-5]]'),
        (Path(__file__), '[[../a-sh-file.sh][text-5.1]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-sh-file.sh][text-5.1]]'),
        (Path(__file__), '[[../a-ex.ini.example][text-5.2]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-ex.ini.example][text-5.2]]'),
        (Path(__file__), '[[../a-ex-5.3.ini.example]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-ex-5.3.ini.example][../a-ex-5.3.ini.example]]'),

        (Path(__file__), '[[file:a-docs-file.md][text-6]]', '[[hrefl:/docs' + base + 'a-docs-file.html][text-6]]'),
        (Path(__file__), '[[./a-docs-file.md][text-7]]', '[[hrefl:/docs' + base + 'a-docs-file.html][text-7]]'),

        (Path(__file__), '[[./../a-docs-file.md][text-8]]', '[[hrefl:/docs/pyontutils/nifstd/a-docs-file.html][text-8]]'),
        (Path(__file__), '[[file:../a-docs-file.md][text-9]]', '[[hrefl:/docs/pyontutils/nifstd/a-docs-file.html][text-9]]'),

        (Path(__file__), '[[file:a-docs-file.md#section][text-10]]', '[[hrefl:/docs' + base + 'a-docs-file.html#section][text-10]]'),
        (Path(__file__), '[[file:a-docs%20file.md#section][text-11]]', '[[hrefl:/docs' + base + 'a-docs%20file.html#section][text-11]]'),

        #(Path(__file__), '[[../a-docs-file.md#section][text]]', '[[../a-docs-file.md#section][text]]'),  # FIXME warn error or what?
    )

    def test_all(self):
        bads = ['\n' + '\n'.join((good, actual.decode()))
                for path, nasty, good in self.path_nasty_good
                for actual in (FixLinks(path)(nasty.encode()),)
                if actual.decode() != good]
        lb = '\n\n'
        assert not bads, f'{f"{lb}".join(bads)}'
