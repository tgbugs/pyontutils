#!/usr/bin/env python3.6
"""Compile all ontology related documentation.

Usage:
    docs [options]

Options:
    -h --help    show this
    -s --spell   run hunspell on all docs

"""
import os
import subprocess
from pathlib import Path
import nbformat
from git import Repo
from joblib import Parallel, delayed
from nbconvert import HTMLExporter
from pyontutils.utils import working_dir, noneMembers, TermColors as tc
from pyontutils.ontutils import tokstrip, _bads
from pyontutils.config import devconfig
from pyontutils.htmlfun import htmldoc, atag
try:
    import hunspell
except ImportError:
    hunspell = None

from IPython import embed

suffixFuncs = {}

def suffix(ext):  # TODO multisuffix?
    def decorator(function):
        suffixFuncs['.' + ext.strip('.')] = function
        return function
    return decorator

def getMdReadFormat():
    p = subprocess.Popen(['pandoc', '--version'], stdout=subprocess.PIPE)
    out, _ = p.communicate()
    version = out.split(b'\n', 1)[0].split(b' ', 1)[-1].decode()
    if version < '2.2.1':
        return 'markdown_github'
    else:
        return 'gfm'

md_read_format = getMdReadFormat()


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
compile_org_file = ['emacs', '-q', '-l', Path(devconfig.git_local_base, 'orgstrap/init.el').resolve().as_posix(), '--batch', '-f', 'compile-org-file']

theme = Path(devconfig.ontology_local_repo, 'docs', 'theme-readtheorg.setup')

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
        org = f.read().replace(theme.name.encode(),
                               theme.as_posix().encode())  # TODO just switch the #+SETUPFILE: line
        #print(org.decode())
        out, err = p.communicate(input=org)

    return out.decode()

@suffix('md')
def renderMarkdown(path, title=None, authors=None, date=None, **kwargs):
    mdfile = path.as_posix()
    # TODO fix relative links to point to github

    pandoc = ['pandoc', '--columns', '300', '-f', md_read_format, '-t', 'org', mdfile]
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
    theme = Path(devconfig.ontology_local_repo, 'docs', 'theme-readtheorg.setup') # TODO can source this directly now?
    header = (f'#+TITLE: {title}\n'
              f'#+AUTHOR: {authors}\n'
              f'#+DATE: {date}\n'
              f'#+SETUPFILE: {theme}\n'
              f'#+OPTIONS: ^:nil num:nil html-preamble:t H:2\n'
              #'#+LATEX_HEADER: \\renewcommand\contentsname{Table of Contents}\n'  # unfortunately this is to html...
             )
    #print(header)

    out, err = s.communicate()
    #print(out.decode())
    org = header.encode() + out.replace(b'\_', b'_')
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
        return suffixFuncs[path.suffix](path, **kwargs)
    except KeyError as e:
        raise TypeError(f'Don\'t know how to render {path.suffix}') from e

def makeKwargs(repo, filepath):
    kwargs = {}
    kwargs['title'] = filepath
    kwargs['authors'] = sorted(name.strip()
                               for name in
                               set(repo.git.log(['--pretty=format:%an%x09',
                                                 filepath]).split('\n')))
    kwargs['date'] = repo.git.log(['-n', '1', '--pretty=format:%aI']).strip()
    return kwargs

def outFile(doc, working_dir, BUILD):
    relative_html = doc.relative_to(working_dir.parent).with_suffix('.html')
    return BUILD / 'docs' / relative_html

def run_all(doc, wd, BUILD, **kwargs):
    return outFile(doc, wd, BUILD), renderDoc(doc, **kwargs)

def main():
    from docopt import docopt
    args = docopt(__doc__)
    BUILD = working_dir / 'doc_build'
    if not BUILD.exists():
        BUILD.mkdir()

    repos = (Repo(Path(devconfig.ontology_local_repo).resolve().as_posix()),
             Repo(working_dir.as_posix()))

    skip_folders = 'notebook-testing',

    # TODO move this into run_all
    wd_docs_kwargs = [(Path(repo.working_dir).resolve(),
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

    if 'CI' in os.environ:
        outname_rendered = [(outFile(doc, wd, BUILD), renderDoc(doc, **kwargs))
                            for wd, doc, kwargs in wd_docs_kwargs]
    else:
        outname_rendered = Parallel(n_jobs=9)(delayed(run_all)(doc, wd, BUILD, **kwargs)
                                              for wd, doc, kwargs in wd_docs_kwargs)

    titles = {
        'Components':'Components',
        'NIF-Ontology/README.html':'Introduction to the NIF Ontology',  # 
        'pyontutils/README.html':'Introduction to pyontutils',
        'pyontutils/ilxutils/README.html':'Introduction to ilxutils',
        'Developer docs':'Developer docs',
        'NIF-Ontology/docs/processes.html':'Ontology development processes (START HERE!)',  # HOWTO
        'NIF-Ontology/docs/development setup.html':'Ontology development setup',  # HOWTO
        'NIF-Ontology/docs/import chain.html':'Ontology import chain',  # Documentation
        'pyontutils/resolver/README.html':'Ontology resolver setup',
        'pyontutils/scigraph/README.html':'Ontology SciGraph setup',
        'NIF-Ontology/docs/external-sources.html':'External sources for the ontology',  # Other
        'Contributing':'Contributing',
        'pyontutils/development/README.html':'Contributing to the ontology',
        'pyontutils/development/community/README.html':'Contributing term lists to the ontology',
        'pyontutils/pyontutils/neuron_models/README.html':'Contributing neuron terminology to the ontology',
        'Ontology content':'Ontology content',
        'NIF-Ontology/docs/brain-regions.html':'Parcellation schemes',  # Ontology Content
        'pyontutils/development/methods/README.html':'Methods and techniques',  # Ontology content
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
