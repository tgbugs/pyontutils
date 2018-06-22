import os
import subprocess
from pathlib import Path
import nbformat
from git import Repo
#from markdown import markdown
from nbconvert import HTMLExporter
from pyontutils.config import devconfig
from protcur.core import htmldoc, atag
from IPython import embed

suffixFuncs = {}

def suffix(ext):  # TODO multisuffix?
    def decorator(function):
        suffixFuncs['.' + ext.strip('.')] = function
        return function
    return decorator


def isdoc(filename):
    return any(filename.endswith(ext) for ext in suffixFuncs)

@suffix('org')
def renderOrg(path):
    # FIXME vs using pandoc...
    orgfile = path.as_posix()
    cmd_line = ['emacs', '--batch', '--visit', orgfile, '-f', 'org-html-export-to-html', '--kill']
    scimax_init = ['-l', 'scimax/init.el']  # can trigger fetching many files on an unsuspecting system
    # TODO the easiest way to do this reproducibly is to use jkitchin/scimax
    # to speed things up for CI, it is probably safe to create a zip that has already
    # been bootstrapped, otherwise there will be quite a few weird errors
    #print(' '.join(cmd_line))
    p = subprocess.Popen(cmd_line,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    out, err = p.communicate()
    outpath = path.with_suffix('.html')
    with open(outpath.as_posix(), 'rt') as f:
        return f.read()

@suffix('md')
def renderMarkdown(path):
    mdfile = path.as_posix()
    #with open(mdfile, 'rt') as f:
    # TODO fix relative links to point to github
    #body = markdown(f.read())

    format = 'markdown_github'  # TODO newer version has 'gfm' but apparently I'm not on latest?
    cmd_line = ['pandoc', '-f', format, '-t', 'html', mdfile]
    print(' '.join(cmd_line))

    p = subprocess.Popen(cmd_line,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    out, err = p.communicate()

    body = out.decode()

    title = path.name

    return htmldoc(body, title)

@suffix('ipynb')
def renderNotebook(path):
    nbfile = path.as_posix()
    with open(nbfile, 'rt') as f:
        notebook = nbformat.read(f, as_version=4)
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'full'
    body, resources = html_exporter.from_notebook_node(notebook)
    return body

def renderDoc(path):
    # TODO add links back to github and additional prov for generation
    try:
        return suffixFuncs[path.suffix](path)
    except KeyError as e:
        raise TypeError(f'Don\'t know how to render {path.suffix}') from e

def main():
    working_dir = Path(__file__).absolute().parent.parent
    BUILD = working_dir / 'doc_build'
    if not BUILD.exists():
        BUILD.mkdir()
    #os.chdir(BUILD)
    def outFile(doc):
        return BUILD / doc.relative_to(devconfig.git_local_base).with_suffix('.html')
    repos = (Repo(devconfig.ontology_local_repo),
             Repo(working_dir.as_posix()))

    docs = [Path(repo.working_dir, f)  # .relative_to(BUILD)  # it doesn't do full relative paths... wat
            for repo in repos
            for f in repo.git.ls_files().split('\n')
            if isdoc(f)]

    outname_rendered = [(outFile(doc), renderDoc(doc)) for doc in docs]

    index = ['<h1>Documentation Index</h1>']
    for outname, rendered in outname_rendered:
        index.append(atag(outname.relative_to(BUILD)))  # TODO parse out/add titles
        if not outname.parent.exists():
            outname.parent.mkdir(parents=True)
        with open(outname.as_posix(), 'wt') as f:
            f.write(rendered)

    index_body = '<br>\n'.join(index)
    with open((BUILD / 'index.html').as_posix(), 'wt') as f:
        f.write(htmldoc(index_body, 'NIF Ontology documentation index'))

    if __name__ == '__main__':
        embed()

if __name__ == '__main__':
    main()
