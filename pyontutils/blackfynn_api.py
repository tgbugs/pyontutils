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

import io
import os
import asyncio
from pathlib import PosixPath
from nibabel import nifti1
from pydicom import dcmread
import yaml
import xattr
import sqlite3
import requests
from requests import Session
from requests.exceptions import HTTPError, ConnectionError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from joblib import Parallel, delayed
from blackfynn import Blackfynn, Collection, DataPackage, Organization, File
from blackfynn.models import BaseCollection
from blackfynn import base as bfb
from pyontutils.utils import Async, deferred, async_getter, chunk_list
from pyontutils.config import devconfig
from scipy.io import loadmat
from IPython import embed


class Path(PosixPath):
    """ pathlib Path augmented with xattr support """

    def setxattr(self, key, value, namespace=xattr.NS_USER):
        str_value = str(value)
        xattr.set(self.as_posix(), key, str_value, namespace=namespace)

    def setxattrs(self, xattr_dict, namespace=xattr.NS_USER):
        for k, v in xattr_dict.items():
            self.setxattr(k, v, namespace=namespace)

    def getxattr(self, key, namespace=xattr.NS_USER):
        return xattr.get(self.as_posix(), key, namespace=namespace).decode()

    def xattrs(self, namespace=xattr.NS_USER):
        return {k.decode():v.decode() for k, v in xattr.get_all(self.as_posix(), namespace=namespace)}


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


def download(self, destination):
    """ remove prefix functionality since there are filenames without extensions ... """
    if self.type=="DirectoryViewerData":
        raise NotImplementedError("Downloading S3 directories is currently not supported")

    if os.path.isdir(destination):
        # destination dir
        f_local = os.path.join(destination, os.path.basename(self.s3_key))
    else:
        # exact location
        f_local = destination

    r = requests.get(self.url, stream=True)
    with io.open(f_local, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: f.write(chunk)

    # set local path
    self.local_path = f_local

    return f_local

# monkey patch File.download to
File.download = download


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

def gfiles(package, path):
    # print(p.name)
    # the fanout is horrible ...
    while True:
        try:
            return path, package.files
        except HTTPError as e:
            print(e)
            asyncio.sleep(2)

def unlink_fakes(attrs, fake_paths, metastore):
    for fpath in fake_paths:
        fattrs = {k:v for k, v in fpath.xattrs().items() if k != 'bf.error'}
        if fattrs == attrs:
            fpath.unlink()
            metastore.remove(fpath)
        else:
            print('WARNING: fake xattrs and real xattrs do not match!', attrs, fattrs)

def make_file_xattrs(file):
    return {
        'bf.id':file.pkg_id,
        'bf.file_id':file.id,
        'bf.size':file.size,
        'bf.checksum':'',  # TODO
        # 'bf.old_id': '',  # TODO does this work? also naming previous_id, old_version_id etc...
    }

def fetch_file(file_path, file, metastore, limit=False):
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    fake_paths = list(file_path.parent.glob(file_path.name + '.fake*'))

    if file_path.exists():
        print('already have', file_path)
        attrs = file_path.xattrs()
        unlink_fakes(attrs, fake_paths, metastore)
        return

    limit_mb = 2
    file_mb = file.size / 1024 ** 2
    skip = 'jpeg', 'jpg', 'tif', 'png'
    file_xattrs = make_file_xattrs(file)

    if (not limit or
        (file_mb < limit_mb and
         (not file_path.suffixes or
          file_path.suffixes[0][1:].lower() not in skip))):
        print('fetching', file)
        for i in range(4):  # try 4 times
            try:
                # FIXME I think README_README is an s3_key related error
                file.download(file_path.as_posix())
                file_path.setxattrs(file_xattrs)
                metastore.setxattrs(file_path, file_xattrs)
                attrs = file_path.xattrs()  # yes slow, but is a sanity check
                # TODO validate the checksum when we get it
                unlink_fakes(attrs, fake_paths, metastore)
                return
            except (HTTPError, ConnectionError) as e:
                error = str(e)
                status_code = e.response.status_code
                asyncio.sleep(3)
        else:
            print(error)
            error_path = file_path.with_suffix(file_path.suffix + '.fake.ERROR')
            error_path.touch()
            file_xattrs['bf.error'] = str(status_code)
            error_path.setxattrs(file_xattrs)
            metastore.setxattrs(error_path, file_xattrs)
    else:
        fsize = str(int(file_mb)) + 'M' if file_mb >= 1 else str(file.size // 1024) + 'K'
        fakepath = file_path.with_suffix(file_path.suffix + '.fake.' + fsize)
        fakepath.touch()
        fakepath.setxattrs(file_xattrs)
        metastore.setxattrs(fakepath, file_xattrs)

def make_files_meta(collection):
    # TODO file fetching status? file hash?
    return {make_filename(file):[package.id, file.id, file.size]
            for package in collection
            if isinstance(package, DataPackage)
            for file in package.files}

def make_folder_and_meta(parent_path, collection, metastore):
    folder_path = parent_path / collection.name
    #meta_file = folder_path / collection.id
    #if isinstance(collection, Organization):
        #files_meta = {}
    #else:
        #files_meta = make_files_meta(collection)
    folder_path.mkdir(parents=True, exist_ok=True)
    folder_path.setxattr('bf.id', collection.id)  # sadly xattrs are easy to accidentally zap :/
    metastore.setxattr(folder_path, 'bf.id', collection.id)
    #with open(meta_file, 'wt') as f:
        #yaml.dump(files_meta, f, default_flow_style=False)


def get_file_by_id(get, file_path, pid, fid):
    package = get(pid)
    if package is None:
        print('WARNING package does not exist', file_path, pid, fid)
        return None, None

    for f in package.files:
        if f.id == fid:
            return file_path, f
    else:
        print('WARNING file does not exist', file_path, pid, fid)
        return None, None

class MetaStore:
    """ A local backup against accidental xattr removal """
    attrs = 'bf.id', 'bf.file_id', 'bf.size', 'bf.checksum', 'bf.error'
    # FIXME horribly inefficient 1 connection per file due to the async code ... :/
    def __init__(self, db_path):
        if isinstance(db_path, Path):
            db_path = db_path.as_posix()

        self.db_path = db_path
        self.setup()

    def conn(self):
        return sqlite3.connect(self.db_path)

    def setup(self):
        sqls = (('CREATE TABLE IF NOT EXISTS fsxattrs '
                 '(path TEXT PRIMARY KEY,'
                 'bf_id TEXT NOT NULL,'
                 'bf_file_id INTEGER,'
                 'bf_size INTEGER,'
                 'bf_checksum BLOB,'
                 'bf_error INTEGER);'),
                ('CREATE UNIQUE INDEX IF NOT EXISTS fsxattrs_u_path ON fsxattrs (path);'))
        conn = self.conn()
        with conn:
            for sql in sqls:
                conn.execute(sql)

    def bulk(self, pdict):
        sql = (f'INSERT OR REPLACE INTO fsxattrs (path, bf_id, bf_file_id, bf_size, bf_checksum, bf_error) VALUES (?, ?, ?, ?, ?, ?)')
        conn = self.conn()
        with conn:
            for path, attrs in pdict.items():
                args = path.as_posix(), *self.convert_attrs(attrs)
                conn.execute(sql, args)

    def remove(self, path):
        sql = 'DELETE FROM fsxattrs WHERE path = ?'
        args = path.as_posix(),
        conn = self.conn()
        with conn:
            return conn.execute(sql, args)
        
    def convert_attrs(self, attrs):
        for key in self.attrs:
            if key in attrs:
                yield attrs[key]
            else:
                yield None

    def xattrs(self, path):
        sql = 'SELECT * FROM fsxattrs WHERE path = ?'
        args = path.as_posix(),
        conn = self.conn()
        with conn:
            cursor = conn.execute(sql, args)
            values = cursor.fetchone()
            print(values)
            if values:
                keys = [n.replace('_', '.', 1) for n, *_ in cursor.description]
                #print(keys, values)
                return {k:v for k, v in zip(keys, values) if k != 'path' and v is not None}  # skip path itself
            else:
                return {}

    def setxattr(self, path, key, value):
        return self.setxattrs(path, {key:value})

    def setxattrs(self, path, attrs):
        # FIXME skip nulls on replace
        sql = (f'INSERT OR REPLACE INTO fsxattrs (path, bf_id, bf_file_id, bf_size, bf_checksum, bf_error) VALUES (?, ?, ?, ?, ?, ?)')
        args = path.as_posix(), *self.convert_attrs(attrs)
        conn = self.conn()
        with conn:
            return conn.execute(sql, args)

    def getxattr(self, path, key):
        if key in self.attrs:
            col = key.replace('.', '_')
            sql = f'SELECT {col} FROM fsxattrs WHERE path = ?'
            args = path.as_posix(),
            conn = self.conn()
            with conn:
                return conn.execute(sql, args)
        else:
            print('WARNING unknown key', key)
        

class BFLocal:

    class NoBfMeta(Exception):
        """ There is not bf id for this file. """

    def __init__(self):
        self.bf = Blackfynn(api_token=devconfig.secrets('blackfynn-sparc-key'),
                            api_secret=devconfig.secrets('blackfynn-sparc-secret'))
        self.project_name = self.bf.context.name
        self.project_path = local_storage_prefix / self.project_name
        self.metastore = MetaStore(self.project_path.parent / (self.project_name + ' xattrs.db'))

    @property
    def error_meta(self):
        for path in list(self.project_path.rglob('*ERROR')):
            yield self.get_file_meta(path)

    @property
    def fake_files(self):
        yield from self.project_path.rglob('*.fake.*')

    @property
    def big_meta(self):
        for path in self.fake_files:
            if path.suffix != '.ERROR':
                yield self.get_file_meta(path)

    def populate_metastore(self):
        """ This should be run after find_missing_meta. """
        # FIXME this function is monstrously slow :/
        # need a bulk insert
        all_attrs = {path:path.xattrs() for path in self.project_path.rglob('*')}
        bad = [path for path, attrs in all_attrs.items() if not attrs]
        if bad:
            print('WARNING:', path, 'is missing meta, run find_missing_meta')
            all_attrs = {p:a for p, a in all_attrs.items() if a}

        self.metastore.bulk(all_attrs)

    def find_missing_meta(self):
        for path in self.project_path.rglob('*'):
            attrs = path.xattrs()
            if not attrs:
                print('Found path with missing metadata', path)
                attrs = self.metastore.xattrs(path)
                if not attrs:
                    print('No local metadata was found for', path)
                    attrs = self.recover_meta(path)

                path.setxattrs(attrs)
                # TODO checksum may no longer match since we changed it

    def recover_meta(self, path):
        pattrs = path.parent.xattrs()
        codid = pattrs['bf.id']
        if codid.startswith('N:collection:'):
            thing = self.bf.get(codid)
        elif codid.startswith('N:dataset:'):
            thing = self.bf.get_dataset(codid)  # heterogenity is fun!
        else:
            raise BaseException('What are you doing!??!?!')

        test_path = path
        while '.fake' in test_path.suffixes:
            test_path = test_path.with_suffix('')

        for poc in thing:
            if poc.name == test_path.stem:  # FIXME
                for file in poc.files:  # FIXME files vs folders
                    filename = make_filename(file)
                    if filename == test_path.name:
                        return make_file_xattrs(file)

    def get_file_meta(self, path):
        attrs = path.xattrs()
        if 'bf.id' not in attrs:
            # TODO maintain a single backup mapping of xattrs to paths
            # and just use the xattrs for performance
            attrs = self.metastore.xattrs(path)
            if attrs:
                # TODO checksum ... (sigh git)
                path.setxattrs(attrx)
                attrs = path.xattrs()
            else:
                raise self.NoBfMeta

        pid = attrs['bf.id']
        if pid.startswith('N:package:'):
            fid = int(attrs['bf.file_id'])
            file_path = path
            while '.fake' in file_path.suffixes:
                file_path = file_path.with_suffix('')
            
            return file_path, pid, fid
        else:
            print('WARNING what is going on with', path, attrs)

    def fetch_path(self, path):
        """ Fetch individual big files.
            `path` argument must be to a fake file which has the meta stored in xattrs """
        # automatic async function application inside a list comp ... would be fun
        fetch_file(*get_file_by_id(self.bf.get, *self.get_file_meta(path)), self.metastore)

    def fetch_errors(self):
        bfiles = {fp:f for fp, f in
                  Async()(deferred(get_file_by_id)(self.bf.get, file_path, pid, fid)
                          for file_path, pid, fid in self.error_meta)}
        Async()(deferred(fetch_file)(filepath, file, self.metastore) for filepath, file in bfiles.items() if not filepath.exists())

    def file_fetch_dict(self, packages):
        return {folder_path / make_filename(file):file
                for folder_path, files in
                Async()(deferred(gfiles)(package, path) for package, path in packages)
                for file in files}

    def cons(self):
        ds = self.bf.datasets()
        useful = {d.id:d for d in ds}  # don't worry, I've made this mistake too
        small = useful['N:dataset:f3ccf58a-7789-4280-836e-ad9d84ee2082']
        hrm = useful['N:dataset:be0183e4-a912-465a-bd15-ff36973ee8b3']  # lots of 500 errors
        readme_bug = useful['N:dataset:6d6818f2-ef75-4be5-9360-8d37661a8463']
        skip = (
            'N:dataset:83e0ebd2-dae2-4ca0-ad6e-81eb39cfc053',  # hackathon
            'N:dataset:ec2e13ae-c42a-4606-b25b-ad4af90c01bb',  # big max
        )
        datasets = [d for d in ds if d.id not in skip]
        #datasets = hrm, readme_bug
        #datasets = small,
        #embed()
        #return
        packages = []
        collections = [(self.bf.context, local_storage_prefix)]
        for dataset in datasets:
            dataset_name = dataset.name
            ds_path = self.project_path / dataset_name
            collections.append((dataset, self.project_path))
            for package_or_collection in dataset:
                pocs = list(get_packages(package_or_collection, ds_path))
                packages.extend(((poc, fp) for poc, fp in pocs
                                 if isinstance(poc, DataPackage)))
                collections.extend(((poc, fp) for poc, fp in pocs
                                    if isinstance(poc, BaseCollection) or isinstance(poc, Organization)))

        bfolders = [make_folder_and_meta(parent_path, collection, self.metastore)
                    for collection, parent_path in collections]  # FIXME duplicates and missing ids
        # TODO the collection file should hold the mapping from the file names to their blackfynn ids and local hashes
        #meta = 'subjects', 'submission', 'submission_spreadsheet', 'dataset_description', 'detaset_description_spreadsheet', 'manifest', 'README'
        #meta_subset = [(package, fp) for package, fp in packages if package.name in meta]
        bfiles = self.file_fetch_dict(packages)

        # beware that this will send as many requests as it can as fast as it can
        # which is not the friendliest thing to do to an api
        Async()(deferred(fetch_file)(filepath, file, self.metastore, limit=True)
                for filepath, file in bfiles.items() if not filepath.exists())
        #embed()


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
              Async()(deferred(gfiles)(package, path) for package, path in packages)
              for file in files}

    # beware that this will send as many requests as it can as fast as it can
    # which is not the friendliest thing to do to an api
    Async()(deferred(fetch_file)(*fpf, self.metastore) for fpf in bfiles.items() if not fp.exists())

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
    bfl = BFLocal()
    #bfl.cons()
    #bfl.fetch_errors()
    ff = list(bfl.fake_files)
    embed()

if __name__ == '__main__':
    main()
