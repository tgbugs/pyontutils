"""Accessing files via the blackfynn api

# Install these python packages.
``` bash
pip install blackfynn nibabel pydicom
git clone https://github.com/tgbugs/pyontutils.git
pushd pyontutils
python setup.py develop --user
ontutils devconfig --write
# you can edit ./pyontutils/devconfig.yaml to match your system if needs be
touch ${HOME}/pyontutils-secrets.yaml
chmod 0600 ${HOME}/pyontutils-secrets.yaml
```

# Get a blackfynn api key and api secret
navigate to https://app.blackfynn.io/${blackfynn_organization}/profile/
You have to find your way through the UI if you don't know your org id :/

SPARC MVP is at
https://app.blackfynn.io/N:organization:89dfbdad-a451-4941-ad97-4b8479ed3de4/profile/

add the following lines to your secrets.yaml file from the blackfynn site
you can (and should) save those keys elsewhere as well
```
blackfynn-mvp-key: ${apikey}
blackfynn-mvp-secret: ${apisecret}
```

"""

from pathlib import Path
from nibabel import nifti1
from pydicom import dcmread
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from blackfynn import Blackfynn, Collection
from blackfynn import base as bfb
from pyontutils.utils import Async, deferred
from pyontutils.config import devconfig
from scipy.io import loadmat
from IPython import embed


# CHANGE THIS PATH TO MATCH YOUR SYSTEM
local_storage_prefix = Path('~/files/blackfynn_local/').expanduser()
prefix = 'https://app.blackfynn.io/'
lp = len(prefix)


@property
def patch_session(self):
    """
    Make requests-futures work within threaded/distributed environment.
    """
    if self._session is None:
        self._session = Session()
        self._set_auth(self._token)

        # Enable retries via urllib
        adapter = HTTPAdapter(
            pool_connections=1000,  # wheeee
            pool_maxsize=1000,  # wheeee
            max_retries=Retry(
                total=self.settings.max_request_timeout_retries,
                backoff_factor=.5,
                status_forcelist=[502, 503, 504] # Retriable errors (but not POSTs)
            )
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

    return self._session


# monkey patch to avoid session overflow during async
bfb.ClientSession.session = patch_session


def destructure_uri(uri):
    if not uri.startswith(prefix):
        return None  # TODO less cryptic return value or exception

    suffix = uri[lp:]
    for maybe_id in suffix.split('/'):
        if maybe_id.startswith('N:'):
            yield maybe_id

    'N:organization:89dfbdad-a451-4941-ad97-4b8479ed3de4'
    '/datasets/'
    'N:dataset:bedda0db-c275-4d79-87ce-fc7bf1e11600'
    '/files'


def make_filename(file):
    # we have to do this because the type on the package is unreliable
    # so we have to get it from s3 because that is what will roundtrip
    _, file_name_s3 = file.s3_key.rsplit('/', 1)
    return file_name_s3

def process_package(package, path, doasync=True):
    # packages are the souless shells of files
    # you can retrieve them quickly, but they have no substance

    if not path.exists():
        path.mkdir(parents=True)

    if isinstance(package, Collection):
        npath = path / package.name
        if doasync:  # FIXME recursive async doesn't quite work
            for lst in Async(debug=True)(deferred(pp)(npackage, npath)
                                        for npackage in package):
                yield from lst
        else:
            yield from (process_package(npackage, npath, False)
                        for npackage in package)

    else:
        for file in package.files:
            file_name = make_filename(file)
            print(file_name)
            file_path = path / file_name
            yield file, file_path


def pp(package, path, doasync=True):
    return list(process_package(package, path, doasync))


def get_packages(package_or_collection, path):
    """ flatten collections into packages """
    if isinstance(package_or_collection, Collection):
        npath = path / package_or_collection.name
        for npc in package_or_collection:
            yield from get_packages(npc, npath)
    else:
        yield package_or_collection, path


def gfiles(p, f):
    # print(p.name)
    # the fanout is horrible ...
    return f, p.files

def fetch_file(file, file_path):
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exists_ok=True)

    print('fetching', file)
    file.download(file_path)

def mvp():
    """ In order to be performant for large numbers of packages we have
        to get all the packages first and then async retrieve all the files
    """
    bf = Blackfynn(api_token=devconfig.secrets('blackfynn-mvp-key'),
                    api_secret=devconfig.secrets('blackfynn-mvp-secret'))

    ds = bf.datasets()
    useful = {d.id:d for d in ds}  # don't worry, I've made this mistake too

    project_name = bf.context.name

    helm = useful['N:dataset:bedda0db-c275-4d79-87ce-fc7bf1e11600']
    helmr = useful['N:dataset:d412a972-870c-4b63-9865-8d790065bd43']
    datasets = helm, helmr  # TODO add more datasets here
    packages = []
    for dataset in datasets:
        dataset_name = dataset.name
        ds_path = local_storage_prefix / project_name / dataset_name
        for package_or_collection in dataset:
            packages.extend(get_packages(package_or_collection, ds_path))

    bfiles = {folder_path / make_filename(file):file
              for folder_path, files in
              Async()(deferred(gfiles)(p, f) for p, f in packages)
              for file in files}

    # beware that this will send as many requests as it can as fast as it can
    # which is not the friendliest thing to do to an api
    Async()(deferred(fetch_file)(f, fp) for fp, f in bfiles.items() if not fp.exists())

    return bf, bfiles


def process_files(bf, files):
    ns = [nifti1.load(f.as_posix()) for f in files if '.nii' in f.suffixes]
    ms = [loadmat(f.as_posix()) for f in files if '.mat' in f.suffixes]
    dcs = [dcmread(f.as_posix()) for f in files if '.dcm' in f.suffixes]  # loaded dicom files
    embed()  # XXX you will drop into an interactive terminal in this scope


def main():
    bf, files = mvp()
    process_files(bf, files)

if __name__ == '__main__':
    main()
