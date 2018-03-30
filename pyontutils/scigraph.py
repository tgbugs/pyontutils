from pyontutils.core import devconfig
from pyontutils import scigraph_client
from IPython import embed

scigraph_client.BASEPATH = (f'http://{devconfig.scigraph_host}'
                            f'{":" if devconfig.scigraph_port else ""}'
                            f'{devconfig.scigraph_port}/scigraph')

__all__ = [e for e in dir(scigraph_client) if type(getattr(scigraph_client, e)) == type]

###

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
