#!/usr/bin/env python3
"""
    Client library generator for SciGraph REST api.
"""

import requests
from IPython import embed

class State:
    def __init__(self, api_url):
        self.shebang = "#!/usr/bin/env python3\n"
        self.imports = "import requests\n\n"
        self.api_url = api_url
        self.current_path = self.api_url
        self.exten_mapping = {}
        self.paths = {}
        self.globs = {}
        self.tab = '    '
        self.gencode()

    @property
    def code(self):
        return self.make_main()

    def make_main(self):
        code = ""
        code += self.shebang
        code += self.make_doc()
        code += self.imports
        code += "exten_mapping = %s\n\n" % repr(self.exten_mapping)
        code += self.make_baseclass()
        code += self._code
        
        return code
        
    def make_doc(self):
        code = '""" Swagger Version: {swaggerVersion}, API Version: {apiVersion}\n{t}generated for {api_url}\n{t}by scigraph.py\n"""\n'
        swaggerVersion = self.globs['swaggerVersion']
        apiVersion = self.globs['apiVersion']
        return code.format(swaggerVersion=swaggerVersion, apiVersion=apiVersion, api_url=self.api_url, t=self.tab)

    def make_baseclass(self):
        code = (
            'class restService:\n'
            '{t}""" Base class for SciGraph rest services. """\n\n'
            '{t}def _get(self, method, url, output=None):\n'
            '{t}{t}print(url)\n'
            '{t}{t}s = requests.Session()\n'
            '{t}{t}req = requests.Request(method=method, url=url)\n'
            '{t}{t}if output:\n'
            '{t}{t}{t}req.headers[\'Accept\'] = output\n'
            '{t}{t}prep = req.prepare()\n'
            '{t}{t}resp = s.send(prep)\n'
            '{t}{t}if resp.headers[\'content-type\'] == \'application/json\':\n'
            '{t}{t}{t}return resp.json()\n'
            '{t}{t}elif resp.headers[\'content-type\'].startswith(\'text/plain\'):\n'
            '{t}{t}{t}return resp.text\n'
            '{t}{t}else:\n'
            '{t}{t}{t}return resp\n'
            '\n'
        )
        return code.format(t=self.tab)

    def make_class(self, dict_):
        code = (
            '\n'
            'class {classname}(restService):\n'
            '{t}""" {docstring} """\n\n'
            '{t}def __init__(self, basePath=\'{basePath}\'):\n'
            '{t}{t}self._basePath = basePath\n\n'
        )
        classname = dict_['resourcePath'].strip('/').capitalize()
        docstring = dict_['docstring']
        _, basePath = self.basePath_(dict_['basePath'])
        return code.format(classname=classname, docstring=docstring, basePath=basePath, t=self.tab)

    def make_param_parts(self, dict_):
        if dict_['required']:
            param_args = '{name}'
            param_args = param_args.format(name=dict_['name'])
        else:
            param_args = "{name}='{defaultValue}'"
            param_args = param_args.format(name=dict_['name'], defaultValue=dict_.get('defaultValue',''))

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
    
        return param_args, param_rest, param_doc

    def make_params(self, list_):
        pargs_list, prests, pdocs = [], [], []
        for param in list_:
            if param['name'] == 'category' or param['name'] == 'prefix':  # FIXME need a more elegant way to build the urls :/
                continue
            parg, prest, pdoc = self.make_param_parts(param)
            pargs_list.append(parg)
            prests.append(prest)
            pdocs.append(pdoc)

        if pargs_list:
            pargs = ', ' + ', '.join(pargs_list)# + ', '  # if there are args add a comma
        else:
            pargs = ''

        if prests:# and pargs_list != prests:  # if prests isn't just a copy of the arg
            prests = '?' + '&'.join([pr + '={%s}'%pr for pr in prests]) + "'.format(%s)" % ', '.join([pr + '=' + pr for pr in prests]) 
        elif pargs:
            prests = "'.format(%s)" % ', '.join([pr + '=' + pr for pr in prests]) 
        else:
            prests = "'"

        pdocs = '\n'.join(pdocs)
        return pargs, prests, pdocs

    def apiVersion(self, value):
        self.globs['apiVersion'] = value
        return None, ''

    def swaggerVersion(self, value):
        self.globs['swaggerVersion'] = value
        return None, ''

    def operation(self, api_dict):
        code = (
            '{t}def {nickname}(self{params}{default_output}):\n'
            '{t}{t}""" {docstring}\n{t}{t}"""\n\n'
            '{t}{t}url = self._basePath + \'{path}{param_rest}\n'
            '{t}{t}return self._get(\'{method}\', url{output})\n'
        )

        params, param_rest, param_docs = self.make_params(api_dict['parameters'])
        nickname = api_dict['nickname']
        path = self.paths[nickname]
        docstring = api_dict['summary'] + ' from: ' + path + '\n\n{t}{t}{t}Arguments:\n'.format(t=self.tab) + param_docs
        if 'produces' in api_dict:  # ICK but the alt is nastier
            outputs, default_output = self.make_produces(api_dict['produces'])
            docstring += outputs
            output = ', output'
        else:
            default_output = ''
            output = ''

        method = api_dict['method']
        if len(path.split('{')) > 1:
            if '&' in param_rest:  # FIXME this is obscure and could be explicit at a lower level
                param_rest = '?' + param_rest.split('&',1)[1]  # remove required args from rest args
                #FIXME inconsistency when we have only id...
            elif path.split('{')[1].startswith(param_rest[1:].split('=')[0]):
                param_rest = "'" + param_rest.split("'")[-1]  # single term edge case eg id=id
                
        formatted = code.format(path=path, nickname=nickname, params=params, param_rest=param_rest,
                                method=method, docstring=docstring, default_output=default_output,
                                output=output, t=self.tab)
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
        try:
            for api in list_:
                if 'operations' in api:
                    for operation in api['operations']:
                        self.paths[operation['nickname']] = api['path']
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
        for dict_ in list_:
            code = self.dodict(dict_)
            blocks.append(code)

        return '\n'.join([b for b in blocks if b])

    def dodict(self, dict_):
        blocks = []
        for key, value in dict_.items():
            try:
                print('trying with key:', key)
                name, code = self.__class__.__dict__[key](self, value)
                blocks.append(code)
            except KeyError:  # reduce the stuff we aren't worried about
                # FIXME for some reason this eats other errors too :/
                print('METHOD', key, 'NOT FOUND')
            except ValueError:
                print('wtf value is this!?', key, value)
                raise

        return '\n'.join([b for b in blocks if b])

    def class_json(self, dict_):
        code = self.make_class(dict_)
        code += self.dodict(dict_)
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

def main():
    target = '/tmp/test_api.py'
    s = State('http://matrix.neuinfo.org:9000/scigraph/api-docs')
    code = s.code
    #print(code)
    with open(target, 'wt') as f:
        f.write(code)

if __name__ == '__main__':
    main()


