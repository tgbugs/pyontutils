import os
import yaml
from pathlib import Path
from tempfile import gettempdir
from functools import wraps
from pyontutils.utils import TermColors as tc

checkout_ok = 'NIFSTD_CHECKOUT_OK' in os.environ


def get_api_key():
    try: return os.environ['SCICRUNCH_API_KEY']
    except KeyError: return None


class dproperty(property):
    default = None


class dstr(str):
    default = None

    @property
    def isDefault(self):
        return self == self.default


def default(value):
    def decorator(function, default_value=value):
        dv = dstr(default_value)
        dv.default = default_value

        @wraps(function)
        def inner(*args, **kwargs):
            try:
                out = dstr(function(*args, **kwargs))
                out.default = default_value
                return out
            except (TypeError, KeyError, FileNotFoundError) as e:
                return dv

        pinner = dproperty(inner)
        pinner.default = default_value
        return pinner

    return decorator


tempdir = gettempdir()


class DevConfig:
    skip = 'config', 'write', 'ontology_remote_repo', 'v'
    def __init__(self, config_file=Path(__file__).parent / 'devconfig.yaml'):
        self._override = {}
        self.config_file = config_file
        olrd = lambda: Path(self.git_local_base, self.ontology_repo).as_posix()
        self.__class__.ontology_local_repo.default = olrd

    @property
    def config(self):
        """ Allows changing the config on the fly """
        # TODO more efficient to read once and put watch on the file
        with open(self.config_file.as_posix(), 'rt') as f:  # 3.5/pypy3 can't open Path directly
            config = {k:self._override[k] if
                      k in self._override else
                      v for k, v in yaml.load(f).items()}

        return config if config else None

    @property
    def _config(self):
        # FIXME make it clear that this is read only...
        out = {}  # do it this way to read first
        for name in dir(self):
            if not name.startswith('_') and name not in self.skip:
                thing = getattr(self.__class__, name, None)
                if isinstance(thing, property):
                    if name in self._override:
                        out[name] = self._override[name]
                    else:
                        out[name] = getattr(self, name)

        return out

    def write(self, file=None):
        if file is None:
            file = (Path(__file__).parent / 'devconfig.yaml').as_posix()

        config = {k:str(v) for k, v in self._config.items()}

        if config:
            with open(file, 'wt') as f:
                yaml.dump(config, f, default_flow_style=False)
            if self._override:
                self._override = {}
        else:
            raise ValueError('devconfig is empty?!')

        return file

    def _colluser(self, path):
        path = Path(path)
        prefix = path.home()
        return '~' + path.as_posix().strip(prefix.as_posix())

    @default((Path(__file__).parent.parent / 'scigraph' / 'nifstd_curie_map.yaml').as_posix())
    def curies(self):
        return self.config['curies']

    @default((Path(__file__).parent.parent / 'patches' / 'patches.yaml').as_posix())
    def patch_config(self):
        return self.config['patch_config']

    @default('https://github.com')
    def git_remote_base(self):
        return self.config['git_remote_base']

    @default(tempdir)
    def git_local_base(self):
        return os.path.expanduser(self.config['git_local_base'])

    @git_local_base.setter
    def git_local_base(self, value):
        if isinstance(value, Path):
            value = value.as_posix()
        self._override['git_local_base'] = value
        self.write(self.config_file.as_posix())

    @default('SciCrunch')
    def ontology_org(self):
        return self.config['ontology_org']

    @default('NIF-Ontology')
    def ontology_repo(self):
        return self.config['ontology_repo']

    @property
    def ontology_remote_repo(self):
        return os.path.join(self.git_remote_base, self.ontology_org, self.ontology_repo)

    @dproperty
    def ontology_local_repo(self):
        def add_default(default=self.__class__.ontology_local_repo.default()):
            out = dstr(default)
            out.default = default
            return out

        try:
            olr = Path(self.config['ontology_local_repo']).resolve()
            if olr:
                if olr == self._ontology_local_repo:
                    return add_default(olr)
                else:
                    return add_default(self._ontology_local_repo.as_posix())
            else:
                raise ValueError('config entry for ontology_local_repo is empty')
        except (KeyError, ValueError, FileNotFoundError) as e:
            return add_default(self._ontology_local_repo) if self._ontology_local_repo else add_default()

    @property
    def _maybe_repo(self):
        return Path(self.git_local_base, self.ontology_repo).absolute()

    @property
    def _ontology_local_repo(self):
        try:
            stated_repo = Path(self.config['ontology_local_repo'])
        except FileNotFoundError:
            stated_repo = Path('/dev/null/hahaha')

        maybe_repo = self._maybe_repo
        if stated_repo.exists():
            return stated_repo
        elif maybe_repo.exists():
            return maybe_repo
        else:
            maybe_start = Path(__file__).parent.parent.parent.absolute()
            maybe_base = maybe_start
            fsroot = Path('/')
            while maybe_base != fsroot:
                maybe_repo = maybe_base / self.ontology_repo
                if maybe_repo.exists():
                    print(tc.blue('INFO:'), f'Ontology repository found at {maybe_repo}')
                    return maybe_repo
                else:
                    maybe_base = maybe_base.parent
            else:
                print(tc.red('WARNING:'),
                      f'No repository found in any parent directory of {maybe_start}')

        return Path('/dev/null')  # seems reaonsable ...

    @default('localhost')
    def _scigraph_host(self):
        return self.config['scigraph_host']

    @default(9000)
    def _scigraph_port(self):
        port = self.config['scigraph_port']
        if port is None:
            return ''
        elif port == 80:
            return ''
        else:
            return port

    @default('http://localhost:9000/scigraph')
    def scigraph_api(self):
        return self.config['scigraph_api']

    @scigraph_api.setter
    def scigraph_api(self, value):
        self._override['scigraph_api'] = value
        self.write(self.config_file.as_posix())

    @default((Path(__file__).parent.parent / 'scigraph' / 'graphload.yaml').as_posix())
    def scigraph_graphload(self):
        return self.config['scigraph_graphload']

    @default((Path(__file__).parent.parent / 'scigraph' / 'services.yaml').as_posix())
    def scigraph_services(self):
        return self.config['scigraph_services']

    @default((Path(__file__).parent.parent / 'scigraph' / 'start.sh').as_posix())
    def scigraph_start(self):
        return self.config['scigraph_start']

    @default((Path(__file__).parent.parent / 'scigraph' / 'stop.sh').as_posix())
    def scigraph_stop(self):
        return self.config['scigraph_stop']

    @default((Path(__file__).parent.parent / 'scigraph' / 'scigraph-services.service').as_posix())
    def scigraph_systemd(self):
        return self.config['scigraph_systemd']

    @default((Path(__file__).parent.parent / 'scigraph' / 'scigraph-services.conf').as_posix())
    def scigraph_java(self):
        return self.config['scigraph_java']

    @default('/tmp')
    def zip_location(self):
        return self.config['zip_location']

    def __repr__(self):
        return (f'DevConfig {self.config_file}\n' +
                '\n'.join(f'{k:<20} {v}'
                          for k, v in {k:getattr(self, k)
                                       for k in dir(self) if
                                       not k.startswith('_') and
                                       k not in ('config', 'write', 'config_file') and
                                       isinstance(getattr(self.__class__, k), property)}.items()))


devconfig = DevConfig()


def bootstrap_config():
    if not devconfig.config_file.exists():
        # scigraph api
        maybe_key = get_api_key()
        if maybe_key:
            from pyontutils.scigraph_client import BASEPATH
            devconfig.scigraph_api = BASEPATH
        else:
            devconfig.scigraph_api = devconfig.scigraph_api.default

        # ontology repo
        p1 = Path(__file__).resolve().absolute().parent.parent.parent
        p2 = Path(devconfig.git_local_base).resolve().absolute()
        print(p1, p2)
        if (p1 / devconfig.ontology_repo).exists():
            if p1 != p2:
                devconfig.git_local_base = p1
    else:
        print('config already exists at', devconfig.config_file)


def main():
    from IPython import embed
    print(repr(devconfig))

if __name__ == '__main__':
    main()
