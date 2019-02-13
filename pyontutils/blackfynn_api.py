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
SPARC Consortium is at
https://app.blackfynn.io/N:organization:618e8dd9-f8d2-4dc4-9abb-c6aaab2e78a0/profile/

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
from joblib import Parallel, delayed
from blackfynn import Blackfynn, Collection, DataPackage, Organization
from blackfynn.models import BaseCollection
from blackfynn import base as bfb
from pyontutils.utils import Async, deferred, async_getter, chunk_list
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


def inner(thing):
    """ one level """
    if isinstance(thing, DataPackage):
        return thing,
    else:
        return list(thing)

def outer(dataset):
    return [e for t in Async()(deferred(inner)(thing) for thing in dataset) for e in t]

def heh(c):
    #print(c)
    return list(c)

def asynchelper(chunk):
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    wat = async_getter(heh, [(c,) for c in chunk]) 
    print('chunkdone')
    return [e for t in wat for e in t]

def get_packages(package_or_collection, path):
    """ flatten collections into packages """
    if isinstance(package_or_collection, Collection):
        npath = path / package_or_collection.name
        yield package_or_collection, path
        for npc in package_or_collection:
            yield from get_packages(npc, npath)
    else:
        print(path, package_or_collection)
        yield package_or_collection, path


def get_packages_(dataset):
    """ flatten collections into packages """

    hrm1 = outer(dataset)
    print(len(dataset))
    print(len(hrm1))
    hrm2 = outer(hrm1)
    print(len(hrm2))
    chunks = chunk_list([c for c in hrm2 if isinstance(c, Collection)], 1000)
    #wat = async_getter(heh, [(c,) for c in hrm2 if isinstance(c, Collection)][:1000]) 
    Parallel(n_jobs=8, backend="threading")(delayed(asynchelper)(chunk) for chunk in chunks)
    embed()
    return
    if collector is None:
        collector = []
        
    files = []
    folders = []
    if isinstance(package_or_collection, Collection):
        list(package_or_collection)
    else:
        files.append(package_or_collection, path)

def blah():
    if isinstance(package_or_collection, Collection):
        [t for npc in package_or_collection
         for t in (list(npc) if isinstance(npc, Collection) else (npc,))]
    else:
        yield package_or_collection, path

def pkgs_breadth(package_or_collection, path):
    print(path)
    if isinstance(package_or_collection, Collection):
        npath = path / package_or_collection.name
        to_iter = list(package_or_collection)
        #print(to_iter)
        coll = []
        for thing in Async()(deferred(get_packages)(npc, npath) for npc in to_iter):
            coll.append(thing)
            #yield from thing

        yield coll
        Async()(deferred(list)(t) for t in thing)
        #yield (list(c) for c in coll)
        #[v for h in hrm for v in h]
        
        #for npc in package_or_collection:
            #for poc_p in 
            #yield from get_packages(npc, npath)
    else:
        yield package_or_collection, path

def pkgs_depth(mess):
    hrm = Async()(deferred(list)(t) for t in mess)

def gfiles(p, f):
    # print(p.name)
    # the fanout is horrible ...
    return f, p.files

def fetch_file(file, file_path):
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    print('fetching', file)
    file.download(file_path)

def make_folder_and_meta(parent_path, collection):
    folder_path = parent_path / collection.name
    meta_file = folder_path / collection.id
    folder_path.mkdir(parents=True, exist_ok=True)
    meta_file.touch()

def cons():
    bf = Blackfynn(api_token=devconfig.secrets('blackfynn-sparc-key'),
                   api_secret=devconfig.secrets('blackfynn-sparc-secret'))
    project_name = bf.context.name
    project_path = local_storage_prefix / project_name
    ds = bf.datasets()
    useful = {d.id:d for d in ds}  # don't worry, I've made this mistake too
    small = useful['N:dataset:f3ccf58a-7789-4280-836e-ad9d84ee2082']
    big = useful['N:dataset:ec2e13ae-c42a-4606-b25b-ad4af90c01bb']
    #datasets = [d for d in ds if d != big]
    datasets = small,
    #embed()
    #get_packages_(big)
    #return
    packages = []
    collections = [(bf.context, local_storage_prefix)]
    for dataset in datasets:
        dataset_name = dataset.name
        ds_path = project_path / dataset_name
        collections.append((dataset, local_storage_prefix / project_name))
        for package_or_collection in dataset:
            pocs = list(get_packages(package_or_collection, ds_path))
            packages.extend(((poc, fp) for poc, fp in pocs if isinstance(poc, DataPackage)))
            collections.extend(((poc, fp) for poc, fp in pocs if isinstance(poc, BaseCollection) or isinstance(poc, Organization)))

    bfolders = [make_folder_and_meta(parent_path, collection) for collection, parent_path in collections]  # FIXME duplicates and missing ids
    meta = 'subjects', 'submission', 'submission_spreadsheet', 'dataset_description', 'detaset_description_spreadsheet', 'manifest', 'README'
    meta_subset = [(package, fp) for package, fp in packages if package.name in meta]
    bfiles = {folder_path / make_filename(file):file
              for folder_path, files in
              Async()(deferred(gfiles)(p, f) for p, f in meta_subset)
              for file in files}

    # beware that this will send as many requests as it can as fast as it can
    # which is not the friendliest thing to do to an api
    Async()(deferred(fetch_file)(f, fp) for fp, f in bfiles.items() if not fp.exists())



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
    niftis = [nifti1.load(f.as_posix()) for f in files if '.nii' in f.suffixes]
    mats = [loadmat(f.as_posix()) for f in files if '.mat' in f.suffixes]
    dicoms = [dcmread(f.as_posix()) for f in files if '.dcm' in f.suffixes]  # loaded dicom files
    embed()  # XXX you will drop into an interactive terminal in this scope


def mvp_main():
    bf, files = mvp()
    process_files(bf, files)

def main():
    cons()

if __name__ == '__main__':
    main()
