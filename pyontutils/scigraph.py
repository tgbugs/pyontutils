from pyontutils import scigraph_client
from pyontutils.config import devconfig, get_api_key

scigraph_client.BASEPATH = (f'{devconfig.scigraph_api}')

scigraph_client.restService.api_key = get_api_key()

__all__ = [e for e in dir(scigraph_client) if type(getattr(scigraph_client, e)) == type]

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
