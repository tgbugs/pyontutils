#!/usr/bin/env python3.7
"""Compile all ontology related documentation.

Usage:
    ont-docs [options] [--repo=<REPO>...]

Options:
    -h --help            show this
    -s --spell           run hunspell on all docs
    -o --docstring-only  build docstrings only
    -j --jobs=NJOBS      number of jobs [default: 9]
    -r --repo=<REPO>     additional repos to crawl for docs

"""
import os
import re
import ast
import shutil
import subprocess
from urllib.parse import urlparse
from importlib import import_module
import nbformat
from git import Repo
from htmlfn import htmldoc, atag
from joblib import Parallel, delayed
from nbconvert import HTMLExporter
from augpathlib import RepoPath as Path, exceptions as aexc
from pyontutils.utils import TODAY, noneMembers, makeSimpleLogger
from pyontutils.utils import TermColors as tc, get_working_dir
from pyontutils.config import auth
from pyontutils.ontutils import tokstrip, _bads

log = makeSimpleLogger('ont-docs')
working_dir = Path(__file__).resolve().working_dir

try:
    import hunspell
except ImportError:
    hunspell = None

suffixFuncs = {}


def patch_theme_setup(theme):
    with open(theme, 'rt+') as f:
        dat = f.read()
        f.seek(0)
        f.write(dat.replace('="styles/', '="/docs/styles/'))


_org_edit_link_html = '#+HTML: <div align="right"><a href={edit_link}>Edit on GitHub</a></div>\n'
def makeOrgHeader(title, authors, date, theme, edit_link=None):
    header = (f'#+TITLE: {title}\n'
              f'#+AUTHOR: {authors}\n'
              f'#+DATE: {date}\n'
              f'#+SETUPFILE: {theme}\n'
              f'#+OPTIONS: ^:nil num:nil html-preamble:t H:2\n'
              #'#+LATEX_HEADER: \\renewcommand\contentsname{Table of Contents}\n'  # unfortunately this is to html...
             )

    if edit_link is not None:
        header += _org_edit_link_html.format(edit_link=edit_link)

    return header


class FixLinks:
    link_pattern = re.compile(rb'\[\[(.*?)\]\[(.*?)\]\]', flags=re.S)  # non greedy . matches all
    single_pattern = re.compile(rb'\[\[(file:.*?)\]\]')

    class MakeMeAnInlineSrcBlock(Exception):
        """ EVIL """

    def __init__(self, current_file):
        print('========================================')
        print(current_file)
        self.current_file = current_file
        self.working_dir = get_working_dir(self.current_file)
        self.repo = Repo(self.working_dir)
        self.remote_url = next(self.repo.remote().urls)
        if self.remote_url.startswith('git@'):
            self.remote_url = 'ssh://' + self.remote_url

        duh = urlparse(self.remote_url)
        self.netloc = duh.netloc

        if self.netloc.startswith('git@github.com'):
            _, self.group = self.netloc.split(':')
            self.netloc = 'github.com'

        elif self.netloc == 'github.com':
            _, self.group, *rest = duh.path.split('/')
        else:
            raise NotImplementedError(self.remote_url)



    def __call__(self, org):
        org = re.sub(rb'\[\[\.\/', b'[[file:', org)  # run this once at the start
        org = re.sub(rb'\[\[\.\.\/', b'[[file:../', org)  # run this once at the start

        #print(org.decode())
        out = re.sub(self.link_pattern, self.process_matches, org)
        out = re.sub(self.single_pattern, self.process_matches, out)
        #print(out.decode())
        return out

    def process_matches(self, match):
        href, *text = match.groups()
        if text:
            text, = text
        else:
            log.debug(match)
            text = href.replace(b'file:', b'')

        try:
            outlink = b'[[' + self.fix_href(href) + b'][' + self.fix_text(text, href) + b']]'
        except self.MakeMeAnInlineSrcBlock as e:
            outlink = f'={href.decode().replace("file:", "")}='.encode()

        #if b'md#' in outlink:
        #if match.group() != outlink:
            #print('MATCH', match.group().decode())
            #print('OUTLN', outlink.decode())
        return outlink

    def fix_text(self, btext, bhref):
        if not btext:
            return bhref

        return btext.replace(b'\n', b' ').replace(b'\r', b' ')  # grrr pandoc with the \r :/

    @staticmethod
    def fix_github(href):
        up = urlparse(href)
        _, user, project, rest = up.path.split('/', 3)
        if (user not in ('tgbugs', 'SciCrunch') or
            not (rest.startswith('blob') or rest.startswith('tree'))):
            return href

        _, branch, rest = rest.split('/', 2)
        if branch != 'master':
            return href

        rest, *fragment = rest.rsplit('#', 1)
        fragment = '#' + fragment if fragment else ''
        rest, *query = rest.rsplit('?', 1)
        query = '?' + query if query else ''
        dir_stem, old_suffix = rest.rsplit('.', 1)
        local_path = dir_stem + '.html'
        path = f'/docs/{project}/' + local_path + query + fragment
        out = 'hrefl:' + path
        #log.debug(out)
        return out

    def fix_href(self, bhref):
        href = bhref.decode()
        out = href

        if any(out.startswith(p) for p in ('http', 'img:')):
            # TODO if there is a full github link to one of our files here swap it out
            if (out.startswith('https://github.com') and
                (any(out.endswith(suffix) or (suffix + '#') in out for suffix in
                    ('.md', '.org', '.ipynb')))):
                out = self.fix_github(out)
                return out.encode()
            else:
                return bhref


        class SubRel:
            current_file = self.current_file
            working_dir = self.working_dir
            def __init__(self, base, mmaisb=self.MakeMeAnInlineSrcBlock):
                self.base = base
                self.MakeMeAnInlineSrcBlock = mmaisb  # lol

            def __call__(self, match):
                name, suffix, rest = match.groups()
                if rest is None:
                    rest = ''

                if not any(name.startswith(p) for p in ('$', '#')):
                    try:
                        rel = (self.current_file.parent /
                            (name + suffix)).resolve().relative_to(self.working_dir)
                    except ValueError as e:
                        log.error('path went outside current repo')
                        return name + suffix + rest

                    if suffix in ('.md', '.org', '.ipynb'):
                        rel = rel.with_suffix('.html')
                    rel_path = rel.as_posix() + rest
                    #print('aaaaaaaaaaa', suffix, rel, rel_path)
                    return self.base + rel_path
                elif name.startswith('$'):
                    raise self.MakeMeAnInlineSrcBlock(match.group())
                else:
                    #print('bbbbbbbbbbb', match.group())
                    return match.group()  # rel_path = name + ext + rest


        #print('----------------------------------------')
        # TODO consider htmlifying these ourselves and serving them directly
        sub_github = SubRel(f'https://{self.netloc}/{self.group}/{self.working_dir.name}/blob/master/')
        # source file and/or code extensions regex
        # TODO folders that simply end
        code_regex = (r'(\.(?:el|py|sh|ttl|graphml|yml|yaml|spec|example|xlsx|svg)'
                      r'|LICENSE|catalog-extras|authorized_keys|\.vimrc)')
        out0 = re.sub(r'^file:(.*)'
                      + code_regex +
                      r'(#.+)*$',
                      sub_github, out)

        #print('----------------------------------------')
        # FIXME won't work if the outer folder does not match the github project name
        sub_docs = SubRel(f'hrefl:/docs/{self.working_dir.name}/')
        out1 = re.sub(r'^file:(.*)'
                      r'(\.(?:md|org|ipynb))'
                      r'(#.+)*$', sub_docs, out0)
        out = out1
        #print('----------------------------------------')

        if not any(out.startswith(s) for s in ('https:', 'http:', 'hrefl:',
                                               'file:', 'img:', 'mailto:', '/', '#')):
            log.warning(f'Potentially relative path {out!r} does not have a known good start in {self.current_file}')

        return out.encode()

def get__doc__s():
    repo = Repo(working_dir.as_posix())
    paths = sorted(f for f in repo.git.ls_files().split('\n')
                   if f.endswith('.py') and
                   any(f.startswith(n) for n in
                       ('pyontutils', 'ttlser', 'nifstd', 'neurondm')))
    # TODO figure out how to do relative loads for resolver docs
    docs = []
    #skip = 'neuron', 'phenotype_namespaces'  # import issues + none have __doc__
    skip = 'ilxcli', 'deploy'
    for i, path in enumerate(paths):
        if any(nope in path for nope in skip):
            continue
        ppath = (working_dir / path).resolve()
        #print(ppath)
        module_path = ppath.relative_to(working_dir).as_posix()[:-3].replace('/', '.')
        #print(module_path)

        with open(ppath, 'rt') as f:
            tree = ast.parse(f.read())

        doc = ast.get_docstring(tree)

        #module = import_module(module_path)
        #doc = (module.__doc__
               #if module.__doc__
               #else print(tc.red('WARNING:'), 'no docstring for', module_path))
        if doc is None:
            #print(tc.red('WARNING:'), 'no docstring for', module_path)
            pass

        if doc and 'Usage:' in doc:
            # get cli program name
            title = doc.split('Usage:', 1)[1].strip().split(' ')[0]
            heading = 'Scripts'
        else:
            title = module_path
            heading = 'Modules'
        #print(title)
        docs.append((heading, title, doc))

    return sorted(docs, reverse=True)


def docstrings(theme):
    docstr_file = 'docstrings.org'
    docstr_path = working_dir / docstr_file
    title = 'Command line programs and libraries'
    authors = 'various'
    date = TODAY()
    docstr_kwargs = (working_dir, docstr_path,
                     {'authors': authors,
                      'date': date,
                      'title': title})
    docstrings = get__doc__s()
    header = makeOrgHeader(title, authors, date, theme)

    done = []
    dslist = []
    for type, module, docstring in docstrings:
        if type not in done:
            done.append(type)
            dslist.append(f'* {type}')
        if docstring is not None:
            dslist.append(f'** {module}\n#+BEGIN_SRC\n{docstring}\n#+END_SRC')

    docstrings_org = header + '\n'.join(dslist)
    with open(docstr_path.as_posix(), 'wt') as f:
        f.write(docstrings_org)

    return docstr_kwargs


def suffix(ext):  # TODO multisuffix?
    def decorator(function):
        suffixFuncs['.' + ext.strip('.')] = function
        return function
    return decorator

def pandocVersion():
    p = subprocess.Popen(['pandoc', '--version'], stdout=subprocess.PIPE)
    out, _ = p.communicate()
    version = out.split(b'\n', 1)[0].split(b' ', 1)[-1].decode()
    return version

def getMdReadFormat(version):
    if version < '2.2.1':
        return 'markdown_github'
    else:
        return 'gfm'

pdv = pandocVersion()
md_read_format = getMdReadFormat(pdv)
pandoc_columns = pdv < '2.2.3' # pandoc version >= 2.2.3 vastly improved org export
#pandoc_columns = True  # I think this was due to the fact that I had a weird version lingering


def spell(filenames, debug=False):
    if hunspell is None:
        raise ImportError('hunspell is not installed on your system. If you want '
                          'to run `ontutils spell` please run pipenv install --dev --skip-lock. '
                          'You will need the development libs for hunspell on your system.')
    hobj = hunspell.HunSpell('/usr/share/hunspell/en_US.dic', '/usr/share/hunspell/en_US.aff')
    #nobj = hunspell.HunSpell(os.path.expanduser('~/git/domain_wordlists/neuroscience-en.dic'), '/usr/share/hunspell/en_US.aff')  # segfaults without aff :x
    collect = set()
    for filename in filenames:
        missed = False
        no = []
        with open(filename, 'rt') as f:
            for line_ in f.readlines():
                line = line_.rstrip()
                nline = []
                #print(tc.blue(line))
                for pattern in _bads:
                    line = line.replace(pattern, ' ' * len(pattern))

                #print(line)
                for tok in line.split(' '):
                    prefix, tok, suffix = tokstrip(tok)
                    #print((prefix, tok, suffix))
                    if not hobj.spell(tok):# and not nobj.spell(tok):
                        missed = True
                        collect.add(tok)
                        nline.append(prefix + tc.red(tok) + suffix)
                    else:
                        nline.append(prefix + tok + suffix)
                line = ' '.join(nline)
                no.append(line)

        o = '\n'.join(no)
        if missed:
            #print(filename, s, o)
            print('>>>', o)
            pass

    if debug:
        [print(_) for _ in sorted(collect)]
        breakpoint()


# NOTE if emacs does not point to /usr/bin/emacs or similar this will fail
compile_org_file = ['emacs', '-q', '-l',
                    (auth.get_path('git-local-base') /
                     'orgstrap/init.el').resolve().as_posix(),
                    '--batch', '-f', 'compile-org-file']


@suffix('org')
def renderOrg(path, **kwargs):
    orgfile = path.as_posix()
    try:
        ref = path.latest_commit.hexsha
        github_link = path.remote_uri_human(ref=ref)
    except aexc.NoCommitsForFile:
        github_link = None

    #print(' '.join(compile_org_file))
    p = subprocess.Popen(compile_org_file,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)

    with open(orgfile, 'rb') as f:
        # for now we do this and don't bother with the stream implementaiton of read1 write1
        org_in = f.read()
        theme = kwargs['theme']
        full_theme = theme.as_posix()
        if b'#+SETUPFILE:' not in org_in:
            insert = f'\n\n#+SETUPFILE: {full_theme}\n'.encode()
        else:
            insert = b''

        if github_link is not None:
            insert += _org_edit_link_html.format(edit_link=github_link).encode() + b'\n'

        try:
            if org_in.startswith(b'* '):
                org = insert + org_in
            else:
                title_author_etc, rest = org_in.split(b'\n\n', 1)
                org = (title_author_etc +
                       insert +
                       rest)
        except ValueError as e:
            title = kwargs['title']
            authors = kwargs['authors']
            date = kwargs['date']
            title_author_etc = makeOrgHeader(title, authors, date, theme, github_link)
            org = title_author_etc.encode() + org_in
            #raise ValueError(f'{orgfile!r}') from e


        # fix links
        fix_links = FixLinks(path)
        org = fix_links(org)

        #org =  + org_in  # TODO check how this interacts with other #+SETUPFILE: lines
        #print(org.decode())
        out, err = p.communicate(input=org)

    return out.decode()


@suffix('md')
def renderMarkdown(path, title=None, authors=None, date=None, **kwargs):
    mdfile = path.as_posix()
    try:
        ref = path.latest_commit.hexsha
        github_link = path.remote_uri_human(ref=ref)
    except aexc.NoCommitsForFile:
        github_link = None

    # TODO fix relative links to point to github

    if pandoc_columns:
        pandoc = ['pandoc', '--columns', '600', '-f', md_read_format, '-t', 'org', mdfile]
    else:
        pandoc = ['pandoc', '-f', md_read_format, '-t', 'org', mdfile]
    sed = ['sed', r's/\[\[\(.\+\)\]\[\[\[\(.\+\)\]\]\]\]/[[img:\2][\1]]/g']
    ohnosed = ['sed', r's/\]\]\]\]\ \[\[/\]\]\]\]\n\[\[/g']

    p = subprocess.Popen(pandoc,
                         stdout=subprocess.PIPE)
    ohno = subprocess.Popen(ohnosed,
                            stdin=p.stdout,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    s = subprocess.Popen(sed,
                         stdin=ohno.stdout,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    e = subprocess.Popen(compile_org_file,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)  # DUH
    authors = ', '.join(authors)
    theme = kwargs['theme']
    header = makeOrgHeader(title, authors, date, theme, github_link)
    out, err = s.communicate()
    #print(out.decode())

    org = header.encode() + out.replace(b'\_', b'_')  #.replace(b'[[file:', b'[[./')

    org = re.sub(br'(\w)=s', br'\1= s', org)  # the closing = on inline code blocks needs a trailing space

    ## org = org.replace(b'.md][', b'.html][')  # FIXME fix suffixes for doc paths

    #org = re.sub(br'\[(.+\.)[a-z]+\]\[', br'[\1html][', org)
    # [[]] case and [[][]] case
    gitorg = kwargs['org']
    gitrepo = kwargs['repo']
    branch = kwargs['branch']
    dir_ = title.rsplit('/', 1)[0]
    dir_ = '' if dir_ == title else dir_ + '/'


    # fix links
    fix_links = FixLinks(path)
    org = fix_links(org)

    #print(org.decode())

    # debug debug
    #with open(path.with_suffix('.org').as_posix(), 'wb') as f:
        #f.write(org)
    # there is not satisfactory way to fix this issue right now
    # but it might also be a bug in pandoc's org exporter
    body, err = e.communicate(input=org)
    # debug
    #print(' '.join(pandoc), '|', ' '.join(sed), '|', ' '.join(compile_org_file))
    #if b'[[img:' in out or not out or 'external-sources' in path.as_posix():
        #breakpoint()
    err = err.strip(b'Created img link.\n')  # FIMXE lack of distinc STDERR is very annoying
    if e.returncode:
        # if this happens direct stderr to stdout to get the message
        raise subprocess.CalledProcessError(e.returncode,
                                            ' '.join(e.args) + f' {path.as_posix()}') from ValueError(err.decode())
    if not body or b'*temp*' in body:
        raise ValueError(f'Output document for {path.as_posix()} '
                         'has no body! the input org was:\n'
                         f'{org.decode()}')
    return body.decode().replace('Table of Contents', title)

@suffix('ipynb')
def renderNotebook(path, **kwargs):
    nbfile = path.as_posix()
    with open(nbfile, 'rt') as f:
        notebook = nbformat.read(f, as_version=4)
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'full'
    body, resources = html_exporter.from_notebook_node(notebook)
    return body

def renderDoc(path, **kwargs):
    # TODO add links back to github and additional prov for generation
    try:
        # renderMarkdown # renderOrg
        return suffixFuncs[path.suffix](path, **kwargs)
    except KeyError as e:
        raise TypeError(f'Don\'t know how to render {path.suffix}') from e

def makeKwargs(repo, filepath):
    kwargs = {}
    kwargs['title'] = (Path(repo.working_dir).name + ' ' + filepath
                       if filepath.startswith('README.')
                       else filepath)
    kwargs['authors'] = sorted(name.strip()
                               for name in
                               set(repo.git.log(['--pretty=format:%an%x09',
                                                 filepath]).split('\n')))
    kwargs['date'] = repo.git.log(['-n', '1', '--pretty=format:%aI']).strip()
    repo_url = Path(next(next(r for r in repo.remotes if r.name == 'origin').urls))
    kwargs['org'] = repo_url.parent.name
    kwargs['repo'] = repo_url.stem
    kwargs['branch'] = 'master'  # TODO figure out how to get the default branch on the remote

    return kwargs

def outFile(doc, working_dir, BUILD):
    relative_html = doc.relative_to(working_dir.parent).with_suffix('.html')
    return BUILD / 'docs' / relative_html


def run_all(doc, wd, BUILD, **kwargs):
    return outFile(doc, wd, BUILD), renderDoc(doc, **kwargs)


def render_docs(wd_docs_kwargs, BUILD, n_jobs=9):
    if 'CI' in os.environ or n_jobs == 1:
        outname_rendered = [(outFile(doc, wd, BUILD), renderDoc(doc, **kwargs))
                            for wd, doc, kwargs in wd_docs_kwargs]
    else:
        outname_rendered = Parallel(n_jobs=n_jobs)(delayed(run_all)(doc, wd, BUILD, **kwargs)
                                              for wd, doc, kwargs in wd_docs_kwargs)
    return outname_rendered


def deadlink_check(html_file):
    """ TODO """


def prepare_paths(BUILD, docs_dir, theme_repo, theme):
    patch_theme_setup(theme)

    if not BUILD.exists():
        BUILD.mkdir()

    if not docs_dir.exists():
        docs_dir.mkdir()

    theme_styles_dir = theme_repo / 'styles'
    doc_styles_dir = docs_dir / 'styles'
    if doc_styles_dir.exists():
        shutil.rmtree(doc_styles_dir)

    shutil.copytree(theme_styles_dir, doc_styles_dir)

    # this is tricky
    #images_dir = docs_dir / 'images'
    #if images_dir.exists():
        #shutil.rmtree(images_dir)

    #images_dir.mkdir()
    #shutil.copy(image, images_dir)


def main():
    from docopt import docopt
    args = docopt(__doc__)

    BUILD = working_dir / 'doc_build'
    docs_dir = BUILD / 'docs'
    glb = Path(auth.get_path('git-local-base'))
    theme_repo = glb / 'org-html-themes'
    theme =  theme_repo / 'setup/theme-readtheorg-local.setup'
    prepare_paths(BUILD, docs_dir, theme_repo, theme)

    docstring_kwargs = docstrings(theme)
    wd_docs_kwargs = [docstring_kwargs]
    if args['--docstring-only']:
        [kwargs.update({'theme': theme}) for _, _, kwargs in wd_docs_kwargs]
        outname, rendered = render_docs(wd_docs_kwargs, BUILD, 1)[0]
        if not outname.parent.exists():
            outname.parent.mkdir(parents=True)
        with open(outname.as_posix(), 'wt') as f:
            f.write(rendered)
        return

    names = ('augpathlib', 'interlex', 'ontquery', 'orthauth', 'sparc-curation') + tuple(args['--repo'])
    repo_paths = [Path(auth.get_path('ontology-local-repo')),
                  Path(working_dir)] + [glb / name for name in names]
    repos = [p.repo for p in repo_paths]
    skip_folders = 'notebook-testing', 'complete', 'ilxutils', 'librdflib'
    rskip = {
        'pyontutils': (
            'docs/NeuronLangExample.ipynb',  # exact skip due to moving file
            'ilxutils/ilx-playground.ipynb',
            'nifstd/resources/sawg.org',  # published via another workflow
        ),
        'sparc-curation': (
            'README.md',  # insubstantial
            'docs/apinatomy.org',
            'docs/developer-guide.org',
            'docs/notes.org',
            'test/apinatomy/README.org',
        ),
        'interlex': (
            'README.md',  # insubstantial
            'docs/explaining.org',  # not ready
        ),}

    et = tuple()
    # TODO move this into run_all
    #wd_docs_kwargs = [(Path(repo.working_dir).resolve(),
    wd_docs_kwargs += [(Path(repo.working_dir).resolve(),
                        Path(repo.working_dir, f).resolve(),
                        makeKwargs(repo, f))
                       for repo in repos
                       for f in repo.git.ls_files().split('\n')
                       if Path(f).suffix in suffixFuncs
                       #and Path(repo.working_dir).name == 'NIF-Ontology' and f == 'README.md'  # DEBUG
                       #and Path(repo.working_dir).name == 'pyontutils' and f == 'README.md'  # DEBUG
                       #and Path(repo.working_dir).name == 'sparc-curation' and f == 'docs/setup.org'  # DEBUG
                       and noneMembers(f, *skip_folders)
                       and f not in rskip.get(Path(repo.working_dir).name, et)]

    [kwargs.update({'theme': theme}) for _, _, kwargs in wd_docs_kwargs]

    if args['--spell']:
        spell((f.as_posix() for _, f, _ in wd_docs_kwargs))
        return

    outname_rendered = render_docs(wd_docs_kwargs, BUILD, int(args['--jobs']))

    titles = {
        ###
        'Components':'Components',
        'NIF-Ontology/README.html':'Introduction to the NIF Ontology',  #
        'ontquery/README.html':'Introduction to ontquery',
        'orthauth/README.html':'Introduction to orthauth',
        'pyontutils/README.html':'Introduction to pyontutils',
        'pyontutils/nifstd/README.html':'Introduction to nifstd-tools',
        'pyontutils/neurondm/README.html':'Introduction to neurondm',
        'pyontutils/ilxutils/README.html':'Introduction to ilxutils',

        ###
        'Developer docs':'Developer docs',
        'NIF-Ontology/docs/processes.html':'Ontology development processes (START HERE!)',  # HOWTO
        'NIF-Ontology/docs/development-setup.html': 'Ontology development setup',  # HOWTO
        'sparc-curation/docs/setup.html': 'Developer and curator setup (broader scope but extremely detailed)',
        'pyontutils/docs/release.html': 'Python library packaging and release process',
        'NIF-Ontology/docs/import-chain.html': 'Ontology import chain',  # Documentation

        'pyontutils/nifstd/resolver/README.html': 'Ontology resolver setup',
        'interlex/alt/README.html': 'InterLex alternate resolver',  # TODO
        'interlex/docs/setup.html': '',  # present but not visibly listed
        'interlex/docs/implementation.html': '',  # present but not visibly listed

        'pyontutils/nifstd/scigraph/README.html': 'Ontology SciGraph setup',
        'sparc-curation/resources/scigraph/README.html': 'SPARC SciGraph setup',
        'sparc-curation/resources/scigraph/data/build.html': 'SPARC SciGraph data setup',

        'pyontutils/docstrings.html': 'Command line programs',
        'NIF-Ontology/docs/external-sources.html': 'External sources for the ontology',  # Other
        'ontquery/docs/interlex-client.html': 'InterLex client library doccumentation',
        'orthauth/docs/guide.html': 'Orthauth guide',

        ###
        'Contributing':'Contributing',
        'pyontutils/nifstd/development/README.html':'Contributing to the ontology',
        'pyontutils/nifstd/development/community/README.html':'Contributing term lists to the ontology',
        'pyontutils/neurondm/neurondm/models/README.html':'Contributing neuron terminology to the ontology',

        ###
        'Ontology content':'Ontology content',
        'NIF-Ontology/docs/brain-regions.html':'Parcellation schemes',  # Ontology Content
        'pyontutils/nifstd/development/methods/README.html':'Methods and techniques',  # Ontology content
        'NIF-Ontology/docs/Neurons.html':'Neuron Lang overview',
        'pyontutils/neurondm/docs/NeuronLangExample.html':'Neuron Lang examples',
        'pyontutils/neurondm/docs/neurons_notebook.html':'Neuron Lang setup',

        ###
        'Specifications':'Specifications',
        'NIF-Ontology/docs/interlex-spec.html':'InterLex specification',  # Documentation
        'pyontutils/ttlser/docs/ttlser.html':'Deterministic turtle specification',

        ###
        'Other':'Other',
        'augpathlib/README.html': 'augpathlib readme',
        'pyontutils/htmlfn/README.html': 'htmlfn readme',
        'pyontutils/ttlser/README.html': 'ttlser readme',
        'sparc-curation/docs/background.html': '',  # present but not visibly listed
    }

    titles_sparc = {  # TODO abstract this out ...
        'Background': 'Background',
        'sparc-curation/docs/background.html': 'SPARC curation background',
        'Other':'Other',
        'sparc-curation/README.html': 'sparc-curation readme',
    }

    index = [
        '<b class="Components">Components</b>',
        '<b class="Developer docs">Developer docs</b>',
        '<b class="Contributing">Contributing</b>',
        '<b class="Ontology content">Ontology content</b>',
        '<b class="Specifications">Specifications</b>',
        '<b class="Other">Other</b>',
    ]
    for outname, rendered in outname_rendered:
        apath = outname.relative_to(BUILD / 'docs')
        title = titles.get(apath.as_posix(), None)
        # TODO parse out/add titles
        value = atag(apath) if title is None else atag(apath, title)
        index.append(value)
        if not outname.parent.exists():
            outname.parent.mkdir(parents=True)
        with open(outname.as_posix(), 'wt') as f:
            f.write(rendered)

    lt  = list(titles)
    def title_key(a):
        return lt.index(a.split('"')[1])

    index_body = '<br>\n'.join(['<h1>Documentation Index</h1>'] + sorted(index, key=title_key))
    with open((BUILD / 'docs/index.html').as_posix(), 'wt') as f:
        f.write(htmldoc(index_body,
                        title='NIF Ontology documentation index'))

if __name__ == '__main__':
    main()
