#!/usr/bin/env python3
from pyontutils.core import devconfig
__doc__ = f"""Client library generator for SciGraph REST api.

Usage:
    scigraph-codegen [options]

Options:
    -o --output-file=FILE       save client library here    [default: /tmp/scigraph_client.py]

    -a --api=API                API endpoint to build from  [default: {devconfig.scigraph_api}]
    -v --scigraph-version=VER   API docs version            [default: 2]

    -b --basepath=BASEPATH      alternate default basepath  [default: https://scicrunch.org/api/1/scigraph]

"""

import inspect
import requests
from  IPython import embed


class restService:
    """ Base class for SciGraph rest services. """

    api_key = None

    def __init__(self, cache=False, key=None):
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
        self._session.mount('http://', adapter)

        if cache:
            #print('WARNING: cache enabled, if you mutate the contents of return values you will mutate the cache!')
            self._cache = dict()
            self._get = self._cache_get
        else:
            self._get = self._normal_get

        if key is not None:
            self.api_key = key

    def __del__(self):
        self._session.close()

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
        safe = prep.url.replace(self.api_key, '[secure]') if self.api_key else prep.url
        if self._verbose: print(safe)
        try:
            resp = s.send(prep)
        except requests.exceptions.ConnectionError as e:
            host_port = prep.url.split(prep.path_url)[0]
            raise ConnectionError('Could not connect to %s are SciGraph services running?' % host_port) from e
        if resp.status_code == 401:
            raise ConnectionError(f'{resp.reason}. Did you set {self.__class__.__name__}.api_key = my_api_key?')
        elif not resp.ok:
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
            return self._cache[key]
        else:
            resp = self._normal_get(method, url, params, output)
            self._cache[key] = resp
            return resp

    def _make_rest(self, default=None, **kwargs):
        kwargs = {k:v for k, v in kwargs.items() if v}
        param_rest = '&'.join(['%s={%s}' % (arg, arg) for arg in kwargs if arg != default])
        param_rest = param_rest if param_rest else ''
        return param_rest


class CLASSNAME(restService):
    """ DOCSTRING """

    def __init__(self, basePath=None, verbose=False, cache=False, key=None):
        if basePath is None:
            basePath = BASEPATH
        self._basePath = basePath
        self._verbose = verbose
        super().__init__(cache, key)


class FAKECLASS:
    def NICKNAME(selfPARAMSDEFAULT_OUTPUT):
        """ DOCSTRING
        """
        {params_conditional}
        kwargs = {param_rest}
        kwargs = {dict_comp}
        param_rest = self._make_rest({required}, **kwargs)
        url = self._basePath + ('{path}').format(**kwargs)
        requests_params = {dict_comp2}
        output = self._get('{method}', url, requests_params, {output})
        return output if output else {empty_return_type}

    @staticmethod
    def make():
        code = inspect.getsource(FAKECLASS.NICKNAME)
        code = code.replace('requests_params, ', 'requests_params')
        code = code.replace('        {params_conditional}','{params_conditional}')
        for name in ('NICKNAME','PARAMS','DEFAULT_OUTPUT', 'DOCSTRING'):
            code = code.replace(name, '{' + name.lower() + '}')
        return code


operation_code = FAKECLASS.make()


class State:
    def __init__(self, api_url, basepath=None):
        self.shebang = "#!/usr/bin/env python3\n"
        self.imports = "import builtins\nimport requests\nfrom json import dumps\nfrom urllib import parse\n\n"
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
        print('Generating:', classname)
        #_, basePath = self.basePath_(dict_['basePath'])
        return code.replace('CLASSNAME', classname).replace('DOCSTRING', docstring).replace("'BASEPATH'", 'BASEPATH')

    def make_param_parts(self, dict_):
        if dict_['required']:
            param_args = '{name}'
            param_args = param_args.format(name=dict_['name'])
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

        param_rest = '{name}'
        param_rest = param_rest.format(name=dict_['name'])

        param_doc = '{t}{t}{t}{name}: {description}'


        desc = dict_.get('description','')
        if len(desc) > 60:
            tmp = desc.split(' ')
            part = len(desc) // 60
            size = len(tmp) // part
            lines = []
            for i in range(part + 1):
                lines.append(' '.join(tmp[i*size:(i+1) * size]))
            desc = '\n{t}{t}{t}'.format(t=self.tab).join([l for l in lines if l])
        param_doc = param_doc.format(name=dict_['name'], description=desc, t=self.tab)

        return param_args, param_rest, param_doc, required

    def make_params(self, list_):
        pargs_list, prests, pdocs = [], [], []
        required = None
        for param in list_:
            if 'schema' in param:  # skip 'body' entries, they cause problems
                continue
            parg, prest, pdoc, put_required = self.make_param_parts(param)
            if put_required:
                required = "'%s'" % put_required  # XXX fail for multi required?
            pargs_list.append(parg)
            prests.append(prest)
            pdocs.append(pdoc)

        if pargs_list:
            pargs = ', ' + ', '.join(pargs_list)
        else:
            pargs = ''

        if prests:
            prests = '{' + ', '.join(["'%s':%s"%(pr, pr) for pr in prests]) + '}'
        else:
            prests = '{}'

        pdocs = '\n'.join(pdocs)
        return pargs, prests, pdocs, required

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
        dict_comp = '{k:dumps(v) if builtins.type(v) is dict else v for k, v in kwargs.items()}'  # json needs " not '
        params, param_rest, param_docs, required = self.make_params(api_dict['parameters'])
        empty_return_type = self.make_return(api_dict)
        nickname = api_dict['nickname']
        path = self._paths[nickname]
        docstring = api_dict.get('summary', '') + ' from: ' + path + '\n\n{t}{t}{t}Arguments:\n'.format(t=self.tab) + param_docs
        # handle whether required is in the url
        if required:
            if '{' + required.strip("'") + '}' not in path:
                required = None
        if required:
            dict_comp2 = '{k:v for k, v in kwargs.items() if k != %s}' % required
        else:
            dict_comp2 = 'kwargs'

        params_conditional = ''
        for cond in 'id', 'url', 'type':
            if cond in param_rest:
                params_conditional += (
                    "\n{t}{t}if {cond} and {cond}.startswith('http:'):\n"
                    "{t}{t}{t}{cond} = parse.quote({cond}, safe='')").format(cond=cond, t=self.tab)

        if 'produces' in api_dict:  # ICK but the alt is nastier
            outputs, default_output = self.make_produces(api_dict['produces'])
            docstring += outputs
            output = ', output'
        else:
            default_output = ''
            output = ''

        method = api_dict['method']

        formatted = operation_code.format(path=path, nickname=nickname, params=params, param_rest=param_rest,
                            dict_comp=dict_comp, dict_comp2=dict_comp2, method=method,
                            docstring=docstring, required=required, default_output=default_output,
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
        if methods:
            code += methods
        else:
            code += '    # No methods exist for this API endpoint.\n'
        return None, code

    def dotopdict(self, dict_):
        for api in dict_['apis']:
            json = self.top_path(api['path'])
            json['docstring'] = api['description']
            api['class_json'] = json
        return dict_

    def gencode(self):
        """ Run this to generate the code """
        ledict = requests.get(self.api_url).json()
        ledict = self.dotopdict(ledict)
        out = self.dodict(ledict)
        self._code = out

class State2(State):
    path_prefix = ''
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
            if self.path_prefix and self.path_prefix not in path:
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


def main():
    from docopt import docopt
    from docopt import parse_defaults
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    args = docopt(__doc__, version='scigraph-codegen 1.0.0')
    if args['--api'] == defaults['--basepath']:
        args['--api'] = 'https://scicrunch.org/swagger-docs'

    if args['--api'] == 'https://scicrunch.org/swagger-docs':
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
    s = state(api_url, basepath)
    code = s.code()
    with open(output_file, 'wt') as f:
        f.write(code)
    import os
    os.system(f'python {output_file}')

if __name__ == '__main__':
    main()


