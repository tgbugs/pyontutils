""" Tests for the various cli programs """

from pyontutils.integration_test_helper import _TestCliBase, Folders


class TestCli(Folders, _TestCliBase):
    commands = (
        ['googapis', '--help'],
        ['graphml-to-ttl', '--help'],
        ['necromancy', '--help'],
        ['ontload', '--help'],
        ['overlaps', '--help'],
        ['qnamefix', '--help'],
        ['scigraph-codegen', '--help'],
        ['scig', '--help'],
        ['ttlfmt', '--help'],
    )
