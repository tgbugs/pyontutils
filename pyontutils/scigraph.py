from pyontutils import scigraph_client
from pyontutils.config import auth

scigraph_client.BASEPATH = auth.get('scigraph-api')

# WARNING if you import this module anywhere in your program
# and you change the BASEPATH from what it is in auth-config
# you may LEAK YOUR API KEY !!!!!!! To avoid this import
# from scigraph_client directly and do not import this

_sapi = auth.get('scigraph-api')
_need_api_key = 'https' in _sapi and 'scicrunch.org' in _sapi
if _need_api_key:  # FIXME this is _the_ case for auth.monkey_patch(when=_need_api_key)
    scigraph_client.restService.api_key = auth.get('scigraph-api-key')

__all__ = [e for e in dir(scigraph_client)
           if type(getattr(scigraph_client, e)) == type and
           not e.endswith('Base')]

###
Analyzer = scigraph_client.Analyzer

Annotations = scigraph_client.Annotations

Cypher = scigraph_client.Cypher

Dynamic = scigraph_client.Dynamic

Graph = scigraph_client.Graph

Lexical = scigraph_client.Lexical

Refine = scigraph_client.Refine

Vocabulary = scigraph_client.Vocabulary

restService = scigraph_client.restService
###

def main():
    with open(__file__, 'rt') as f:
        text = f.read()

    code = '\n\n'.join(f'{name} = scigraph_client.' + name for name in __all__)

    sep = '\n###\n'
    start, mid, end = text.split(sep)
    code = sep.join((start, code, end))
    with open(__file__, 'wt') as f:
        f.write(code)

if __name__ == '__main__':
    main()
