#!/usr/bin/env python3
import tempfile
from pyontutils.config import auth
__doc__ = f"""Client library generator for SciGraph REST api.

Usage:
    scigraph-codegen [options] [--dynamic=<PATH>...]

Options:
    -o --output-file=FILE       save client library here    [default: {tempfile.tempdir}/scigraph_client.py]

    -a --api=API                API endpoint to build from  [default: {auth.get('scigraph-api')}]
    -v --scigraph-version=VER   API docs version            [default: 2]

    -b --basepath=BASEPATH      alternate default basepath  [default: https://scicrunch.org/api/1/sparc-scigraph]
    -d --dynamic=<PATH>         additional servers to search for dynamic endpoints

"""

import re
import copy
import inspect
import requests


class restService:
    """ Base class for SciGraph rest services. """

    _api_key = None

    _hrx = re.compile('^https?://')

    def __init__(self, cache=False, safe_cache=False, key=None, do_error=False):
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
        self._session.mount('http://', adapter)
        self._do_error = do_error

        if cache:
            #print('WARNING: cache enabled, if you mutate the contents of return values you will mutate the cache!')
            self._cache = dict()
            if safe_cache:
                self._get = self._safe_cache_get
            else:
                self._get = self._cache_get

        else:
            self._get = self._normal_get

        if key is not None:
            self.api_key = key
            raise DeprecationWarning('this way of passing keys will be deprecated soon')

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value

    def __del__(self):
        self._session.close()

    def _safe_url(self, url):
        return url.replace(self.api_key, '[secure]') if self.api_key else url

    @property
    def _last_url(self):
        return self._safe_url(self.__last_url)

    def _normal_get(self, method, url, params=None, output=None):
        s = self._session
        if self.api_key is not None:
            params['key'] = self.api_key
        if method == 'POST':
            req = requests.Request(method=method, url=url, data=params)
        else:
            req = requests.Request(method=method, url=url, params=params)
        if output:
            req.headers['Accept'] = output
        prep = req.prepare()
        if self._verbose: print(self._safe_url(prep.url))
        try:
            resp = s.send(prep)
            self.__last_url = resp.url
        except requests.exceptions.ConnectionError as e:
            host_port = prep.url.split(prep.path_url)[0]
            raise ConnectionError(f'Could not connect to {host_port}. '
                                  'Are SciGraph services running?') from e
        if resp.status_code == 401:
            raise ConnectionError(f'{resp.reason}. '
                                  f'Did you set {self.__class__.__name__}.api_key'
                                  ' = my_api_key?')
        elif not resp.ok:
            if self._do_error:
                resp.raise_for_status()
            else:
                return None
        elif resp.headers['content-type'] == 'application/json':
            return resp.json()
        elif resp.headers['content-type'].startswith('text/plain'):
            return resp.text
        else:
            return resp

    def _cache_get(self, method, url, params=None, output=None):
        if params:
            pkey = '?' + '&'.join(['%s=%s' % (k,v) for k,v in sorted(params.items()) if v is not None])
        else:
            pkey = ''
        key = url + pkey + ' ' + method + ' ' + str(output)
        if  key in self._cache:
            if self._verbose:
                print('cache hit', key)
            self.__last_url, resp = self._cache[key]
        else:
            resp = self._normal_get(method, url, params, output)
            self._cache[key] = self.__last_url, resp

        return resp

    def _safe_cache_get(self, *args, **kwargs):
        """ If cached values might be used in a context where they
            could be mutated, then safe_cache = True should be set
            and this wrapper will protect the output """
        return copy.deepcopy(self._cache_get(*args, **kwargs))  # prevent mutation of the cache

    def _make_rest(self, default=None, **kwargs):
        kwargs = {k:v for k, v in kwargs.items() if v}
        param_rest = '&'.join(['%s={%s}' % (arg, arg) for arg in kwargs if arg != default])
        param_rest = param_rest if param_rest else ''
        return param_rest


class SUBCLASS:
    @classmethod
    def make(cls):
        code = inspect.getsource(cls).replace('SUBCLASS', cls.__name__ + 'Base')
        return '\n\n' + code


class Cypher(SUBCLASS):
    @staticmethod
    def fix_quotes(string, s1=':["', s2='"],'):
        out = []
        def subsplit(sstr, s=s2):
            #print(s)
            if s == '",' and sstr.endswith('"}'):  # special case for end of record
                s = '"}'
            if s:
                string, *rest = sstr.rsplit(s, 1)
            else:
                string = sstr
                rest = '',

            if rest:
                #print('>>>>', string)
                #print('>>>>', rest)
                r, = rest
                if s == '"],':
                    fixed_string = Cypher.fix_quotes(string, '","', '') + s + r
                else:
                    fixed_string = string.replace('"', r'\"') + s + r

                return fixed_string

        for sub1 in string.split(s1):
            ss = subsplit(sub1)
            if ss is None:
                if s1 == ':["':
                    out.append(Cypher.fix_quotes(sub1, ':"', '",'))
                else:
                    out.append(sub1)
            else:
                out.append(ss)

        return s1.join(out)

    def fix_cypher(self, record):
        rep = re.sub(r'({|, )(\S+)(: "|: \[)', r'\1"\2"\3',
                     self.fix_quotes(record.strip()).
                     split(']', 1)[1] .
                     replace(':"', ': "') .
                     replace(':[', ': [') .
                     replace('",', '", ') .
                     replace('"],', '"], ') .
                     replace('\n', '\\n') .
                     replace('xml:lang="en"', r'xml:lang=\"en\"')
                    )
        try:
            value = {self.qname(k):v for k, v in literal_eval(rep).items()}
        except (ValueError, SyntaxError) as e:
            print(repr(record))
            print(repr(rep))
            raise e

        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setCuries()

    def _setCuries(self):
        try:
            self._curies = self.getCuries()
        except ConnectionError:
            self._curies = {}

        self._inv = {v:k for k, v in self._curies.items()}

    @property
    def api_key(self):
        # note that using properties means that
        # if you want to use properties at all in
        # a subClass hierarchy you have to reimplement
        # them every single time to be aware if the
        # parent class value chanes
        if isinstance(restService.api_key, str):
            return restService.api_key
        else:
            return self._api_key

    @api_key.setter
    def api_key(self, value):
        old_key = self.api_key
        self._api_key = value
        if old_key is None and value is not None:
            self._setCuries()

    def qname(self, iri):
        for prefix, curie in self._inv.items():
            if iri.startswith(prefix):
                return iri.replace(prefix, curie + ':')
        else:
            return iri

    def execute(self, query, limit, output='text/plain', **kwargs):
        if output == 'text/plain':
            out = super().execute(query, limit, output, **kwargs)
            rows = []
            if out:
                for raw in out.split('|')[3:-1]:
                    record = raw.strip()
                    if record:
                        d = self.fix_cypher(record)
                        rows.append(d)

            return rows

        else:
            return super().execute(query, limit, output, **kwargs)


class Dynamic(SUBCLASS):

    @staticmethod
    def _path_to_id(path):
        return (path.strip('/')
                .replace('dynamic/', '')
                .replace('{', '')
                .replace('}', '')
                .replace('/', '_')
                .replace('-', '_'))

    def _path_function_arg(self, path):
        if '?' in path:
            path, query = path.split('?', 1)
            kwargs = parse_qs(query)
        else:
            kwargs = {}

        if '.' in path:
            # FIXME logic seems bad ...
            if ':' not in path or path.index('.') > path.index(':'):
                raise ValueError('extensions not supported directly please use output=mimetype')

        if ':' in path:  # curie FIXME way more potential arguments here ...
            key = lambda s: len(s)
            args = []
            puts = []
            while ':' in path:
                path, arg = path.rsplit('/', 1)
                args.append(arg)
                base = self._path_to_id(path)
                putative = self._path_to_id(path + '/{')
                if ':' not in putative:
                    puts.append(putative)

            args.reverse()  # args are parsed backwards

            cands = sorted([p for p in dir(self) if p.startswith(puts[0])], key=key)
            if len(cands) > 1:
                effs = [getattr(self, self._path_to_id(c)) for c in cands]
                specs = [inspect.getargspec(f) for f in effs]
                lens = [len(s.args) - 1 - len(s.defaults) for s in specs]
                largs = len(args)
                new_cands = []
                for c, l in zip(cands, lens):
                    if l == largs:
                        new_cands.append(c)

                if len(new_cands) > 1:
                    raise TypeError('sigh')

                cands = new_cands

            elif not cands:
                raise ValueError(f'{self._basePath} does not have endpoints matching {path}')

            fname = cands[0]
        else:
            arg = None
            args = []

            fname = self._path_to_id(path)

        if not hasattr(self, fname):
            raise ValueError(f'{self._basePath} does not have endpoint {path} -> {fname!r}')

        return getattr(self, fname), args, kwargs

    def dispatch(self, path, output='application/json', **kwargs):
        f, args, query_kwargs = self._path_function_arg(path)
        kwargs.update(query_kwargs)
        try:
            return f(*args, output=output, **kwargs) if args else f(output=output, **kwargs)
        except TypeError as e:
            raise TypeError('Did you remember to set parameters in the services config?') from e


class Graph(SUBCLASS):
    @staticmethod
    def ordered(start, edges, predicate=None, inverse=False):
        """ Depth first edges from a SciGraph response. """
        s, o = 'sub', 'obj'
        if inverse:
            s, o = o, s

        edges = list(edges)
        for edge in tuple(edges):
            if predicate is not None and edge['pred'] != predicate:
                print('scoop!')
                continue

            if edge[s] == start:
                yield edge
                edges.remove(edge)
                yield from Graph.ordered(edge[o], edges, predicate=predicate)


class CLASSNAME(restService):
    """ DOCSTRING """

    def __init__(self, basePath=None, verbose=False, cache=False, safe_cache=False, key=None, do_error=False):
        if basePath is None:
            basePath = BASEPATH
        self._basePath = basePath
        self._verbose = verbose
        super().__init__(cache=cache, safe_cache=safe_cache, key=key, do_error=do_error)


class FAKECLASS:
    def NICKNAME(selfPARAMSDEFAULT_OUTPUTKWARGS):
        """ DOCSTRING
        """
        {params_conditional}
        kwargs = {param_rest}
        {dict_comp}
        url = self._basePath + ('{path}').format(**kwargs)
        requests_params = {dict_comp2}
        output = self._get('{method}', url, requests_params, {output})
        return output if output else {empty_return_type}

    @staticmethod
    def make():
        code = inspect.getsource(FAKECLASS.NICKNAME)
        code = code.replace('requests_params, ', 'requests_params')
        code = code.replace('        {params_conditional}','{params_conditional}')
        for name in ('NICKNAME','PARAMS','DEFAULT_OUTPUT', 'DOCSTRING', 'KWARGS'):
            code = code.replace(name, '{' + name.lower() + '}')
        return code


operation_code = FAKECLASS.make()


class State:
    def __init__(self, api_url, basepath=None, dynamics=tuple()):
        # TODO autopopulate from subclasses
        self._dynamics = dynamics
        self.classname = None
        self._subclasses = {sc.__name__:sc for sc in SUBCLASS.__subclasses__()}

        self.shebang = "#!/usr/bin/env python3\n"
        self.imports = ('import re\n'
                        'import copy\n'
                        'import inspect\n'
                        'import builtins\n'
                        'from urllib.parse import parse_qs\n'
                        'import requests\n'
                        'from ast import literal_eval\n'
                        'from json import dumps\n'
                        'from urllib import parse\n\n')
        self._basepath = basepath if basepath is not None else api_url.rsplit('/', 1)[0]
        self.api_url = api_url
        self.current_path = self.api_url
        self.exten_mapping = {}
        self._paths = {}
        self.globs = {}
        self.tab = '    '
        self.gencode()

    def code(self):
        return self.make_main()

    def make_main(self):
        code = ""
        code += self.shebang
        code += self.make_doc()
        code += self.imports
        code += f'BASEPATH = {self._basepath!r}\n\n'
        code += "exten_mapping = {%s}\n\n" % ', '.join(["'" + '\': \''.join(_) + "'" for _ in sorted(self.exten_mapping.items())])
        code += self.make_baseclass()
        code += self._code
        code += '\n'

        return code

    def make_doc(self):
        code = ('"""WARNING: DO NOT MODIFY THIS FILE\n'
                'IT IS AUTOMATICALLY GENERATED BY scigraph.py\n'
                'AND WILL BE OVERWRITTEN\n'
                'Swagger Version: {swaggerVersion}, API Version: {apiVersion}\n'
                'generated for {api_url}\nby scigraph.py\n"""\n')
        swaggerVersion = self.globs['swaggerVersion']
        apiVersion = self.globs['apiVersion']
        return code.format(swaggerVersion=swaggerVersion, apiVersion=apiVersion, api_url=self.api_url, t=self.tab)

    def make_baseclass(self):
        return inspect.getsource(restService) + '\n'

    def make_class(self, dict_):
        code = '\n' + inspect.getsource(CLASSNAME) + '\n'
        classname = dict_['resourcePath'].strip('/').capitalize()
        docstring = dict_['docstring']
        if classname in self._subclasses:
            self.classname = classname  # FIXME ICK
            classname = classname + 'Base'
        print('Generating:', classname)
        #_, basePath = self.basePath_(dict_['basePath'])
        return (code.replace('CLASSNAME', classname)
                .replace('DOCSTRING', docstring)
                .replace("'BASEPATH'", 'BASEPATH'))

    def make_subclass(self):
        if self.classname in self._subclasses:
            subclass = self._subclasses[self.classname]
            subclass_code = subclass.make()
            self.classname = None
            return subclass_code
        else:
            return ''

    def make_param_parts(self, dict_):
        if dict_['required']:
            #param_args = '{name}'
            #param_args = param_args.format(name=dict_['name'])
            param_args = dict_['name']
            required = param_args
        else:
            param_args = "{name}={defaultValue}"
            dv = dict_.get('defaultValue', None)
            if dv:
                try:
                    dv = int(dv)
                except ValueError:
                    if dv == 'true':
                        dv = 'True'
                    elif dv == 'false':
                        dv = 'False'
                    else:
                        dv = "'%s'" % dv
            param_args = param_args.format(name=dict_['name'], defaultValue=dv)
            required = None

        #param_rest = '{name}'
        #param_rest = param_rest.format(name=dict_['name'])
        param_rest = dict_['name']

        param_doc = '{t}{t}{t}{name}:{description}'

        desc = dict_.get('description','')
        LIMIT = 65
        if len(desc) > LIMIT:
            desc = desc.replace('>', '> ||').replace('<', '|| <')
            tmp = desc.split(' ')
            lines = []
            line = None
            for token in tmp:
                if not line:
                    line = token
                elif len(line) + len(' ' + token) > LIMIT:
                    lines.append(line)
                    line = token
                else:
                    line += ' ' + token

            if line not in lines:
                if len(line) < 10:
                    lines[-1] += ' ' + line
                else:
                    lines.append(line)

            space = (' ' * (len(dict_['name']) + 2))
            desc = '\n{t}{t}{t}{space}'.format(t=self.tab, space=space).join([l for l in lines if l])
            desc = desc.replace('> ||', '>').replace('|| <', '<').replace('||', '')

        desc = ' ' + desc if desc else desc
        param_doc = param_doc.format(name=dict_['name'], description=desc, t=self.tab)

        return param_args, param_rest, param_doc, required

    def make_params(self, list_):
        pargs_list, prests, pdocs = [], [], []
        required = None
        needs_kwargs = False
        for param in list_:
            if 'schema' in param:  # skip 'body' entries, they cause problems
                continue
            parg, prest, pdoc, put_required = self.make_param_parts(param)
            if put_required:
                required = "'%s'" % put_required  # XXX fail for multi required?
            pargs_list.append(parg)
            prests.append(prest)
            pdocs.append(pdoc)
            if param['name'] == 'cypherQuery':
                needs_kwargs = True

        if pargs_list:
            pargs = ', ' + ', '.join(pargs_list)
        else:
            pargs = ''

        pkeys = prests

        kwargs = ', **kwargs' if needs_kwargs else ''

        if prests:
            prests = '{' + ', '.join([f'{pr!r}: {pr}' for pr in prests]) + kwargs + '}'
        else:
            prests = '{}'

        pdocs = '\n'.join(pdocs)
        return pargs, prests, pdocs, required, pkeys, needs_kwargs

    def make_return(self, api_dict):
        return_type = None
        if 'type' in api_dict:
            return_type = api_dict['type']  # array or other (Graph, etc)
            print(return_type)
        elif 'responses' in api_dict:
            resps = api_dict['responses']
            if '200' in resps:
                scm = resps['200']['schema']
                if 'type' in scm:
                    return_type = scm['type']

        if return_type is None:
            print(f'    No return type for {api_dict["operationId"]}')

        type_return_dict = {  # TODO source from asdf['definitions'] for 2.0
            'array': '[]',
            'object': '{}',
            'string': None,
            'Annotations': '[]',  # bug in docs
            'Graph': "{'nodes':[], 'edges':[]}",  # risky
            'ConceptDTO': None,  # better None than empty dict
            'RefineResult': None,  # TODO
            'AnalyzerResult' :None,  # TODO
            None:None,
        }

        return type_return_dict[return_type]

    def apiVersion(self, value):
        self.globs['apiVersion'] = value
        return None, ''

    def swaggerVersion(self, value):
        self.globs['swaggerVersion'] = value
        return None, ''

    def operation(self, api_dict):
        params, param_rest, param_docs, required, pkeys, needs_kwargs = self.make_params(api_dict['parameters'])
        dict_comp = (('kwargs = {k:dumps(v) if builtins.type(v) '
                      'is dict else v for k, v in kwargs.items()}')
                      # json needs " not '
                      if param_rest != '{}' else '# type caste not needed')
        empty_return_type = self.make_return(api_dict)
        nickname = api_dict['nickname']
        path = self._paths[nickname]
        docstring = (api_dict.get('summary', '') +
                     ' from: ' +
                     path +
                     '\n\n{t}{t}{t}Arguments:\n'.format(t=self.tab) +
                     param_docs)

        if 'x-query' in api_dict:
            _p = '{t}{t}{t}'.format(t=self.tab)
            _query = api_dict['x-query'].replace('\n', '\n' + _p)
            docstring += '\n\n{p}Query:\n{p}{q}'.format(p=_p, q=_query)
            docstring = docstring.rstrip() + '\n'

        # handle whether required is in the url
        if required:
            if '{' + required.strip("'") + '}' not in path:
                required = None
        if required:
            dict_comp2 = '{k:v for k, v in kwargs.items() if k != %s}' % required
        else:
            dict_comp2 = 'kwargs'

        params_conditional = ''
        for key in pkeys:
            #if [_ for _ in ('id', 'url', 'type', 'relationship') if _ in key]:
            # FIXME detect this from the parameter type ...
            if key in ('id', 'artifact_id', 'species_id',
                       'region_id', 'species-id', 'fma_id', 'root_id'):
                cond = key
                params_conditional += (
                    "\n{t}{t}if {cond} and self._hrx.match({cond}):\n"
                    "{t}{t}{t}{cond} = parse.quote({cond}, safe='')").format(cond=cond, t=self.tab)

        if 'produces' in api_dict:  # ICK but the alt is nastier
            outputs, default_output = self.make_produces(api_dict['produces'])
            docstring += outputs
            output = ', output'
        else:
            default_output = ''
            output = ''

        kwargs = ', **kwargs' if needs_kwargs else ''

        method = api_dict['method']

        if '{' in path and '-' in path:  # FIXME hack
            before, after = path.split('{', 1)  # use split since there can be multiple paths
            path = before + '{' + after.replace('-', '_')

        if output and nickname == 'execute':
            path = ('{"/cypher/execute.json" '
                    'if output == "application/json" else'
                    ' "/cypher/execute"}')
            opcode = operation_code.replace("'{path}'", "f'{path}'")
        else:
            opcode = operation_code

        formatted = opcode.format(
            path=path, nickname=nickname, params=params, param_rest=param_rest,
            dict_comp=dict_comp, dict_comp2=dict_comp2, method=method,
            docstring=docstring, required=required, default_output=default_output, kwargs=kwargs,
            params_conditional=params_conditional, output=output, t=self.tab,
            empty_return_type=empty_return_type)
        self.dodict(api_dict)  # catch any stateful things we need, but we arent generating code from it
        return formatted

    def description(self, value):
        return None, ''

    def resourcePath(self, value):
        return None, ''

    def top_path(self, extension):
        newpath = self.api_url + extension
        json = requests.get(newpath).json()
        return json

    def path(self, value):
        # if anything do substitution here
        # need something extra here?
        return None, ''

    def apis(self, list_):
        print('    Starting ...')
        try:
            for api in list_:
                if 'operations' in api:
                    for operation in api['operations']:
                        self._paths[operation['nickname']] = api['path']
        except:
            raise BaseException
        return None, self.dolist(list_)

    def models(self, dict_):
        return None, self.dodict(dict_)

    def Features(self, dict_):
        self.dodict(dict_)
        return None, ''

    def Graph(self, dict_):
        self.dodict(dict_)
        return None, ''

    def properties(self, dict_):
        return None, self.dodict(dict_)

    def operations(self, list_):
        self.context = 'operations'
        code = '\n'.join(self.operation(l) for l in list_)
        return None, code

    def produces(self, list_):
        return None, ''

    def make_produces(self, list_):
        # we make return option here including the docstring
        for mimetype in list_:
            self.exten_mapping[mimetype] = mimetype.split('/')[-1]

        outputs = '\n{t}{t}{t}outputs:\n{t}{t}{t}{t}'
        outputs += '\n{t}{t}{t}{t}'.join(list_)

        default_output = ', output=\'{output}\''.format(output=list_[0])
        return outputs.format(t=self.tab), default_output   # FIXME there MUST be a better way to deal with the bloody {t} all at once

    def basePath_(self, value):
        dirs = value.split('/')
        curs = self.api_url.split('/')
        for d in dirs:
            if d == '..':
                curs = curs[:-1]
            else:
                curs.append(d)

        return None, '/'.join(curs)

    def dolist(self, list_):
        blocks = []
        def sortkey(d):
            if 'path' in d:
                return d['path']
            elif 'nickname' in d:
                return d['nickname']
            elif 'name' in d:
                return d['name']
            else:
                return 0

        list_.sort(key=sortkey)
        for dict_ in list_:
            code = self.dodict(dict_)
            blocks.append(code)

        return '\n'.join([b for b in blocks if b])

    def dodict(self, dict_):
        blocks = []
        methods = {k:v for k, v in inspect.getmembers(self) if k != 'code' and inspect.ismethod(v)}  # ismethod calls properties :/
        for key, value in dict_.items():
            #print('trying with key:', key)
            if key in methods:
                #name, code = methods[key](self, value)
                name, code = methods[key](value)
                blocks.append(code)
            else:
                #print('METHOD', key, 'NOT FOUND')
                pass

        return '\n'.join([b for b in blocks if b])

    def class_json(self, dict_):
        code = self.make_class(dict_)
        methods = self.dodict(dict_)
        subclass_code = self.make_subclass()

        if methods:
            code += methods
        else:
            code += '    # No methods exist for this API endpoint.\n'

        return None, code + subclass_code

    def dotopdict(self, dict_):
        for api in dict_['apis']:
            json = self.top_path(api['path'])
            json['docstring'] = api['description']
            api['class_json'] = json
        return dict_

    def gencode(self):
        """ Run this to generate the code """
        resp = requests.get(self.api_url)
        if not resp.ok:
            if resp.status_code == 401 and 'scicrunch.org' in self.api_url:
                resp = requests.get(
                    self.api_url,
                    params={'key': auth.get('scigraph-api-key')})
            else:
                resp.raise_for_status()

        ledict = resp.json()
        for durl in self._dynamics:
            dj = requests.get(durl).json()
            for p in dj['paths']:
                if p.startswith('/dynamic') and p not in ledict['paths']:
                    ledict['paths'][p] = dj['paths'][p]

        ledict = self.dotopdict(ledict)
        out = self.dodict(ledict)
        self._code = out


class State2(State):
    path_prefix = ''
    dynamic_produces = [
        'application/json',
        'application/graphson',
        'application/xml',
        'application/graphml+xml',
        'application/xgmml',
        'text/gml',
        'text/csv',
        'text/tab-separated-values',
        'image/jpeg',
        'image/png',
    ]
    def dotopdict(self, dict_):
        """ Rewrite the 2.0 json to match what we feed the code for 1.2 """
        mlookup = {'get':'GET', 'post':'POST'}
        def rearrange(path, method_dict, method):
            oid = method_dict['operationId']
            self._paths[oid] = path
            method_dict['nickname'] = oid
            method_dict['method'] = mlookup[method]

        paths = dict_['paths']
        for path, path_dict in paths.items():
            if path.startswith('/dynamic'):
                #if '{' in path:
                    #operationId = path.split('/{', 1)[0].rsplit('/', 1)[-1]
                operationId = Dynamic._path_to_id(path)

                xq = path_dict.pop('x-query')
                for k in tuple(path_dict):
                    if k.startswith('x-'):
                        print(f'Removed unknown key: {k}')
                        path_dict.pop(k)

                for method_dict in path_dict.values():
                    method_dict['operationId'] = operationId
                    method_dict['x-query'] = xq
                    method_dict['produces'] = self.dynamic_produces
                    method_dict['path'] = path  # FIXME ??
                    for pd in method_dict['parameters']:
                        pd['name'] = pd['name'].replace('-', '_')

            elif self.path_prefix and self.path_prefix not in path:
                continue
            path_dict['operations'] = []
            for method, method_dict in sorted(path_dict.items()):
                if method == 'operations':
                    continue
                rearrange(path, method_dict, method)
                #print(self.operation(method_dict))
                path_dict['operations'].append(method_dict)
            path_dict['path'] = path

        def setp(v, lenp=len(self.path_prefix)):
            v['path'] = v['path'][lenp:]
            return v

        dict_['apis'] = []
        for tag_dict in dict_['tags']:
            path = '/' + tag_dict['name']
            d = {'path':path,
                 'description':tag_dict['description'],
                 'class_json':{
                     'docstring':tag_dict['description'],
                     'resourcePath':path,
                     'apis':[setp(v) for k, v in paths.items()
                             if k.startswith(self.path_prefix + path)]},
            }
            dict_['apis'].append(d)

        # make sure this is run first so we don't get key errors
        self._swagger(dict_['swagger'])
        self._info(dict_['info'])
        self._definitions(dict_['definitions'])

        return dict_

    def _swagger(self, string):
        self.globs['swaggerVersion'] = string
        return None, ''

    def _info(self, dict_):
        self._version(dict_['version'])
        return None, ''

    def _version(self, string):
        self.globs['apiVersion'] = string
        return None, ''

    def _definitions(self, dict_):
        self._return_defs = dict_
        return None, ''

    def title(self, string):
        return None, ''

    def tags(self, list_):
        return None, ''


def moduleDirect(basepath, module_name, *, version=2):
    """ Avoid the need for dynamics altogether """
    if version < 2:
        state = State
        docs_path = 'api-docs'
    else:
        state = State2
        docs_path = 'swagger.json'

    api_url = f'{basepath}/{docs_path}'
    s = state(api_url, basepath)
    code = s.code()
    return importDirect(code, module_name)


def importDirect(code, module_name):
    from types import ModuleType
    compiled = compile(code, '', 'exec')
    module = ModuleType(module_name)
    exec(compiled, module.__dict__)
    return module


def main():
    from docopt import docopt
    from docopt import parse_defaults
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    args = docopt(__doc__, version='scigraph-codegen 1.0.0')
    ssd = 'https://scicrunch.org/swagger-docs'
    if args['--api'] == defaults['--basepath']:
        args['--api'] = ssd

    if args['--api'] == 'https://scicrunch.org/api/1/scigraph':
        args['--api'] = ssd

    if args['--api'] == ssd:
        State2.path_prefix = '/scigraph'

    output_file, api, version, basepath = (
        args['--' + k]
        for k in ('output-file', 'api', 'scigraph-version', 'basepath'))
    version = int(version)
    basepath = None if basepath == 'default' else basepath
    if version < 2:
        state = State
        docs_path = 'api-docs'
    else:
        state = State2
        docs_path = 'swagger.json'

    api_url = f'{api}/{docs_path}'
    print(api_url)

    dynamics = [f'{d}/swagger.json' for d in args['--dynamic']]
    if dynamics:
        print('dynamics:', dynamics)

    s = state(api_url, basepath, dynamics=dynamics)
    code = s.code()
    with open(output_file, 'wt') as f:
        f.write(code)
    import os
    os.system(f'python {output_file}')

if __name__ == '__main__':
    main()
