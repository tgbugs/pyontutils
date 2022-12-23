import re
import unittest
from pathlib import Path
import pytest
from pyontutils.utils import get_working_dir
from nifstd_tools.docs import FixLinks

working_dir = get_working_dir(__file__)
if working_dir is None:
    name = 'pyontutils'
else:
    name = working_dir.name

base = ('/' + name + '/nifstd/test' + '/')
gitbase = 'https://github.com/tgbugs/pyontutils/blob/master/nifstd/test/'


class TestRegex(unittest.TestCase):
    def test_regex(self):
        tomatch = b'[[file:${HOME}/.ssh/config][your ssh config file]]'
        ml = re.match(FixLinks.link_pattern, tomatch)
        assert len(ml.groups()) == 2, ml


@pytest.mark.skipif(working_dir is None, reason='Not in git repo so not testing.')  # FIXME create a temp repo?
class TestFixLinks(unittest.TestCase):
    target = Path(__file__)
    path_nasty_good = (
        (target, '[[file:${HOME}/.ssh/config][your ssh config file]]', '=${HOME}/.ssh/config='),
        (target, '[[file:${HOME}/.ssh/config][~/.ssh/config]]', '=~/.ssh/config='),
        (target, '[[file:${HOME}/.ssh_tmp]]', '=${HOME}/.ssh_tmp='),
        (target, '[[http://example.org/test-1][text\ntext]]', '[[http://example.org/test-1][text text]]'),
        (target, '[[][text-2]]', '[[][text-2]]'),

        (target, '[[file:a-code-file.py][text-3]]', '[[' + gitbase + 'a-code-file.py][text-3]]'),
        (target, '[[./a-code-file.py][text-4]]', '[[' + gitbase + 'a-code-file.py][text-4]]'),
        (target, '[[file:a-ttl-file.ttl][text-5]]', '[[' + gitbase + 'a-ttl-file.ttl][text-5]]'),
        (target, '[[../a-sh-file.sh][text-5.1]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-sh-file.sh][text-5.1]]'),
        (target, '[[../a-ex.ini.example][text-5.2]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-ex.ini.example][text-5.2]]'),
        (target, '[[../a-ex-5.3.ini.example]]', '[[' + gitbase.rsplit('/', 2)[0] + '/a-ex-5.3.ini.example]]'),  # [../a-ex-5.3.ini.example]  # FIXME reasonable, lost, TODO restore

        (target, '[[file:a-docs-file.md][text-6]]', '[[hrefl:/docs' + base + 'a-docs-file.html][text-6]]'),
        (target, '[[./a-docs-file.md][text-7]]', '[[hrefl:/docs' + base + 'a-docs-file.html][text-7]]'),

        (target, '[[./../a-docs-file.md][text-8]]', '[[hrefl:/docs/pyontutils/nifstd/a-docs-file.html][text-8]]'),
        (target, '[[file:../a-docs-file.md][text-9]]', '[[hrefl:/docs/pyontutils/nifstd/a-docs-file.html][text-9]]'),

        (target, '[[file:a-docs-file.md#section][text-10]]', '[[hrefl:/docs' + base + 'a-docs-file.html#section][text-10]]'),
        (target, '[[file:a-docs%20file.md#section][text-11]]', '[[hrefl:/docs' + base + 'a-docs%20file.html#section][text-11]]'),

        #(target, '[[../a-docs-file.md#section][text]]', '[[../a-docs-file.md#section][text]]'),  # FIXME warn error or what?
    )

    def test_fix_links(self):
        bads = ['\n' + '\n'.join((good, actual.decode()))
                for path, nasty, good in self.path_nasty_good
                for actual in (FixLinks(path, False)(nasty.encode()),)
                if actual.decode() != good]
        lb = '\n\n'
        assert not bads, f'{f"{lb}".join(bads)}'
