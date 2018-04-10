import os
import yaml
from pathlib import Path
from tempfile import gettempdir
from functools import wraps
from pyontutils.utils import TermColors as tc

def get_api_key():
    try: return os.environ['SCICRUNCH_API_KEY']
    except KeyError: return None

def default(value):
    def decorator(function, default_value=value):
        @wraps(function)
        def inner(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (TypeError, KeyError, FileNotFoundError) as e:
                return default_value
        return property(inner)
    return decorator

tempdir = gettempdir()

class DevConfig:
    skip = 'config', 'write', 'ontology_remote_repo', 'v'
    def __init__(self, config_file=Path(__file__).parent / 'devconfig.yaml'):
        self.config_file = config_file

    @property
    def config(self):
        """ Allows changing the config on the fly """
        # TODO more efficient to read once and put watch on the file
        with open(self.config_file.as_posix(), 'rt') as f:  # 3.5/pypy3 can't open Path directly
            config = yaml.load(f)

        return config if config else None

    @property
    def _config(self):
        out = {}  # do it this way to read first
        for name in dir(self):
            if not name.startswith('_') and name not in self.skip:
                thing = getattr(self.__class__, name, None)
                if isinstance(thing, property):
                    out[name] = getattr(self, name)

        return out

    def write(self, file=None):
        if file is None:
            file = (Path(__file__).parent / 'devconfig.yaml').as_posix()

        config = self._config
        if config:
            with open(file, 'wt') as f:
                yaml.dump(config, f, default_flow_style=False)
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

    @default('SciCrunch')
    def ontology_org(self):
        return self.config['ontology_org']

    @default('NIF-Ontology')
    def ontology_repo(self):
        return self.config['ontology_repo']

    @property
    def ontology_remote_repo(self):
        return os.path.join(self.git_remote_base, self.ontology_org, self.ontology_repo)

    @property
    def ontology_local_repo(self):
        try:
            olr = self.config['ontology_local_repo']
            if olr:
                return olr
            else:
                raise ValueError('config entry for ontology_local_repo is empty')
        except (KeyError, ValueError, FileNotFoundError) as e:
            maybe_repo = Path(__file__).parent.parent.parent / self.ontology_repo
            if maybe_repo.exists():
                return str(maybe_repo)
            else:
                print(tc.red('WARNING:'), f'No repository found at {maybe_repo}')  # TODO test for this
                return tempdir

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


devconfig = DevConfig()


