import os
import pprint
import unittest
import pytest
import orthauth as oa
from pyontutils import sheets
from pyontutils.config import auth

# TODO move some of this to orthauth directly
# no SCOPES
# bad path
# no path/path is null

auth_config = {'auth-variables': {'google-api-store-file': None,
                                  'google-api-store-file-readonly': None,}}

user_configs = dict(
    user_config_ok = {'auth-variables': {'google-api-store-file':
                                         {'path': 'google api store-file'},
                                         'google-api-store-file-readonly':
                                         {'path': 'google api store-file-readonly'},},
                      'auth-stores': {'runtime': True}},
    user_config_null = {'auth-variables': {'google-api-store-file': None,
                                           'google-api-store-file-readonly': None,},
                        'auth-stores': {'runtime': True}},
    user_config_empty = {},
    user_config_no_vars = {'auth-variables': {},
                           'auth-stores': {'runtime': True}},
)

secrets =dict(
    secrets_ok = {'google': {'api': {'store-file-readonly': '/dev/null/some-path'}}},
    secrets_not_rel = {'google': {'api': {'store-file-readonly': 'some-path'}}},
    secrets_null = {'google': {'api': {'store-file-readonly': None}}},
    secrets_empty = {},
    secrets_no_path = {'google': {'api': {}}},
)


def key_creds(e): return (isinstance(e, KeyError) and
                          e.args and
                          e.args[0] == 'google-api-creds-file')

def type_scopes(e): return (isinstance(e, TypeError) and
                            e.args and
                            e.args[0].startswith('SCOPES has not been set'))

def value_nofi(e): return (isinstance(e, ValueError) and
                           e.args and
                           e.args[0].startswith('The file (or absense of file)'))

def value_nova(e): return (isinstance(e, oa.exceptions.SecretError) and
                           e.args and
                           e.args[0].startswith('This secret path'))

def value_val(e): return (isinstance(e, oa.exceptions.SecretError) and
                          #not breakpoint() and
                          e.args and
                          e.args[0].startswith('Value of secret at'))

def nbpe(e): return isinstance(e, oa.exceptions.NoBasePathError)

def default(e): return False


errors = {
    ('user_config_ok', 'secrets_ok'):           key_creds,
    ('user_config_ok', 'secrets_not_rel'):      nbpe,
    ('user_config_ok', 'secrets_null'):         value_val,
    ('user_config_ok', 'secrets_empty'):        value_nova,
    ('user_config_ok', 'secrets_no_path'):      value_nova,
    ('user_config_null', 'secrets_ok'):         value_nofi,
    ('user_config_null', 'secrets_not_rel'):    value_nofi,
    ('user_config_null', 'secrets_null'):       value_nofi,
    ('user_config_null', 'secrets_empty'):      value_nofi,
    ('user_config_null', 'secrets_no_path'):    value_nofi,
    ('user_config_empty', 'secrets_ok'):        value_nofi,
    ('user_config_empty', 'secrets_not_rel'):   value_nofi,
    ('user_config_empty', 'secrets_null'):      value_nofi,
    ('user_config_empty', 'secrets_empty'):     value_nofi,
    ('user_config_empty', 'secrets_no_path'):   value_nofi,
    ('user_config_no_vars', 'secrets_ok'):      value_nofi,
    ('user_config_no_vars', 'secrets_not_rel'): value_nofi,
    ('user_config_no_vars', 'secrets_null'):    value_nofi,
    ('user_config_no_vars', 'secrets_empty'):   value_nofi,
    ('user_config_no_vars', 'secrets_no_path'): value_nofi,
}


def do_test(expect, SCOPES='https://www.googleapis.com/auth/spreadsheets.readonly'):
    try:
        s = sheets._get_oauth_service(SCOPES=SCOPES)
    except Exception as e:
        if not expect(e):
            raise e


class TestGetOauthService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__auth = sheets.auth

    @classmethod
    def tearDownClass(cls):
        sheets.auth = cls.__auth

    def test(self):
        keep_expect = ('user_config_no_vars',
                       'user_config_empty',
                       'user_config_null',
                       'secrets_not_rel',
                       'secrets_empty',
                       'secrets_no_path',
                       'secrets_null',
        )
        bads = []
        for cname, cblob in user_configs.items():
            for sname, sblob in secrets.items():
                sheets.auth = oa.AuthConfig.runtimeConfig(auth_config, cblob, sblob)
                expect = errors[cname, sname]
                try:
                    do_test(expect)
                except Exception as e:
                    if (cname, sname) == ('user_config_ok', 'secrets_null'):
                        raise e

                    bads.append((cname, sname, e))

                try:
                    expect = (expect
                              if cname in keep_expect or sname in keep_expect else
                              type_scopes)
                    do_test(expect, None)  # FIXME some others come first
                except Exception as e:
                    bads.append((cname, sname, 'SCOPES=None', e))

        assert not bads, pprint.pformat(bads)


class SheetToTest(sheets.Sheet):

    name = 'pyontutils-test'
    sheet_name = 'tests'
    index_columns = 'id',
    fetch_grid = True


@pytest.mark.skipif(auth.get_path('google-api-store-file-readonly') is None and
                    auth.get_path('google-api-service-account-file') is None,
                    reason='Google API creds required.')
class TestSheets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # ensure we always start from a sane state
        base_sheet = SheetToTest(readonly=False)
        start = [['id', 'name', 'other'],
                 ['a', '', ''],
                 ['b', '', ''],
                 ['c', '', ''],
                 ['d', '', ''],]
        base_sheet.update(start)
        base_sheet.commit()

        # new object to avoid any potential lingering state
        # (we would catch this in the tests below)
        cls.base_sheet = SheetToTest(readonly=False)
        assert cls.base_sheet.values == start
        cls.base_sheet_ro = SheetToTest()

    @classmethod
    def tearDownClass(cls):
        # FIXME shrinks should deal with this themselves
        # but it is not always obvious whether a call to
        # update should enqueue a resize requests
        cls.base_sheet._delete_rest()
        cls.base_sheet.commit()

    def setUp(self):
        self.sheet = SheetToTest(readonly=False, fetch=False)
        self.sheet_ro = SheetToTest(fetch=False)

        # keep the fetch count down at risk of desync
        self.sheet._fetch_from_other_sheet(self.base_sheet)
        self.sheet_ro._fetch_from_other_sheet(self.base_sheet_ro)

    def test_fromUrl(self):
        NewSheet = sheets.Sheet.fromUrl(self.sheet._uri_human() + '#gid=0')
        ns = NewSheet()
        assert ns.values == self.sheet_ro.values

    def test_fetch_return(self):
        a, b, c, d, e = self.sheet.fetch()
        a, b, c, d, e = self.sheet.fetch(fetch_meta=False)

    def test_range(self):
        """ test the corners """
        #rcs = ((0, 0), (0, -1), (-1, 0), (-1, -1))  # asymmetry is hard
        rcs = ((0, 0, 'A1'), (-1, -1, 'C5'))

        assert self.sheet.cell_object(0, -1).range != self.sheet.cell_object(-1, -1).range

        for r, c, e in rcs:
            cell = self.sheet.cell_object(r, c)
            cell_range = cell._range

            _, rr = cell.row.range.split('!', 1)
            rf, rl = rr.split(':', 1)
            row_range = rf if not r else rl

            _, cr = cell.column.range.split('!', 1)
            cf, cl = cr.split(':', 1)
            column_range = cf if not c else cl

            assert cell_range == row_range == e, (r, c)
            assert cell_range == column_range == e, (r, c)

    def test_update(self):
        row = self.sheet.row_object(1)

        row.name().value = 'hello there'
        self.sheet.commit()
        self.sheet_ro.fetch(fetch_meta=False)
        tv1 = self.sheet_ro.values
        assert self.sheet.values == tv1

        row.name().value = ''
        self.sheet.commit()
        self.sheet_ro.fetch(fetch_meta=False)
        tv2 = self.sheet_ro.values
        assert self.sheet.values == tv2
        assert tv1 != tv2

    def test_1_upsert_up(self):
        row = ['a', 'lol', 'nope']
        assert row not in self.sheet.values
        row_object, _ = self.sheet._row_from_index(row=row)
        original_values = list(row_object.values)  # dupe the list since we mutate values
        assert original_values != row

        try:
            self.sheet.upsert(row)
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1
        finally:
            self.sheet.upsert(original_values)
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1

    def test_delete(self):
        row = ['d', '', '']
        assert row in self.sheet.values
        row_object, _ = self.sheet._row_from_index(row=row)

        try:
            self.sheet.delete(row)
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1
            assert row not in tv1
        finally:
            if row not in tv1:
                self.sheet.insert(row)  # FIXME can only append not insert back to previous location ...
                self.sheet.commit()
                self.sheet_ro.fetch(fetch_meta=False)
                tv1 = self.sheet_ro.values
                assert self.sheet.values == tv1
                assert row in tv1

    def test_1_upsert_in(self):
        row = ['e', 'lol', 'nope']
        assert row not in self.sheet.values
        self.sheet.upsert(row)
        self.sheet.commit()
        self.sheet_ro.fetch(fetch_meta=False)
        tv1 = self.sheet_ro.values
        try:
            assert self.sheet.values == tv1
        finally:
            if row in self.sheet.values:
                self.sheet.delete(row)
                self.sheet.commit()
                self.sheet_ro.fetch(fetch_meta=False)
                tv1 = self.sheet_ro.values
                assert self.sheet.values == tv1

    def test_append(self):
        """ make sure that you are on the version of the
            test sheet that doesn't have extra rows """
        rows = dict(
            row1 = ['f', 'append', '1'],
            row2 = ['g', 'append', '2'],
            row3 = ['h', 'append', '3'],)
        for row in rows.values():
            assert row not in self.sheet.values
            self.sheet._appendRow(row)

        self.sheet.commit()
        self.sheet_ro.fetch(fetch_meta=False)
        tv1 = self.sheet_ro.values
        try:
            assert self.sheet.values == tv1
        finally:
            to_delete = []
            for row in rows.values():
                if row in self.sheet.values:
                    to_delete.append(row)

            if to_delete:
                self.sheet.delete(*to_delete)
                self.sheet.commit()
                self.sheet_ro.fetch(fetch_meta=False)
                tv1 = self.sheet_ro.values
                assert self.sheet.values == tv1

    @pytest.mark.skip('TODO')
    def test_stash(self):
        # create another instance of the sheet
        # update using that instance
        # fetch to make sure stashing works as expected
        pass

    def test_set_values_update(self):
        ovalues = [list(l) for l in self.sheet.values]  # duh mutation is evil
        _test_value = [[1, 2, 3, 4],
                       [1, 2, 3, 4],
                       [1, 2, 3, 4],
                       [1, 2, 3, 4],]
        # haven't implemented conversion of cell values to strings yet
        test_value = [[str(c) for c in r] for r in _test_value]

        oic = self.sheet.index_columns
        self.sheet.index_columns = tuple()
        self.sheet.update(test_value)  # FIXME vs non-truncating self.sheet.values = test_value
        assert self.sheet._values_less_removed() == test_value
        assert self.sheet.uncommitted()  # FIXME this needs to be run by default every test
        assert ovalues != test_value  # FIXME this needs to be run by default every test
        assert ovalues[0] != test_value[0]

        try:
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1
        finally:
            self.sheet.update(ovalues)
            self.sheet.index_columns = oic
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv2 = self.sheet_ro.values
            # FIXME I suspect this will break due to missing ends
            assert self.sheet.values == tv2
            assert tv2 == ovalues

    def test_set_values_update_more_cols(self):
        ovalues = [list(l) for l in self.sheet.values]  # duh mutation is evil
        _test_value = [[1, 2, 3, 4, 5],  # FIXME these should probably throw errors too
                       [1, 2, 3, 4, 5],  # since they break the primary key assuptions?
                       [1, 2, 3, 4, 5],
                       [1, 2, 3, 4, 5],]
        # haven't implemented conversion of cell values to strings yet
        test_value = [[str(c) for c in r] for r in _test_value]

        oic = self.sheet.index_columns
        self.sheet.index_columns = tuple()
        self.sheet.update(test_value)  # FIXME vs non-truncating self.sheet.values = test_value
        assert self.sheet._values_less_removed() == test_value
        assert self.sheet.uncommitted()  # FIXME this needs to be run by default every test
        assert ovalues != test_value  # FIXME this needs to be run by default every test
        assert ovalues[0] != test_value[0]

        try:
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1
        finally:
            # FIXME need to delete the new rows not just return to the size of the old values
            self.sheet.update(ovalues)
            self.sheet.index_columns = oic
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv2 = self.sheet_ro.values
            # FIXME I suspect this will break due to missing ends
            assert self.sheet.values == tv2
            assert tv2 == ovalues

    def test_set_values_update_more_rows(self):
        ovalues = [list(l) for l in self.sheet.values]  # duh mutation is evil
        _test_value = [[1, 2, 3, 4],  # FIXME these should probably throw errors too
                       [1, 2, 3, 4],  # since they break the primary key assuptions?
                       [1, 2, 3, 4],
                       [1, 2, 3, 4],
                       [2, 2, 3, 4],
                       [3, 2, 3, 4],
                       [4, 2, 3, 4],]
        # haven't implemented conversion of cell values to strings yet
        test_value = [[str(c) for c in r] for r in _test_value]

        oic = self.sheet.index_columns
        self.sheet.index_columns = tuple()
        self.sheet.update(test_value)  # FIXME vs non-truncating self.sheet.values = test_value
        assert self.sheet._values_less_removed() == test_value
        assert self.sheet.uncommitted()  # FIXME this needs to be run by default every test
        assert ovalues != test_value  # FIXME this needs to be run by default every test
        assert ovalues[0] != test_value[0]

        try:
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv1 = self.sheet_ro.values
            assert self.sheet.values == tv1
        finally:
            # FIXME need to delete the new rows not just return to the size of the old values
            self.sheet.update(ovalues)
            self.sheet.index_columns = oic
            self.sheet.commit()
            self.sheet_ro.fetch(fetch_meta=False)
            tv2 = self.sheet_ro.values
            # FIXME I suspect this will break due to missing ends
            assert self.sheet.values == tv2
            assert tv2 == ovalues

    def test_row(self):
        r = self.sheet.row_object(0)
        r.header
        r = r.rowAbove()
        r = r.rowBelow()
        r.cell_object(1).value = 'oops'
        a = r.cells
        b = [c.column for c in r.cells]
        repr((a, b))

    def test_column(self):
        c = self.sheet.column_object(0)
        c.header
        c = c.columnLeft()
        c = c.columnRight()
        c.cell_object(1).value = 'oops'
        a = c.cells
        b = [c.row for c in c.cells]
        repr((a, b))
