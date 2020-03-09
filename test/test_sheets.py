import pprint
import unittest
import orthauth as oa
from pyontutils import sheets

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
                           e.args[0].startswith('No file exists'))

def value_nova(e): return (isinstance(e, ValueError) and
                           e.args and
                           e.args[0].startswith('No value found'))

def value_val(e): return (isinstance(e, ValueError) and
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
    except BaseException as e:
        if not expect(e):
            raise e


class TestGetOauthService(unittest.TestCase):
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
                except BaseException as e:
                    if (cname, sname) == ('user_config_ok', 'secrets_null'):
                        raise e

                    bads.append((cname, sname, e))

                try:
                    expect = (expect
                              if cname in keep_expect or sname in keep_expect else
                              type_scopes)
                    do_test(expect, None)  # FIXME some others come first
                except BaseException as e:
                    bads.append((cname, sname, 'SCOPES=None', e))

        assert not bads, pprint.pformat(bads)
