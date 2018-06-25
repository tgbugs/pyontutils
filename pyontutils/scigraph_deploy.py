#!/usr/bin/env python3.6
from pyontutils.core import devconfig
__doc__ = f"""Deploy SciGraph services and loaded graph.

Usage:
    scigraph-deploy all [options] <repo> <remote_base> <build_host> <services_host>
    scigraph-deploy graph [options] <repo> <remote_base> <build_host> <services_host>
    scigraph-deploy config [options] <build_host> <services_host>
    scigraph-deploy services [options] <build_host> <services_host>
    scigraph-deploy [options]

Options:
    -U --build-user=USER                build_user              [default: bamboo]
    -E --services-user=USER             services_user           [default: bamboo]

    -G --graph-latest-url=LAG           url to latest graph     [default: file:///tmp/graph/LATEST]
    -A --services-latest-url=LAS        url to latest services  [default: file:///tmp/scigraph/LATEST]
    -F --graph-folder=DLOC              set graph location      [default: from-services-config]
    -V --services-folder=PATH           jars sent here          [default: /opt/scigraph-services/]
    -T --services-config=SCFG           services.yaml location  [default: {devconfig.scigraph_services}]
                                        if only the filename is given assued to be in scigraph-config-folder
                                        will look for *.template version of the file
    -y --systemd-config=FILE            name of systemd config  [default: {devconfig.scigraph_systemd}]
                                        if only the filename is given assued to be in scigraph-config-folder
                                        will look for *.template version of the file
    -j --java-config=FILE               name of java template   [default: {devconfig.scigraph_java}]
                                        if only the filename is given assued to be in scigraph-config-folder
                                        will look for *.template version of the file

    -I --first-time                     generate the one shots or run them
    -X --execute                        run the compiled commands
    -R --build-only                     build but do not deploy various components
    -L --local                          run all commands locally (runs actual python!)

    --services-log-loc=FOLDER           services logs           [default: /var/log/scigraph-services/]

    -H --ssh-user                       if
"""
#    -J --java-config-loc=FILEPATH       location to deploy java config [default: /etc/]
# yes we could have tried to do this in make...
# on the build server you need pyontutils SciGraph NIF-Ontology
# on the services deploy server you only need pyontutils...
#  so just use the build server too, its easier than fighting bamboo

import os
import socket
import inspect
from os.path import join as jpth
from shlex import quote as squote
from pathlib import Path
from functools import wraps
from collections import namedtuple
import yaml
from docopt import parse_defaults
from pyontutils.utils import anyMembers
from pyontutils.ontload import __doc__ as ontload_docs
from pyontutils.ontload import defaults as ontload_defaults
from pyontutils.ontload import run as ontload_main
from pyontutils.ontload import COMMIT_HASH_HEAD_LEN, NotBuiltError, locate_config_file, getCuries
from IPython import embed

ontload_defaults.update({'<repo>':None,
                         '<remote_base>':None})  # these don't need values
defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
defaults.update({'<repo>':None,
                 '<remote_base>':None,
                 '<build_host>':None,
                 '<services_host>':None})  # these don't need values
combined_defaults = {**ontload_defaults, **defaults}

USER = os.environ['USER']
HOST = socket.gethostname()

AND = ' && '
OR = ' || '
ACCEPT = '; '

BLD = '*build'
SER = '*services'
EXE = '*executor'
GRA = '*graph'

class Builder:
    """ Build and/or run the SciGraph build and deploy chain. """
    # filenames currently not set by options [default: ]
    scigraph_repo = 'SciGraph'
    start_script = f'{devconfig.scigraph_start}'
    stop_script = f'{devconfig.scigraph_stop}'
    services_jar = 'scigraph-services.jar'
    heap_dump = 'head.dump'
    garbage_collection_log = 'gc.log'
    services_log = 'sysout.log'
    etc = '/etc/'
    zip_loc_var = 'ZIP_LOC'
    def __init__(self, args, **kwargs):
        self.__dict__.update(kwargs)
        self._updated = False
        if self.check_built:
            self.build_only = True
        self._host = HOST
        self._user = USER
        self.args = args
        self.ontload_args = {k:v for k, v in args.items()}  # send them all!
        self.ontload_args['scigraph'] = self.services
        if self.all or self.graph:
            self.ontload_args['graph'] = True
        self.ontload_args.update({'imports':None,'chain':None,'extra':None,'<ontologies>':[]})
        mode = [k for k, v in self.args.items()
                if not k.startswith('-')
                and not k.startswith('<')
                and v]
        self.mode = mode[0] if mode else None
        self.build_services_config()  # needed to update self.graph_folder  XXX hack fixme
        self._init_more()

        self.same_remotes = False
        if self.local and self.build_only:
            if self.check_built:
                self.local_dispatch()
            return
        elif self.build_host == self.services_host and self.build_user == self.build_user:
            self.same_remotes = True
            # the executor is different from the remotes
            if self.build_host != self._host and not self.check_built:
                #self._host = self.build_host
                #self._user = self.build_user
                self._building = False
                for name, obj in inspect.getmembers(self):
                    continue  # TODO there is a bug here with executor/build boundaries
                    # i think the issues is with the way we are calling anyMembers
                    if inspect.ismethod(obj) and anyMembers(name,
                                                            'config',
                                                            'services',
                                                            'graph',
                                                            'remote'):
                        @wraps(obj)
                        def mutex_on_ssh(*args, func=obj, **kwargs):  # ah late binding hacks
                            if not self._building:
                                self._building = True
                                out = func(*args, **kwargs)
                                self._building = False
                                if out.startswith('('):
                                    #out = f'"{out[1:-1]}"'
                                    out = out[1:-1]
                                print('YAY FOR ONLY ONE SSH!')
                                return out
                                #return f'ssh {self._user}@{self._host} {out}'
                            else:
                                return func(*args, **kwargs)
                        setattr(self, name, mutex_on_ssh)
            elif not self.local:
                print('WARNING: all servers are equivalent to localhost '
                      'but you are running without --local. Did you mean to?')
        elif self.build_host == self._host and self.build_user == self._user:
            if not self.local:
                print('WARNING: all servers are equivalent to localhost '
                      'but you are running without --local. Did you mean to?')


    def _init_more(self):
        all = {'--build-user',
               '--services-user',
               '--first-time',
               '--execute',
               '--local',
               '--git-local',
               '--zip-location',
               '--check-built',
               '--debug',
              }
        #not_pyontutils = '--systemd-config', '--java-config', '--services-log-loc',
        self.repo_arg_skip_mapping = {
            self.scigraph_repo:{'--scp-loc'},
            self.repo:{'--scigraph-scp-loc'},
            'pyontutils':{'--scp-loc',
                          '--scigraph-scp-loc',
                          '--graph-latest-url',
                          '--services-latest-url',
                         },
        }

    def compile(self):
        if self.first_time:
            code = self.oneshots()
        elif self.local:
            print('FIXME this should not be running')
            self.local_dispatch()
            code = 'echo This was a triumph.'
        elif self.build_only:
            code = self.build()
        else:
            code = self.deploy()  # NOTE really 'remote'
        assert '{' not in code, (f'You have an unformatted string somewhere.\n'
                                 f'{code[code.index("{")-30:code.index("{")+30]}')
        return code

    def exec(self):
        code = self.compile()
        os.system(code)
        return code

    def run(self):  # if the executor happens to be what is running this
        if self.execute:
            return self.exec()
        else:
            return self.compile()

    def makeOutput(self, BSE, commands, oper=ACCEPT, defer_shell_expansion=False):
        for o in (AND, OR, ACCEPT):
            if o in commands:
                raise TypeError(f'You have an "{o}" operator in with the commands!')

        to_run = (oper + ('\n' if self.debug else '')).join(c for c in commands if c)

        host, user = self.context(BSE)

        #if defer_shell_expansion and not self.same_remotes and not self.local:
        if defer_shell_expansion and not self.local:  # FIXME same remotes issues
            to_run = squote(to_run)
        same_server = self._host == host and self._user == user
        if BSE == EXE or same_server or self.local:
            if same_server:
                print('Your', BSE, 'server is the same as your executor so not using ssh.')
            if len(commands) > 1:
                to_run = f'({to_run})'
                # parens to preserve order of operations that are defined together as a function
                # for the purposes of handling returns and combining with other logic
                # there may also be weird errors with quote not working right...
            return to_run
        else:
            if not defer_shell_expansion:
                to_run = f'"{to_run}"'
            if self._host == host:
                return f'sudo -u {user} bash -c {to_run}'  # XXX if ${} is in to_run... trouble?
            elif BSE == BLD:
                return f'ssh {user}@{host} {to_run}'
            elif BSE == SER:
                return f'ssh {user}@{host} {to_run}'
            else:
                raise BaseException('wat')

    def runOnExecutor(self, *commands, oper=ACCEPT, defer_shell_expansion=False):
        """ This runs in the executor of the current scope.
            You cannot magically back out since there are no
            gurantees that ssh keys will be in place (they shouldn't be). """
        return self.makeOutput(EXE, commands, oper=oper, defer_shell_expansion=defer_shell_expansion)

    def runOnBuild(self, *commands, oper=ACCEPT, defer_shell_expansion=False):
        return self.makeOutput(BLD, commands, oper=oper, defer_shell_expansion=defer_shell_expansion)

    def runOnServices(self, *commands, oper=ACCEPT, defer_shell_expansion=False):
        return self.makeOutput(SER, commands, oper=oper, defer_shell_expansion=defer_shell_expansion)

    def switcContext(self, BSE):
        if BSE == BLD:
            self._host = self.build_host
            self._user = self.build_user
        elif BSE == SER:
            self._host = self.services_host
            self._user = self.services_user
        elif BSE == EXE:
            self._host = HOST
            self._user = USER

    def context(self, BSE):
        if BSE == BLD:
            return self.build_host, self.build_user
        elif BSE == SER:
            return self.services_host, self.services_user
        elif BSE == EXE:
            return self._user, self._host
        else:
            raise TypeError('wat')

    def _getRepo(self, mode):
        if mode == 'all':
            repo = None
        elif mode == 'graph':
            repo = self.repo
        elif mode == 'config':
            repo = 'pyontutils'
        elif mode == 'services':
            repo = self.scigraph_repo
        else:
            raise TypeError(f'WAT {mode}')


        return repo

    def formatted_args(self, args, mode=None, **additional_args):
        if mode is None:
            mode = self.mode
        scp = '--scp-loc', '--scigraph-scp-loc'
        nargs = {**args, **additional_args}
        cfgr = '<build_host>', '<services_host>'
        allr = '<repo>', '<remote_base>', '<build_host>', '<services_host>'
        r = allr if mode == 'all' or mode == 'graph' else cfgr
        reqs = [nargs[k] for k in r if k in nargs]
        strings = [mode]
        repo = self._getRepo(mode)
        for k, v in sorted(nargs.items()):
            if repo is not None and k in self.repo_arg_skip_mapping[repo]:
                continue
            if k in combined_defaults and v != combined_defaults[k]:
                if k.startswith('-'):
                    if k in scp:  # FIXME don't want to have to do this
                        user_host, path = v.split(':')
                        user, host = user_host.split('@')
                        print(user, host, path, self.build_host, self.build_user)
                        if host == self.build_host and user == self.build_user:
                            string = f'{k} {user}@localhost:{path}'
                        else:
                            string = f'{k} {v}'
                    elif combined_defaults[k] is None:  # argcount == 0
                        if v:
                            string = k
                        else:
                            continue
                    else:
                        string = f'{k} {v}'
                else:
                    continue
                strings.append(string)

        strings += reqs
        out = ' '.join(strings)
        return out

    def LATEST(self, repo):
        if repo == self.repo:
            return self.graph_latest_url
        elif repo == self.scigraph_repo:
            return self.services_latest_url

    # oneshots that need to be run on build and services

    def oneshots(self):
        return self.runOnExecutor(self.oneshots_build(), self.oneshots_services())

    def oneshots_build(self, commands_only=False):
        return self.runOnBuild(*self.cmds_python(),
                               *self.cmds_rdflib(),
                               *self.cmds_pyontutils(),
                               defer_shell_expansion=True,
                               oper=AND)

    def oneshots_services(self, commands_only=False):
        java_config_path = jpth(self.etc, self.java_config)
        return self.runOnServices(
            f'sudo mkdir {self.services_folder}',
            f'sudo chown {self.services_user}:{self.services_user} {self.services_folder}',
            f'sudo mkdir {self.services_log_loc}',
            f'sudo chown {self.services_user}:{self.services_user} {self.services_log_loc}',
            f'sudo touch {java_config_path}',
            f'sudo chown {self.services_user}:{self.services_user} {java_config_path}',
            f'sudo mkdir -p {self.graph_folder}',
            f'sudo chown {self.services_user}:{self.services_user} {self.graph_folder}',
            oper=AND)

    def cmds_python(self, os='centos7'):
        iftest = 'if {}; then echo os ok; else echo os bad; exit 1 ; fi'
        if os == 'centos7':
            TEST = '[ -f /etc/centos-release ]'
            return (iftest.format(TEST),
                    'sudo yum -y install yum-utils',
                    'sudo yum -y groupinstall development',
                    'sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm',
                    'sudo yum -y install python36u',
                    'sudo yum -y install python36u-pip',
                    'sudo yum -y install python36u-devel',  # psutil needs this
                    'sudo pip3.6 install wheel',
                   )

    def _repo_base(self, repo_name):
        name, _ = os.path.splitext(os.path.basename(repo_name))
        return (f'mkdir -p {self.git_local}; cd {self.git_local}',
                f'git clone {repo_name}; cd {name} && export RES=$(git pull)',
                f'if [[ $RES != "Already up-to-date." ]] || [ ! -f dist/{name}*.whl  ]; then '
                'python3.6 setup.py bdist_wheel; '
                f'pip3.6 install --user --upgrade dist/{name}*.whl; '
                'fi')

    def cmds_rdflib(self):
        return self._repo_base('https://github.com/tgbugs/rdflib.git')

    def cmds_pyontutils(self):
        return self._repo_base('https://github.com/tgbugs/pyontutils.git')


    # pass along commands to build

    def build(self, mode=None, check=False):
        """ Just shuffle the current call off to the build server with --local attached """
        kwargs = {}
        if not self.build_only:  # don't try to deploy twice
            kwargs[' --build-only'] = True
        if not self.local:
            kwargs['--local'] = True
        if check:
            kwargs['--check-built'] = True
        remote_args = self.formatted_args(self.args, mode, **kwargs)
        cmds = tuple() if self.check_built or self._updated else self.cmds_pyontutils()
        if not self._updated:
            self._updated = True
        return self.runOnBuild(*cmds,
                               f'scigraph-deploy {remote_args}',
                               defer_shell_expansion=True,
                               oper=AND)

    # local commands that actually do the work on the build server

    def local_dispatch(self):
        self.build_config()  # we always need to run this
        if self.graph or self.all:
            self.build_graph()
        elif self.services:
            self.build_services()

        if self.check_built:
            return

        if not self.build_only:  # executor == build so we call immediately
            # TODO this is not quite right... need to call immediately
            pass

    def build_graph(self):
        return ontload_main(self.ontload_args)

    def build_services(self):
        return ontload_main(self.ontload_args)

    def build_services_config(self):
        services_config_template = self.locate_config_template(self.services_config)
        curies_location = self.curies
        curies, _ = getCuries(curies_location)
        with open(services_config_template, 'rt') as f:
            services_config = yaml.load(f)
        services_config['graphConfiguration']['curies'] = curies
        if self.graph_folder != combined_defaults['--graph-folder']:
            services_config['graphConfiguration']['location'] = self.graph_folder
        else:
            self.graph_folder = services_config['graphConfiguration']['location']
        port = services_config['server']['connector']['port']
        url = services_config['serviceMetadata']['preview']['url']
        services_config['serviceMetadata']['preview']['url'] = url.format(HOSTNAME=self.services_host, PORT=port)
        url = services_config['serviceMetadata']['view']['url']
        services_config['serviceMetadata']['view']['url'] = url.format(HOSTNAME=self.services_host, PORT=port)
        #print(self.graph_folder)
        services_config_path = jpth(self.zip_location, self.services_config)  # save loc
        p = Path(services_config_path)
        if not p.parent.exists(): p.parent.mkdir(parents=True)
        with open(services_config_path, 'wt') as f:
            yaml.dump(services_config, f, default_flow_style=False)

    def _config_helper(self):  # TODO decorator?
        # templates in dict for easier link between filename and vars
        PathDict = namedtuple('PathDict', ['template', 'variables', 'configured'])
        def ld(filename):
            template = self.locate_config_template(filename)
            variables = dict()
            return PathDict(template, variables, filename)

        _templates = {}

        # variable support functions
        def setVars(template_var, config_filename, *var_vals, templates=_templates):
            pd = ld(config_filename)
            templates[template_var] = pd
            for var, val in var_vals:
                pd.variables[var] = val

        def build(templates=_templates):
            # format and save them as their real selves!
            for template_file, kwargs, config_file in templates.values():
                with open(template_file, 'rt') as f:
                    template = f.read()
                config = template.format(**kwargs)
                #print(config_file)
                config_path = jpth(self.zip_location, config_file)
                #print(config_path)
                with open(config_path, 'wt') as f:
                    f.write(config)
                #if config_path.endswith('.sh'):  # scpeeeee
                    #os.chmod(config_path, 0o744)
            print(self.zip_location)  # sent back over ssh

        return setVars, build

    def build_config(self):
        if self.check_built:
            configs = (self.services_config,
                       self.start_script,
                       self.stop_script,
                       self.systemd_config,
                       self.java_config)
            if not all(os.path.exists(jpth(self.zip_location, c)) for c in configs):
                print('The configs have not been built.')
                raise NotBuiltError('The configs have not been built.')
            else:
                print(self.zip_location)
            return

        self.build_services_config()
        setVars, build = self._config_helper()

        # This reminder that something is a bit weird with using templates,
        # we would rather just let the files be the config
        # themselves, but then one of them would have to be 'wrong'... hrm

        # variables (names should match {variables} in the templates)
        setVars('start_template', self.start_script,
                ('services_user', self.services_user),
                ('java_config_path', jpth(self.etc, self.java_config)),
                ('services_jar_path', jpth(self.services_folder, self.services_jar)),
                ('services_config_path', jpth(self.services_folder, self.services_config)),
                ('services_log', jpth(self.services_log_loc, self.services_log)))
        setVars('stop_template', self.stop_script,
                ('services_user', self.services_user))
        setVars('systemd_config_template', self.systemd_config,
                ('path_to_start_script', jpth(self.services_folder, self.start_script)),
                ('path_to_stop_script', jpth(self.services_folder, self.stop_script)))

        # terror of terrors... this is not going in by default
        # why was this even enabled?!
        debug_jmx = '\n' + '\n'.join(
        ('-Dcom.sun.management.jmxremote.port=8082',
         '-Dcom.sun.management.jmxremote.authenticate=false',
         '-Dcom.sun.management.jmxremote.ssl=false'))
        setVars('java_template', self.java_config,
                ('heap_dump_path', jpth(self.services_log_loc, self.heap_dump)),
                ('services_host', self.services_host),
                ('garbage_collection_log', jpth(self.services_log_loc, self.garbage_collection_log)),
                ('debug_jmx', ''))  # debug_jmx)
        build()

    def _config_path(self, config):
        """ Implements the rule that filenames only for configs
            are assumed to live in --scigraph-config-folder"""
        if '/' not in config:
            return jpth(self.scigraph_config_folder, config)
        else:
            return config

    def locate_folder(self, path):
        return locate_config_file(path, self.git_local)

    def locate_config(self, config):
        config = self._config_path(config)
        folder = self.locate_folder(self.scigraph_config_folder)
        return jpth(folder, config)

    def locate_config_template(self, config):
        extension = '.template'  # XXX this line defines the expected template extension
        #return self.locate_config(config) + extension
        return config + extension

    def _deploy(self, commands_only=False):
        scigraph_commands = self.build_scigraph(build_host, commands_only=True)
        graph_commands = self.build_graph(build_host, commands_only=True)
        commands = scigraph_commands + graph_commands
        return self.makeOutput(BLD, commands, commands_only, fail=True)

    def _deploy_graph(self, commands_only=False):
        f = self.fetch_graph(commands_only=True)
        g = self.remote_graph(commands_only=True)
        commands = (
            #'scigraph-deploy deploy graph {services_host} {services_user}'
            'echo wat',
        )
        return self.makeOutput(SER, commands, commands_only)

    # stuff that the executor server calls on services machine

    def fetch(self, repo):
        if repo == 'pyontutils':
            return '(exit 1)'  # can't fetch
        fetch_LATEST = self.LATEST(repo)
        fetch_folder = os.path.dirname(fetch_LATEST)
        return self.runOnServices(
            f'export LC=$(cat -)',
            f'ZIP={repo}-*-$LC*.zip',
            f'if [ -f $ZIP ]; then unzip $ZIP; exit 0; fi',
            f'export LATEST=$(curl {fetch_LATEST})',
            f'if [[ $LATEST =~ $LC ]]; then curl -O {fetch_folder}/$LATEST; else exit 1; fi',
            defer_shell_expansion=True,
            oper=AND)

    #@can_only_run_on('B')  # really a state dependency on access to specific resources...
    def get_latest_commit(self, repo):
        local_path = jpth(self.git_local, repo)
        return self.runOnBuild(f'cd {local_path}',
                             'git pull 1>/dev/null',
                             'git rev-parse HEAD')

    def deploy(self):
        # deploy logic is a bit different from build
        #  it also inverts the dependency order...
        # XXX this is really 'remote'
        tups = tuple()
        if self.config:  # or self.all:  # don't need to call when all since services pulls it in
            tups += (self.remote_config(),)
        if self.services or self.all:
            tups += (self.remote_services(),)
        if self.graph or self.all:
            tups += (self.remote_graph(),)

        return ';\n\n'.join(tups)

    def deploy_base(self, mode, *src_targs, vardefs=tuple()):
        # simple rule that a type checker could do is prevent runing G env cmds on S... no auth there...
        exe = self.runOnExecutor
        repo = self._getRepo(mode)
        lc_command = self.get_latest_commit(repo)
        check_command = self.build(mode, check=True)
        dependencies = self.build(mode)
        bld_usr_host = f'{self.build_user}@{self.build_host}'
        ser_usr_host = f'{self.services_user}@{self.services_host}'
        fetch = (f'export LATEST_COMMIT=$({lc_command} | cut -b-{COMMIT_HASH_HEAD_LEN})',) + \
                (f'echo $LATEST_COMMIT | ' + self.fetch(repo),) if repo != 'pyontutils' else tuple()  # FIXME $LATEST COMMIT is not escaped
        # XXX NOTE: for 3 way transfers to work you must use ssh-agent
        scps = tuple(f'(scp -3 {bld_usr_host}:{src} {ser_usr_host}:{targ} || '
                     f'echo Failed to copy {src})'
                     for src, targ in src_targs)

        fetches = f'export LATEST_COMMIT=$({lc_command} | cut -b-{COMMIT_HASH_HEAD_LEN}) && '
        if repo != 'pyontutils':
            fetches += f'echo $LATEST_COMMIT | ' + self.fetch(repo)
        else:
            fetches += '(exit 1)'  # too hard to check if configs are up to date

        builds = (f'export {self.zip_loc_var}=$({dependencies} | tail -n1)',
                  *vardefs,
                  *scps)

        return exe(check_command,  # needed to fetch latest
                   exe(fetches,
                       exe(*builds,
                           oper=AND),
                       oper=OR))



        # on services? ||
        # fetch? ||
        # build && scp
        command = exe(check_command,
                      exe(*fetch),  # we do fetch on fail in case the build was cleaned up...
                      exe(f'export {self.zip_loc_var}=$({dependencies} | tail -n1)',
                          oper=AND),
                      oper=OR)  # it's almost forth! >_<
        return command

    #@executor
    def deploy_config(self, commands_only=False):
        # assumed to run on build already
        #ser_usr_host = f'{self.services_user}@{self.services_host}'
        return self.deploy_base('config',
                                (f'${self.zip_loc_var}/{self.services_config}', ''),
                                (f'${self.zip_loc_var}/{self.start_script}', ''),
                                (f'${self.zip_loc_var}/{self.stop_script}', ''),
                                (f'${self.zip_loc_var}/{self.systemd_config}', ''),
                                (f'${self.zip_loc_var}/{self.java_config}', ''))

    def remote_config(self):
        dependencies = self.deploy_config(),
        ser_tar = f'$SERVICES_FOLDER/'
        return self.runOnExecutor(*dependencies,
                                  self.runOnServices(
                                      # ANNOYING
                                      f'export SERVICES_FOLDER={self.services_folder}',
                                      f'sudo mv {self.services_config} {ser_tar}',
                                      f'sudo chmod 744 {self.start_script}',
                                      f'sudo mv {self.start_script} {ser_tar}',
                                      f'sudo chmod 744 {self.stop_script}',
                                      f'sudo mv {self.stop_script} {ser_tar}',
                                      f'sudo mv {self.systemd_config} /etc/systemd/system/',
                                      f'sudo mv {self.java_config} {self.etc}',
                                      'sudo systemctl daemon-reload',
                                      oper=AND),
                                 oper=AND)


    def deploy_services(self):
        return self.deploy_base('services', (f'${self.zip_loc_var}', ''))

    #@services
    def remote_services(self, commands_only=False):
        dependencies = self.remote_config(), self.deploy_services()
        commands = (
            f'export SERVICES_FOLDER={self.services_folder}',
            'unzip -q SciGraph-*-services-*.zip',
            'export SERVICES_NAME=$(echo scigraph-services-*-SNAPSHOT/)',
            f'sudo chown -R {self.services_user}:{self.services_user} $SERVICES_NAME',
            'rm -rf $SERVICES_FOLDER/scigraph*',
            'rm -rf $SERVICES_FOLDER/lib',
            'mv $SERVICES_NAME/* $SERVICES_FOLDER/',
            # NOTE scigraph-services.jar is set by start.sh  # FIXME propagate this via ontload
            f'mv $SERVICES_FOLDER/scigraph-services-*-SNAPSHOT.jar $SERVICES_FOLDER/{self.services_jar}',  # TODO
            # deploy_config needs to have been run for this to work as expected
            'sudo systemctl restart scigraph-services',
            'rmdir $SERVICES_NAME')
        return self.runOnExecutor(*dependencies,
                                  self.runOnServices(*commands,
                                                     defer_shell_expansion=True,
                                                     oper=AND),
                                  oper=AND)

    def deploy_graph(self):
        return self.deploy_base('graph', (f'${self.zip_loc_var}', ''))

    #@depends('services', 'has', 'NIF-Ontology-*-graph-*.zip')
    def remote_graph(self, commands_only=False):
        dependencies = self.deploy_graph(),
        #if self.graph_folder == ontload_defaults['--graph-folder']:
        services_config_file = jpth(self.services_folder, 'services.yaml')  # FIXME param services.yaml
        # DONT TRUST THEIR LIES READ IT FROM THE DISK
        use_python = ("import sys\\n"
                      "import yaml\\n"
                      "with open(\\\"$F\\\", \\\"rt\\\") as f:\\n"
                      "    sys.stdout.write(yaml.load(f)[\\\"graphConfiguration\\\"][\\\"location\\\"])")

        get_graph_folder = f'$(F={services_config_file}; echo -e "{use_python}" | python)'

        commands = self.runOnServices(
            f'export GRAPH_FOLDER={get_graph_folder}',
            'export GRAPH_PARENT_FOLDER=$(dirname $GRAPH_FOLDER)',
            'unzip -q NIF-Ontology-*-graph-*.zip',
            'export GRAPH_NAME=$(echo NIF-Ontology-*-graph-*/)',
            f'sudo chown -R {self.services_user}:{self.services_user} $GRAPH_NAME',
            'mv $GRAPH_NAME $GRAPH_PARENT_FOLDER/',
            'sudo systemctl stop scigraph-services',
            'unlink $GRAPH_FOLDER',
            'ln -sT $GRAPH_PARENT_FOLDER/$GRAPH_NAME $GRAPH_FOLDER',
            'sudo systemctl start scigraph-services',
            defer_shell_expansion=True)
            #oper=AND)
        return self.runOnExecutor(*dependencies,
                                  commands,
                                  oper=AND)


def run(args):
    if args['--debug']:
        print(args)
    # ignoring bamboo sequecing for the moment...
    # check the build server to see if we have built the latest (or the specified commit)
    # if yes just scp those to services
    # if no check the web endpoint to see if latest matches build
    # if yes fetch
    # else build (push to web endpoint)

    'localhost:~/files/ontology-packages/scigraph/'
    'tom@orpheus:~/files/ontology-packages/graph/'
    #b = Builder(build_host, services_host, build_user, services_user,
                #graph_latest_url, scigraph_latest_url,
                #scp, sscp, git_local, repo_name,
                #services_folder, graph_folder, services_config_folder
               #)

    kwargs = {k.strip('--').strip('<').rstrip('>').replace('-','_'):v for k, v in args.items()}
    b = Builder(args, **kwargs)
    if b.mode is not None:
        code = b.run()
    else:
        if args['--view-defaults']:
            for k, v in combined_defaults.items():
                print(f'{k:<22} {v}')
        return

    if b.debug:
        FILE = '/tmp/test.sh'
        with open(FILE, 'wt') as f:
            f.write('#!/usr/bin/env bash\n' + code)
        os.system(f"emacs -batch {FILE} --eval '(indent-region (point-min) (point-max) nil)' -f save-buffer")
        print()
        with open(FILE, 'rt') as f:
            print(f.read())
        #embed()
    if b.local:
        return
        #if b.check_built:
            #return
    else:
        print(code)

def main():
    from docopt import docopt
    global __doc__
    __doc__ = ''.join((__doc__, ontload_docs.split('Options:')[-1]))
    args = docopt(__doc__)
    try:
        run(args)
    except NotBuiltError:
        if args['--check-built']:
            print('Not built')
        os.sys.exit(1)

if __name__ == '__main__':
    main()
