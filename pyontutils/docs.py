import os
import sys
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

@suffix('org')
def renderOrg(path):
    # FIXME vs using pandoc...
    orgfile = path.as_posix()
    orgstrap = ['-l', Path(devconfig.git_local_base, 'orgstrap/init.el').as_posix()]
    cmd_line = ['emacs'] + orgstrap + ['--batch', '--visit', orgfile, '-f', 'org-html-export-to-html', '--kill']
    # TODO the easiest way to do this reproducibly is to use jkitchin/scimax
    # to speed things up for CI, it is probably safe to create a zip that has already
    # been bootstrapped, otherwise there will be quite a few weird errors
    print(' '.join(cmd_line))
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
    format = 'gfm'
    cmd_line = ['pandoc', '-f', format, '-t', 'html', mdfile]

    orgstrap = ['-l', Path(devconfig.git_local_base, 'orgstrap/init.el').resolve().as_posix()]
    pandoc = ['pandoc', '-f', format, '-t', 'org', mdfile]
    pandoc_command = ' '.join(pandoc)
    # this appraoch doesn't seem to work for reasons I don't entirely understand, because
    # pasting the joined command works
    # REMINDER never use --eval="(print 'hello)" in python commands needs to be post bash tokenization?? not the issue
    cmd_line = ['emacs'] + orgstrap + ['--batch',
                                       '--eval',
                                       f'"(eshell-command \\"{pandoc_command} > #<buffer convert>\\")"',
                                       #'--eval="(switch-to-buffer \\"convert\\")"',
                                       #'-f', 'org-html-export-to-html',
                                       '--eval',
                                       '"(with-current-buffer \\"convert\\" (org-mode))"',
                                       '--eval',
                                       '"(with-current-buffer \\"convert\\" (org-html-export-as-html))"',
                                       '--eval',
                                        '"(with-current-buffer \\"*Org HTML Export*\\" (princ (buffer-string)))"',
                                       # as-html -> new buffer *Org HTML Export*
                                       #'--kill'
                                      ]

    #cmd_line = ['sh', '/home/tom/test.sh']#, '|', 'tee']
    emacs = ['emacs'] + orgstrap + ['--batch', '-f', 'compile-org-file']

    print(' '.join(cmd_line))
    p = subprocess.Popen(pandoc,
                         stdout=subprocess.PIPE)
    e = subprocess.Popen(emacs,
                         stdin=p.stdout,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    out, err = e.communicate()
    embed()
    return out.decode()

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
    working_dir = Path(__file__).absolute().resolve().parent.parent
    BUILD = working_dir / 'doc_build'
    if not BUILD.exists():
        BUILD.mkdir()

    def outFile(doc, working_dir):
        return BUILD / 'docs' / doc.relative_to(working_dir.parent).with_suffix('.html')

    repos = (Repo(Path(devconfig.ontology_local_repo).resolve().as_posix()),
             Repo(working_dir.as_posix()))

    wd_docs = [(Path(repo.working_dir).resolve(), Path(repo.working_dir, f).resolve())
               for repo in repos
               for f in repo.git.ls_files().split('\n')
               if Path(f).suffix in suffixFuncs]

    outname_rendered = [(outFile(doc, wd), renderDoc(doc)) for wd, doc in wd_docs]

    index = ['<h1>Documentation Index</h1>']
    for outname, rendered in outname_rendered:
        index.append(atag(outname.relative_to(BUILD / 'docs')))  # TODO parse out/add titles
        if not outname.parent.exists():
            outname.parent.mkdir(parents=True)
        with open(outname.as_posix(), 'wt') as f:
            f.write(rendered)

    index_body = '<br>\n'.join(index)
    with open((BUILD / 'docs/index.html').as_posix(), 'wt') as f:
        f.write(htmldoc(index_body, 'NIF Ontology documentation index'))

if __name__ == '__main__':
    main()
