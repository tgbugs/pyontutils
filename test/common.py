from pathlib import Path
from pyontutils.config import devconfig
from git import Repo as baseRepo


class Repo(baseRepo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._untracked_start = self.untracked()

    def untracked(self):
        return set(self.git.ls_files('--others', '--exclude-standard').split('\n'))

    def diff_untracked(self):
        new_untracked = self.untracked()
        diff = new_untracked - self._untracked_start
        return diff

    def remove_diff_untracked(self):
        wd = Path(self.working_dir)
        for tail in self.diff_untracked():
            path = wd / tail
            print('removing file', path)
            path.unlink()


class Folders:
    _folders =  ('ttl', 'ttl/generated', 'ttl/generated/parcellation', 'ttl/bridge')
    def setUp(self):
        #print('SET UP')
        #print(devconfig.ontology_local_repo)
        if devconfig.ontology_local_repo.isDefault:
            self.fake_local_repo = Path(devconfig.git_local_base, devconfig.ontology_repo)
            if not self.fake_local_repo.exists():  # do not klobber existing
                self.folders = [(self.fake_local_repo / folder)
                                for folder in self._folders]
                self.addCleanup(self._tearDown)
                #print(f'CREATING FOLDERS {self.folders}')
                for folder in self.folders:
                    folder.mkdir(parents=True)
                    # if the parent doesn't exist then there should never
                    # be a case where there is a collision (yes?)

        else:
            self.folders = []

    def recursive_clean(self, d):
        for thing in d.iterdir():
            if thing.is_dir():
                self.recursive_clean(thing)
            else:
                thing.unlink()  # will rm the file

        d.rmdir()

    def _tearDown(self):
        #print('TEAR DOWN')
        if self.folders:
            #print(f'DELETING FOLDERS {self.folders}')
            self.recursive_clean(self.fake_local_repo)


