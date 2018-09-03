#!/usr/bin/env python3.6
"""Compile all ontology related documentation.

Usage:
    ont-docs [options]

Options:
    -h --help            show this
    -s --spell           run hunspell on all docs
    -o --docstring-only  build docstrings only
    -j --jobs=NJOBS      number of jobs [default: 9]

"""
import os
import re
import subprocess
from pathlib import Path
from importlib import import_module
import nbformat
from git import Repo
from joblib import Parallel, delayed
from nbconvert import HTMLExporter
from pyontutils.utils import working_dir, TODAY, noneMembers, TermColors as tc
from pyontutils.config import devconfig
from pyontutils.htmlfun import htmldoc, atag
from pyontutils.ontutils import tokstrip, _bads
try:
    import hunspell
except ImportError:
    hunspell = None

from IPython import embed

suffixFuncs = {}

theme = Path(devconfig.ontology_local_repo, 'docs', 'theme-readtheorg.setup') # TODO can source this directly now?


def makeOrgHeader(title, authors, date, theme=theme):
    header = (f'#+TITLE: {title}\n'
              f'#+AUTHOR: {authors}\n'
              f'#+DATE: {date}\n'
              f'#+SETUPFILE: {theme}\n'
              f'#+OPTIONS: ^:nil num:nil html-preamble:t H:2\n'
              #'#+LATEX_HEADER: \\renewcommand\contentsname{Table of Contents}\n'  # unfortunately this is to html...
             )
    #print(header)
    return header


def get__doc__s():
    repo = Repo(working_dir.as_posix())
    paths = sorted(f for f in repo.git.ls_files().split('\n')
                   if f.endswith('.py') and f.startswith('pyontutils'))
    # TODO figure out how to do relative loads for resolver docs
    docs = []
    skip = 'neuron', 'phenotype_namespaces'  # import issues + none have __doc__
    for i, path in enumerate(paths):
        if any(nope in path for nope in skip):
            continue
        ppath = (working_dir / path).absolute()
        #print(ppath)
        module_path = ppath.relative_to(working_dir).as_posix()[:-3].replace('/', '.')
        print(module_path)
        module = import_module(module_path)
        doc = (module.__doc__
               if module.__doc__
               else print(tc.red('WARNING:'), 'no docstring for', module_path))

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


def docstrings(theme=theme):
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
        embed()


# NOTE if emacs does not point to /usr/bin/emacs or similar this will fail
compile_org_file = ['emacs', '-q', '-l',
                    Path(devconfig.git_local_base,
                         'orgstrap/init.el').resolve().as_posix(),
                    '--batch', '-f', 'compile-org-file']


@suffix('org')
def renderOrg(path, **kwargs):
    orgfile = path.as_posix()
    #print(' '.join(compile_org_file))
    p = subprocess.Popen(compile_org_file,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)

    with open(orgfile, 'rb') as f:
        # for now we do this and don't bother with the stream implementaiton of read1 write1
        org = f.read()
        short_theme = theme.name.encode()
        full_theme = theme.as_posix().encode()
        if full_theme not in org:
            org = org.replace(short_theme, full_theme)  # TODO just switch the #+SETUPFILE: line
        #print(org.decode())
        out, err = p.communicate(input=org)

    return out.decode()


@suffix('md')
def renderMarkdown(path, title=None, authors=None, date=None, **kwargs):
    mdfile = path.as_posix()
    # TODO fix relative links to point to github

    if pandoc_columns:
        pandoc = ['pandoc', '--columns', '300', '-f', md_read_format, '-t', 'org', mdfile]
    else:
        pandoc = ['pandoc', '-f', md_read_format, '-t', 'org', mdfile]
    sed = ['sed', r's/\[\[\(.\+\)\]\[\[\[\(.\+\)\]\]\]\]/[[img:\2][\1]]/g']

    p = subprocess.Popen(pandoc,
                         stdout=subprocess.PIPE)
    s = subprocess.Popen(sed,
                         stdin=p.stdout,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    e = subprocess.Popen(compile_org_file,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)  # DUH
    authors = ', '.join(authors)
    header = makeOrgHeader(title, authors, date, theme)
    out, err = s.communicate()
    #print(out.decode())

    org = header.encode() + out.replace(b'\_', b'_').replace(b'[[file:', b'[[./')

    org = org.replace(b'=s', b'= s')  # FIXME need proper fix for inline code

    ## org = org.replace(b'.md][', b'.html][')  # FIXME fix suffixes for doc paths

    #org = re.sub(br'\[(.+\.)[a-z]+\]\[', br'[\1html][', org)
    # [[]] case and [[][]] case
    gitorg = kwargs['org']
    gitrepo = kwargs['repo']
    branch = kwargs['branch']
    dir_ = title.rsplit('/', 1)[0]
    dir_ = '' if dir_ == title else dir_ + '/'
    # fix links
    org = (re.sub(br'\[\[\.\/(.*(?:py|ttl|graphml|yml|yaml|LICENSE))\]\[(.+)\]\]', br'[[https://github.com/'
                                             + f'{gitorg}/{gitrepo}/blob/{branch}/{dir_}'.encode()
                                             + br'\1][\2]]', org))
    org = (re.sub(br'\[\[\.\/(.*(?:py|ttl|graphml|yml|yaml|LICENSE))\]\]', br'[[https://github.com/'
                                             + f'{gitorg}/{gitrepo}/blob/{branch}/{dir_}'.encode()
                                             + br'\1][\1]]', org))
    org = re.sub(br'\[(.+\.)(?:md|org|ipynb)(#[a-z]+)?\]\[', br'[\1html\2][', org)
    # manual fixes FIXME this is bad news we need a mini parser for this
    org = re.sub(b'https://github.com/tgbugs/pyontutils/blob/master/docs/(.+\.html)',
                 b'/'.join([b'..'] * len(dir_.split('/')))  + br'/pyontutils/docs/\1',
                 org)
    org = org.replace(b'https://github.com/tgbugs/pyontutils/blob/master/README.html',
                      b'/'.join([b'..'] * len(dir_.split('/')))  + b'/pyontutils/README.html')
    org = org.replace(b'https://github.com/SciCrunch/NIF-Ontology/blob/master/docs/processes.html',
                      b'/'.join([b'..'] * len(dir_.split('/')))  + b'/NIF-Ontology/docs/processes.html')
    org = org

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
        #embed()
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


def main():
    from docopt import docopt
    args = docopt(__doc__)
    BUILD = working_dir / 'doc_build'
    if not BUILD.exists():
        BUILD.mkdir()

    docstring_kwargs = docstrings()
    wd_docs_kwargs = [docstring_kwargs]
    if args['--docstring-only']:
        outname, rendered = render_docs(wd_docs_kwargs, BUILD, 1)[0]
        if not outname.parent.exists():
            outname.parent.mkdir(parents=True)
        with open(outname.as_posix(), 'wt') as f:
            f.write(rendered)
        return

    repos = (Repo(Path(devconfig.ontology_local_repo).resolve().as_posix()),
             Repo(working_dir.as_posix()),
             Repo(Path(devconfig.git_local_base, 'ontquery').as_posix()))

    skip_folders = 'notebook-testing',

    # TODO move this into run_all
    wd_docs_kwargs += [(Path(repo.working_dir).resolve(),
                        Path(repo.working_dir, f).resolve(),
                        makeKwargs(repo, f))
                       for repo in repos
                       for f in repo.git.ls_files().split('\n')
                       if Path(f).suffix in suffixFuncs
                       and noneMembers(f, *skip_folders)]

    # doesn't work because read-from-minibuffer cannot block
    #compile_org_forever = ['emacs', '-q', '-l',
                           #Path(devconfig.git_local_base,
                                #'orgstrap/init.el').resolve().as_posix(),
                           #'--batch', '-f', 'compile-org-forever']
    #org_compile_process = subprocess.Popen(compile_org_forever,
                                           #stdin=subprocess.PIPE,
                                           #stdout=subprocess.PIPE,
                                           #stderr=subprocess.PIPE)

    if args['--spell']:
        spell((f.as_posix() for _, f, _ in wd_docs_kwargs))
        return

    outname_rendered = render_docs(wd_docs_kwargs, BUILD, int(args['--jobs']))

    titles = {
        'Components':'Components',
        'NIF-Ontology/README.html':'Introduction to the NIF Ontology',  # 
        'pyontutils/README.html':'Introduction to pyontutils',
        'ontquery/README.html':'Introduction to ontquery',
        'pyontutils/ilxutils/README.html':'Introduction to ilxutils',

        'Developer docs':'Developer docs',
        'NIF-Ontology/docs/processes.html':'Ontology development processes (START HERE!)',  # HOWTO
        'NIF-Ontology/docs/development setup.html':'Ontology development setup',  # HOWTO
        'NIF-Ontology/docs/import chain.html':'Ontology import chain',  # Documentation
        'pyontutils/resolver/README.html':'Ontology resolver setup',
        'pyontutils/scigraph/README.html':'Ontology SciGraph setup',
        'pyontutils/docstrings.html':'Command line programs',
        'NIF-Ontology/docs/external-sources.html':'External sources for the ontology',  # Other

        'Contributing':'Contributing',
        'pyontutils/development/README.html':'Contributing to the ontology',
        'pyontutils/development/community/README.html':'Contributing term lists to the ontology',
        'pyontutils/pyontutils/neuron_models/README.html':'Contributing neuron terminology to the ontology',

        'Ontology content':'Ontology content',
        'NIF-Ontology/docs/brain-regions.html':'Parcellation schemes',  # Ontology Content
        'pyontutils/development/methods/README.html':'Methods and techniques',  # Ontology content
        'NIF-Ontology/docs/Neurons.html':'Neuron Lang overview',
        'pyontutils/docs/NeuronLangExample.html':'Neuron Lang examples',
        'pyontutils/docs/neurons_notebook.html':'Neuron Lang setup',

        'Specifications':'Specifications',
        'NIF-Ontology/docs/interlex-spec.html':'InterLex specification',  # Documentation
        'pyontutils/docs/ttlser.html':'Deterministic turtle specification',
    }
        
    index = [
        '<b class="Components">Components</b>',
        '<b class="Developer docs">Developer docs</b>',
        '<b class="Contributing">Contributing</b>',
        '<b class="Ontology content">Ontology content</b>',
        '<b class="Specifications">Specifications</b>',
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
