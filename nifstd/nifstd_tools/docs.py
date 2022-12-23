#!/usr/bin/env python3
import tempfile
from pyontutils.config import auth
from augpathlib import RepoPath as Path
temp_path = Path(tempfile.tempdir)
_ddconf = auth.get_path('resources') / 'doc-config.yaml'
_ddpath = temp_path / 'build-ont-docs' / 'docs'
glb = Path(auth.get_path('git-local-base'))
_theme_repo = glb / 'org-html-themes'
_theme_path = 'org/theme-readtheorg-local.setup'
__doc__ = f"""Compile all documentation from git repos.

Usage:
    ont-docs [options] [--repo=<REPO>...]
    ont-docs render [options] <path>...

Options:
    -h --help             show this
    -c --config=<PATH>    path to doc-index.yaml [default: {_ddconf}]
    -o --out-path=<PATH>  path inside which docs are built [default: {_ddpath}]
    -b --html-root=<REL>  relative path to the html root [default: ..]
    -s --spell            run hunspell on all docs
    -d --docstring-only   build docstrings only
    -j --jobs=NJOBS       number of jobs [default: 9]
    -r --repo=<REPO>      additional repos to crawl for docs
    --theme=<THEMEPATH>   path to theme inside theme-repo [default: {_theme_path}]
    --theme-repo=<REPO>   path to theme [default: {_theme_repo}]
    --debug               redirect stderr to debug pipeline errors

"""
import os
import re
import ast
import shutil
import logging
import subprocess
from pathlib import PurePath
from urllib.parse import urlparse
from importlib import import_module
import yaml
import htmlfn as hfn
import nbformat
from git import Repo
from joblib import Parallel, delayed
from nbconvert import HTMLExporter
from augpathlib import exceptions as aexc
from pyontutils import clifun as clif
from pyontutils.utils import TODAY, noneMembers, makeSimpleLogger, isoformat
from pyontutils.utils import TermColors as tc, get_working_dir
from pyontutils.utils import asStr, findAssignToName
from pyontutils.ontutils import tokstrip, _bads

# TODO collect images and serve them locally

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
        f.write(dat.replace('="src/', '="/docs/src/'))


def augmentExisting(header, title, authors, date, theme, path):
    def tf(line): return line if line else f'#+TITLE: {title}'
    def af(line):
        if line:
            existing = [a.strip().rstrip()
                        for a in line.split(':', 1)[-1].split(',')]
            all_authors = existing + [a for a in authors if a not in existing]
        else:
            all_authors = authors

        astr = ', '.join(all_authors)
        return f'#+AUTHOR: {astr}'
    def df(line): return f'#+DATE: {date}'
    def of(line):
        # ensure that we always have a table of contents even if the file
        # wants it disabled other export cases
        default = '#+OPTIONS: toc:t'  # not strictly necessary, but a good starter
        always = ' num:nil'

        return ((line.replace('toc:nil', 'toc:t')
                 if 'toc:nil' in line else line)
                if line else default) + always
    def sf(line):
        # we need to ensure that the theme is present we set it first
        # so that the file specified #+setupfile: can override
        stheme = f'#+SETUPFILE: {theme}'
        def fixpath(l):
            path
            _prefix, _spath = l.split(':', 1)
            spath = _spath.strip()
            p = Path(spath)
            if not p.is_absolute():
                # FIXME really need to forward the error stream,
                # missing #+setupfile: entries show up in messages
                npath = (path.parent / p).resolve()
                nspath = npath.as_posix()
            else:
                nspath = spath

            return _prefix + ': ' + nspath

        return stheme + '\n' + fixpath(line) if line else stheme

    sections = (('#+title:', tf),
                ('#+author:', af),
                ('#+date:', df),
                ('#+options:', of),
                ('#+setupfile:', sf),)

    lines = header.split('\n')
    for head, func in sections:
        for i, line in enumerate(tuple(lines)):
            if line.lower().startswith(head):
                if head == '#+title:':
                    title = line.split(':', 1)[-1].strip()

                lines[i] = func(line)
                break
        else:
            lines.append(func(None))

    return '\n'.join(lines) + '\n', title


ob_lang_titles = (
    ('jupyter-python', 'Python'),
    ('sparql', 'SPARQL'),
    ('cypher', 'Cypher'),
    ('elisp', 'Emacs Lisp'),
    ('powershell', 'Powershell'),
    ('dockerfile', 'Dockerfile'),
    ('json', 'JSON'),
)

ob_lang_css = ' '.join([
    f"pre.src-{lang}:before  {{ content: '{display}'; }}"
    for lang, display in ob_lang_titles])

todo_colors_css = (
    '.todo.RC {color:black; background-color:khaki;}'
)


def makeOrgHeader(title, authors, date, theme, edit_link=None,
                  existing=None, path=None):
    if existing is not None:
        existing = existing.decode()
        header, title = augmentExisting(
            existing, title, authors, date, theme, path)

    else:
        header = (f'#+TITLE: {title}\n'
                  f'#+AUTHOR: {", ".join(authors)}\n'
                  f'#+DATE: {date}\n'
                  f'#+SETUPFILE: {theme}\n'
                  f'#+OPTIONS: ^:nil num:nil html-preamble:t H:2\n'
                  # unfortunately this is to html...
                  #'#+LATEX_HEADER: \\renewcommand\contentsname{Table of Contents}\n'
                )

    # at some point org-html-themes removed the default html-style
    # so we add it back
    header += '#+OPTIONS: html-style:t\n'
    # fill in missing langs
    header += f'#+HTML_HEAD: <style>{ob_lang_css}{todo_colors_css}</style>\n'

    # FIXME we need to work our way back from the top within the header
    # so can correctly add this before anything else, which was not an
    # issue when we were splitting from the start instead of the end of
    # the zeroth section
    if edit_link is not None:
        # XXX in this approach have to override org-html-template
        # because by default they are not in the content, which is
        # where the toc is so the link up is hidden behind the toc
        header += f'#+HTML_LINK_UP: {title}\n#+HTML_LINK_HOME: {edit_link}\n'

    return header


def file_git_metadata(file, *, nogiterr=None):
    current_file = Path(file).resolve()
    working_dir = current_file.working_dir
    if working_dir is None:
        # cannot proceed without git
        log.warning(f'Not in repo, not fixing links for {current_file}')
        if nogiterr:
            raise nogiterr()
        else:
            return [None] * 8

    repo = working_dir.repo
    repo_name = working_dir.name
    remote_url = next(repo.remote().urls)
    if remote_url.startswith('/'):
        # cloned locally case
        remote_url = next(Path(remote_url).repo.remote().urls)

    if remote_url.startswith('git@'):
        remote_url = 'ssh://' + remote_url

    duh = urlparse(remote_url)
    netloc = duh.netloc

    if 'github' in netloc:
        netloc_raw = 'raw.githubusercontent.com'
    else:
        raise NotImplementedError(f"don't know raw for: {remote_url}")

    if netloc.startswith('git@github.com'):
        _, group = netloc.split(':')
        netloc = 'github.com'

    elif netloc == 'github.com':
        _, group, *rest = duh.path.split('/')
    else:
        raise NotImplementedError(remote_url)

    return current_file, working_dir, repo, repo_name, remote_url, netloc, netloc_raw, group


class FixLinks:
    # link pattern follows laundry's implementation
    hlc = rb'((?:[^\[\]]|\\\[|\\\])+)'
    link_pattern = re.compile(rb'\[\[' + hlc + rb'(?:\]\[' + hlc + rb')?\]\]', re.S)

    class MakeMeAnInlineSrcBlock(Exception):
        """ EVIL """

    class NoGitError(Exception):
        """ also evil """

    def __init__(self, current_file, verbatim_untracked_missing=True):
        self.verbatim_untracked_missing = verbatim_untracked_missing
        try:
            (
                self.current_file,
                self.working_dir,
                self.repo,
                self.repo_name,
                self.remote_url,
                self.netloc,
                self.netloc_raw,
                self.group,
            ) = file_git_metadata(current_file, nogiterr=self.NoGitError)
        except self.NoGitError:
            self.__call__ = lambda org: org

    def __call__(self, org):
        # run these once at the start
        org = re.sub(rb'\[\[\.\/', b'[[file:', org)  # start from same folder
        org = re.sub(rb'\[\[\.\.\/', b'[[file:../', org)  # relative
        org = re.sub(rb'\[\[~/', b'[[file:~/', org)  # home dir refs
        org = re.sub(rb'\[\[file:::', b'[[file:#', org)  # internal/external (new buffer) fuzzy refs (don't use)

        out = re.sub(self.link_pattern, self.process_matches, org)
        return out

    def process_matches(self, match):
        href, *text = match.groups()
        # (log.info(f'probably bad href match {href!r} {text!r}') if b':' not in href and b' ' in href else log.debug(f'{href!r} {text!r}'))
        if text:
            text, = text

        try:
            if text is None:
                #log.debug(f'single link case {href!r}')
                outlink = b'[[' + self.fix_href(href) + b']]'
            else:
                badmatch = b'\n\n' in text  # empty lines end paragraphs, so no links
                ft = (lambda t, h: t if t else h) if badmatch else self.fix_text
                outlink = b'[[' + self.fix_href(href) + b'][' + ft(text, href) + b']]'
        except self.MakeMeAnInlineSrcBlock as e:
            if text and text.startswith(b'~'):
                tolink = text
            else:
                tolink = href

            outlink = f'={tolink.decode().replace("file:", "")}='.encode()

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

        fragment = '#' + up.fragment if up.fragment else ''
        query = '?' + query if up.query else ''
        dir_stem, old_suffix = rest.rsplit('.', 1)
        local_path = dir_stem + '.html'
        path = f'/docs/{project}/' + local_path + query + fragment
        out = 'hrefl:' + path
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
            verbatim_untracked_missing = self.verbatim_untracked_missing
            def __init__(self, base, mmaisb=self.MakeMeAnInlineSrcBlock):
                self.base = base
                self.MakeMeAnInlineSrcBlock = mmaisb  # lol

            def __call__(self, match):
                name, suffix, rest = match.groups()

                if rest is None:
                    rest = ''
                elif rest.startswith('::'):
                    # normalize org :: links to work for html
                    rest = (rest[2:] if rest.startswith('::#') else '#' + rest[2:])

                if rest:
                    log.log(9, rest)

                # FIXME somehow truncating fragments?
                if not any(name.startswith(p) for p in ('$', '#', '~/')):
                    base = self.base
                    if self.working_dir is None:
                        log.warning('no working directory found, you will have broken links')
                        rel = Path(name + suffix)
                    else:
                        link_target = (self.current_file.parent /
                                       (name + suffix)).resolve()
                        if link_target.is_dir():
                            base = base.replace('/blob/', '/tree/')  # XXX HACK for github
                        elif not self.verbatim_untracked_missing:
                            pass  # early exit so the next two don't trigger
                        elif not link_target.exists():
                            msg = f'link to nonexistent file {link_target}'
                            log.warning(msg)
                            raise self.MakeMeAnInlineSrcBlock(link_target)
                        elif not list(link_target.commits(max_count=1)):
                            msg = ('link to file not tracked by git, '
                                   f'likely a transient tangle {link_target}')
                            log.warning(msg)
                            raise self.MakeMeAnInlineSrcBlock(link_target)

                        # TODO detect tangled files and flag them
                        try:
                            rel = link_target.relative_to(self.working_dir)
                        except ValueError as e:
                            try:
                                # alternate repo case
                                if link_target.working_dir:
                                    # a bit of rework, but handles all our logic for us
                                    # FIXME this is a hack that we shouldn't have to use
                                    # for some reason the relative paths stack if you use
                                    # link_target by itself
                                    ncf = link_target.working_dir / link_target.repo_relative_path.parts[0]
                                    orc = FixLinks(ncf).fix_href(
                                        (b'file:' +
                                         link_target
                                         .repo_relative_path
                                         .as_posix()
                                         .encode()))

                                    return orc.decode() + rest
                                else:
                                    # FIXME raise error here?
                                    return name + suffix + rest
                            except Exception as e2:
                                log.exception(e2)
                                log.error(f'path went outside current repo {link_target}')
                                return name + suffix + rest

                    if suffix in ('.md', '.org', '.ipynb'):
                        rel = rel.with_suffix('.html')

                    rel_path = rel.as_posix() + rest
                    return base + rel_path
                elif name.startswith('$') or name.startswith('~/'):
                    log.log(9, f'inline verbatim for {name}{suffix}{rest}')
                    raise self.MakeMeAnInlineSrcBlock(match.group())
                else:
                    return match.group()


        # tirgger the $ error in the stupidest posible way
        sub_nothing = SubRel(f"we're off to see the inline src block maker")
        out_m1 = re.sub(r'^file:(\$|~/)([^#]*)(#.+)?$', sub_nothing, out)

        if self.working_dir is None:
            msg = 'no working directory found, you will have broken links'
            log.warning(msg)

        #print('----------------------------------------')
        # TODO consider htmlifying these ourselves and serving them directly
        # FIXME /master/ vs /dev/ for NIF-Ontology
        sub_github = SubRel(f'https://{self.netloc}/{self.group}/{self.repo_name}/blob/master/')
        # source file and/or code extensions regex
        # XXX note, for folders to direct to the forge make sure the link ends with /
        # the link checker will usually catch them for you if you miss
        code_regex = (r'(\.(?:el|py|sh|ttl|graphml|yml|yaml|spec|example|xlsx|csv|rkt|lisp)'
                      r'|LICENSE|catalog-extras|authorized_keys|\.vimrc|/)')
        out0 = re.sub(r'^file:(.*)'
                      + code_regex +
                      r'(#.+)?$',
                      sub_github, out_m1)

        #print('----------------------------------------')
        # FIXME for the future, can't hotlink to svg from github
        #sub_github_raw = SubRel(f'https://{self.netloc_raw}/{self.group}/{self.repo_name}/master/')
        #out0_5 = re.sub(r'^file:(.*)' +
        #                r'(\.svg)' +
        #                r'(#.+)*$',
        #                sub_github_raw, out0)

        #print('----------------------------------------')
        # FIXME won't work if the outer folder does not match the github project name
        # FIXME possibly related to apinatomy.org failing to resolve scigraph/README.org::#stuff
        sub_docs = SubRel(f'hrefl:/docs/{self.repo_name}/')
        out1 = re.sub(r'^file:(.*)'
                      r'(\.(?:md|org|ipynb))'
                      r'((?:::#?|#).+)?$',
                      #r'(?:::)?(#.+)?$',
                      sub_docs, out0)
        out = out1
        #print('----------------------------------------')

        if not any(out.startswith(s) for s in (
                'https:', 'http:', 'hrefl:', 'file:', 'img:', 'mailto:',
                'tramp:', 'info:', 'man:', '/', '#')):
            if (' ' in out or
                '${' in out):
                # watch out for bash if [[ ]] cases, not guranteed, but safer
                log.debug(
                    f'skip likely bash if test  {out!r} in {self.current_file}')
            elif (out.startswith('(') and out.endswith(')') or  # coderef, let elisp sort it out
                  out.startswith('{') and out.endswith('}') or  # skip python code that generates org links (lol)
                  out.startswith(':') and out.endswith(':')  # regex :space: etc.
                  ):
                pass
            elif (not out.startswith('*') and  # not a fuzzy heading match
                  not ':' in out and  # curies
                  not Path(out).exists()  # no unprefixed reference to a file
                  ):
                # guess fuzzy link, hope we hit a code block or something
                out = 'file:::#' + out
                log.info(
                    f'fuzzy link transformed to {out!r} in {self.current_file}')
            else:
                log.warning(
                    f'Potentially relative path {out!r} does not '
                    f'have a known good start in {self.current_file}')

        return out.encode()


def get__doc__s(repo_paths, skip_folders, skip):
    paths = sorted(
        rp / f for rp in repo_paths
        if not print(rp, rp.name, skip.get(rp.name, None))
        for f in rp.repo.git.ls_files().split('\n')
        if f.endswith('.py')
        and not f.startswith('test')
        and not [sf for sf in skip_folders if sf in f]
        and not f in skip.get(rp.name, tuple())
        and not print(f)

        #and any(f.startswith(n) for n in ('pyontutils', 'ttlser', 'nifstd', 'neurondm'))  # FIXME hardcoded
    )
    # TODO figure out how to do relative loads for resolver docs
    docs = []
    #skip = 'neuron', 'phenotype_namespaces'  # import issues + none have __doc__
    skip = 'ilxcli', 'deploy', 'test',  # FIXME move to config
    for i, ppath in enumerate(paths):
        path = ppath.repo_relative_path.as_posix()
        if any(nope in path for nope in skip):
            continue
        #print(ppath)
        module_path = ppath.repo_relative_path.as_posix()[:-3].replace('/', '.')
        #print(module_path)

        with open(ppath, 'rt') as f:
            tree = ast.parse(f.read())

        doc = ast.get_docstring(tree)

        if doc is None:
            maybe__doc__ = findAssignToName('__doc__', tree.body)

            if maybe__doc__:  # FIXME warn on multi?
                i, n = maybe__doc__[0]
                prior = tree.body[:i]
                #_values = [asStr(v, prior) for v in n.value.values]
                #doc = ''.join(_values)
                doc = asStr(n.value, prior)
                if isinstance(n.value, ast.JoinedStr):
                    doc = ast.literal_eval(doc)
                if doc.startswith("'"):
                    breakpoint()
                    doc = ast.literal_eval(doc)

            else:
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


def makeDocstrings(BUILD, repo_paths, skip_folders, skip):
    docstr_file = 'docstrings.org'
    docstr_path = BUILD / docstr_file
    title = 'Command line programs and libraries'
    authors = ['various']
    date = TODAY()  # FIXME midnight issues
    docstr_kwargs = (docstr_path, docstr_path,
                     {'authors': authors,
                      'date': date,
                      'title': title,
                      'org': '',
                      'repo': '',
                      'branch': 'master',
                     })
    docstrings = get__doc__s(repo_paths, skip_folders, skip)

    done = []
    dslist = []
    for type, module, docstring in docstrings:
        if type not in done:
            done.append(type)
            dslist.append(f'* {type}')
        if docstring is not None:
            dslist.append(f'** {module}\n#+BEGIN_SRC\n{docstring}\n#+END_SRC')

    docstrings_org = '\n'.join(dslist)
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
orgstrap_init = (glb / 'orgstrap/init.el').resolve()
docs_init = (auth.get_path('resources') / 'docs-init.el').resolve()


def argv_compile_org_file(*, emacs='emacs', hlv=False):
    fun = 'compile-org-file-hlv' if hlv else 'compile-org-file'
    return [emacs,
            '--batch',
            '--quick',
            '--load', orgstrap_init.as_posix(),
            '--load', docs_init.as_posix(),
            '--funcall', fun]


first_sep = re.compile(b'^[^#\n]|\n\n|\n#+(begin_src|BEGIN_SRC)', re.MULTILINE)
first_heading = re.compile(b'^\*+[\ \t]', re.MULTILINE)


@suffix('org')
def renderOrg(path, debug=False, hlv=False, **kwargs):
    orgfile = path.as_posix()
    try:
        ref = path.latest_commit().hexsha
        github_link = path.remote_uri_human(ref=ref)
    except (aexc.NoCommitsForFile, aexc.NotInRepoError):
        github_link = None

    #print(' '.join(argv_compile_org_file(hlv=hlv)))
    p = subprocess.Popen(argv_compile_org_file(hlv=hlv),
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE if debug else subprocess.DEVNULL)

    with open(orgfile, 'rb') as f:
        # for now we do this and don't bother with the stream implementaiton of read1 write1
        org_in = f.read()

    title = kwargs['title']
    authors = kwargs['authors']
    date = kwargs['date']
    theme = kwargs['theme']

    repo = kwargs['repo']
    _title = PurePath(repo + '/' + title).with_suffix('.html').as_posix()
    title = (kwargs['titles'][_title]
            if 'titles' in kwargs and _title in kwargs['titles'] else
            title)

    try:
        if org_in.startswith(b'* '):
            title_author_etc = makeOrgHeader(title, authors, date, theme,
                                             github_link, path=path)
            org = title_author_etc.encode() + org_in
        else:
            match = first_heading.search(org_in)  # zeroth section
            #match = first_sep.search(org_in)
            if match is None:
                breakpoint()
            start = match.start()
            existing, rest = org_in[:start], org_in[start:]
            title_author_etc = makeOrgHeader(title, authors, date, theme,
                                             github_link, existing,
                                             path=path)
            org = (title_author_etc.encode() +
                   rest)
    except ValueError as e:
        log.exception(e)
        title_author_etc = makeOrgHeader(title, authors, date, theme,
                                         github_link, path=path)
        org = title_author_etc.encode() + org_in
        #raise ValueError(f'{orgfile!r}') from e

    # fix links
    fix_links = FixLinks(path)
    org = fix_links(org)

    out, err = p.communicate(input=org)
    if not out and not err or p.returncode != 0:
        log.critical(f'No output and no error for {path}\n'
                     'Set --debug to dump to file.')

    if debug:
        with open(temp_path / f'debug-{path.name}', 'wb') as f:
            f.write(org)

    if p.returncode != 0:
        msg = (f'building {orgfile} failed with {p.returncode}\nout:\n'
               f'{out.decode()}\nerr:\n{err}')
        raise ValueError(msg)

    return out.decode()


@suffix('md')
def renderMarkdown(path, title=None, authors=None, date=None, theme=None,
                   debug=False, **kwargs):
    mdfile = path.as_posix()
    try:
        ref = path.latest_commit().hexsha
        github_link = path.remote_uri_human(ref=ref)
    except aexc.NoCommitsForFile:
        github_link = None

    # TODO fix relative links to point to github

    if pandoc_columns:
        pandoc = ['pandoc',
                  '--columns', '600',
                  '-f', md_read_format,
                  '-t', 'org',
                  mdfile]
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
    e = subprocess.Popen(argv_compile_org_file(),
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=(subprocess.PIPE
                                 # do not set STDOUT on debug, produces garbage
                                 if debug else
                                 subprocess.PIPE))

    repo = kwargs['repo']
    _title = PurePath(repo + '/' + title).with_suffix('.html').as_posix()
    title = (kwargs['titles'][_title]
            if 'titles' in kwargs and _title in kwargs['titles'] else
            title)

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

    #if b'hrefl:' in org or b'img:' in org:
        #with open(temp_path / (f'debug-{path.as_posix().replace("/", "-")}' + '.org'), 'wb') as f:
            #f.write(org)

    # debug debug
    #with open(path.with_suffix('.org').as_posix(), 'wb') as f:
        #f.write(org)
    # there is not satisfactory way to fix this issue right now
    # but it might also be a bug in pandoc's org exporter

    body, err = e.communicate(input=org)

    # debug
    #print(' '.join(pandoc), '|', ' '.join(sed), '|', ' '.join(argv_compile_org_file()))
    #if b'[[img:' in out or not out or 'external-sources' in path.as_posix():
        #breakpoint()

    if debug:
        with open(temp_path / f'debug-{path.with_suffix(".org").name}', 'wb') as f:
            f.write(org)

    if e.returncode:
        # if this happens direct stderr to stdout to get the message
        if err is not None:
            err = err.strip(b'Created img link.\n')  # FIXME lack of distinc STDERR is very annoying

            raise subprocess.CalledProcessError(
                e.returncode, ' '.join(e.args) +
                f' failed for {path.as_posix()}') from ValueError(err.decode())
        else:
            raise subprocess.CalledProcessError(
                e.returncode, ' '.join(e.args) +
                f' failed for {path.as_posix()}') from ValueError(body.decode())

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
    #html_exporter.template_file = 'full'
    body, resources = html_exporter.from_notebook_node(notebook)
    return body


def renderDoc(path, debug=False, **kwargs):
    # TODO add links back to github and additional prov for generation
    print('========================================')
    print(path)
    try:
        # renderMarkdown # renderOrg
        return suffixFuncs[path.suffix](path, debug=debug, **kwargs)
    except KeyError as e:
        raise TypeError(f'Don\'t know how to render {path.suffix}') from e


def makeKwargs(repo_path, filepath, doc_config):
    path = repo_path / filepath
    kwargs = {}
    kwargs['title'] = filepath
    kwargs['authors'] = sorted(
        name.strip()
        for name in
        set(repo_path.repo.git.log(['--follow',
                                    '--pretty=format:%an%x09',
                                    filepath]).split('\n')))
    kwargs['date'] = isoformat(path.latest_commit().authored_datetime)
    repo_url = Path(next(next(r for r in repo_path.repo.remotes
                              if r.name == 'origin').urls))
    kwargs['org'] = repo_url.parent.name
    kwargs['repo'] = repo_url.stem
    kwargs['branch'] = 'master'  # TODO figure out how to get the default branch on the remote
    kwargs['hlv'] = filepath in doc_config['hlv']

    return kwargs


def outFile(doc, working_dir, out_path):
    relative_html = doc.relative_to(working_dir.parent).with_suffix('.html')
    return out_path / relative_html


def run_all(doc, wd, out_path, titles=None, debug=False, logfix=False, **kwargs):
    # workaround for joblib 692 that only creates the logger once
    # workaround for incorrect behavior in old versions of makeSimpleLogger
    log = logging.getLogger('ont-docs')
    if not log.handlers:
        log = makeSimpleLogger('ont-docs')

    return (outFile(doc, wd, out_path),
            renderDoc(doc, titles=titles, debug=debug, **kwargs))


def render_docs(wd_docs_kwargs, out_path, titles=None, n_jobs=9, debug=False):
    if titles is None:
        titles = {}

    # FIXME collect errors so we can see everything that fails in a single pass
    if 'CI' in os.environ or n_jobs == 1:
        outname_rendered = [
            (outFile(doc, wd, out_path),
             renderDoc(doc, titles=titles,
                       debug=debug, **kwargs))
            for wd, doc, kwargs in wd_docs_kwargs]
    else:
        outname_rendered = Parallel(n_jobs=n_jobs)(
            delayed(run_all)(doc, wd, out_path, titles=titles,
                             debug=debug, logfix=not i, **kwargs)
            for i, (wd, doc, kwargs) in enumerate(wd_docs_kwargs))
    return outname_rendered


def deadlink_check(html_file):
    """ TODO """


def prepare_paths(BUILD, out_path, theme_repo, theme):
    patch_theme_setup(theme)

    if not BUILD.exists():
        BUILD.mkdir()

    if not out_path.exists():
        out_path.mkdir()

    theme_styles_dir = theme_repo / 'src'
    doc_styles_dir = out_path / 'src'
    if doc_styles_dir.exists():
        shutil.rmtree(doc_styles_dir)

    shutil.copytree(theme_styles_dir, doc_styles_dir)

    # this is tricky
    #images_dir = out_path / 'images'
    #if images_dir.exists():
        #shutil.rmtree(images_dir)

    #images_dir.mkdir()
    #shutil.copy(image, images_dir)


def only(repo_path, file):
    """ for debugging specific files """
    #and Path(repo.working_dir).name == 'NIF-Ontology' and f == 'README.md'  # DEBUG
    #and Path(repo.working_dir).name == 'pyontutils' and f == 'README.md'  # DEBUG
    #and Path(repo.working_dir).name == 'sparc-curation' and f == 'docs/setup.org'  # DEBUG
    return True


class Options(clif.Options):

    @property
    def config(self):
        return Path(self._args['--config'])

    @property
    def jobs(self):
        return int(self._args['--jobs'])

    @property
    def out_path(self):
        return Path(self._args['--out-path']).expanduser()

    @property
    def BUILD(self):
        return (self.out_path / self.html_root).resolve()

    @property
    def paths(self):
        return [Path(string_path).resolve()
                for string_path in self._args['<path>']]

    @property
    def theme_repo(self):
        return Path(self._args['--theme-repo']).expanduser()

    @property
    def theme(self):
        return self.theme_repo / self._args['--theme']


class Main(clif.Dispatcher):

    @property
    def _doc_config(self):
        with open(self.options.config, 'rt') as f:
            return yaml.safe_load(f)

    def _sanity_check(self):
        if not orgstrap_init.exists():
            msg = ('Required file orstrap/init.el not found. '
                   f'Did you clone orgstrap? {orgstrap_init}')
            raise FileNotFoundError(msg)

    def render(self):
        self._sanity_check()
        prepare_paths(
            self.options.BUILD,
            self.options.out_path,
            self.options.theme_repo,
            self.options.theme)
        doc_config = self._doc_config
        wd_docs_kwargs = [
            (path.working_dir,
             path,
             makeKwargs(path.working_dir, path.repo_relative_path.as_posix(), doc_config))
            for path in self.options.paths]
        [kwargs.update({'theme': self.options.theme}) for _, _, kwargs in wd_docs_kwargs]
        outname_rendered = render_docs(wd_docs_kwargs,
                                       self.options.out_path,
                                       titles=None,
                                       n_jobs=self.options.jobs,
                                       debug=self.options.debug)
        for outname, rendered in outname_rendered:
            outpath = self.options.out_path / outname
            outpath.parent.mkdir(parents=True, exist_ok=True)
            with open(outpath, 'wt') as f:
                f.write(rendered)
            log.info(f'org file rendered to {outpath}')

    def default(self):
        self._sanity_check()
        out_path = self.options.out_path
        BUILD = self.options.BUILD

        prepare_paths(BUILD, out_path, self.options.theme_repo, self.options.theme)

        doc_config = self._doc_config
        names = tuple(doc_config['repos']) + tuple(self.options.repo)  # TODO fetch if missing ?
        repo_paths = [(glb / name).resolve() for name in names]
        repos = [p.repo for p in repo_paths]
        skip_folders = doc_config.get('skip-folders', tuple())
        rskip = doc_config.get('skip', {})

        # TODO move this into run_all
        docstring_kwargs = makeDocstrings(BUILD, repo_paths, skip_folders, rskip)
        wd_docs_kwargs = [docstring_kwargs]
        if self.options.docstring_only:
            [kwargs.update({'theme': theme})
            for _, _, kwargs in wd_docs_kwargs]
            outname, rendered = render_docs(wd_docs_kwargs, out_path,
                                            titles=None,
                                            n_jobs=1,
                                            debug=self.options.debug)[0]
            if not outname.parent.exists():
                outname.parent.mkdir(parents=True)
            with open(outname.as_posix(), 'wt') as f:
                f.write(rendered)
            return

        et = tuple()
        wd_docs_kwargs += [
            (rp, rp / f, makeKwargs(rp, f, doc_config))
            for rp in repo_paths
            for f in rp.repo.git.ls_files().split('\n')
            if Path(f).suffix in suffixFuncs
            and only(rp, f)
            and noneMembers(f, *skip_folders)
            and f not in rskip.get(rp.name, et)]

        [kwargs.update({'theme': self.options.theme}) for _, _, kwargs in wd_docs_kwargs]

        if self.options.spell:
            spell((f.as_posix() for _, f, _ in wd_docs_kwargs))
            return

        titles = doc_config['titles']

        outname_rendered = render_docs(wd_docs_kwargs, out_path, titles,
                                       self.options.jobs,
                                       debug=self.options.debug)

        index = [f'<b class="{heading}">{heading}</b>'
                for heading in doc_config['index']]

        _NOTITLE=object()
        for outname, rendered in outname_rendered:
            apath = outname.relative_to(self.options.out_path)
            title = titles.get(apath.as_posix(), _NOTITLE)
            # TODO parse out/add titles
            if title is not None:
                value = (hfn.atag(apath)
                         if title is _NOTITLE else
                         hfn.atag(apath, title))
                index.append(value)

            if not outname.parent.exists():
                outname.parent.mkdir(parents=True)

            with open(outname.as_posix(), 'wt') as f:
                f.write(rendered)

        lt  = list(titles)
        missing_titles = []
        def title_key(a, _mt=missing_titles):
            title = a.split('"')[1]
            if title not in lt:
                msg = (f'{title} missing from {self.options.config}')
                _mt.append(msg)
                return -1

            return lt.index(title)

        index_body = '<br>\n'.join(['<h1>Documentation Index</h1>'] +
                                    sorted(index, key=title_key))

        if missing_titles:
            msg = '\n'.join(missing_titles)
            raise ValueError(msg)

        with open((out_path / 'index.html').as_posix(), 'wt') as f:
            f.write(hfn.htmldoc(index_body,
                                title=doc_config['title']))


def main():
    from docopt import docopt, parse_defaults
    args = docopt(__doc__)
    defaults = {o.name:o.value if o.argcount else None
                for o in parse_defaults(__doc__)}
    debug = args['--debug']
    options = Options(args, defaults)
    main = Main(options)
    main()


if __name__ == '__main__':
    main()
