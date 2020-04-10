import ontquery as oq
from pyontutils.core import OntTerm
import os

def remote(server=''):

    # Request interlex remote (scigraph is also an option for plugins)
    InterLexRemote = oq.plugin.get('InterLex')

    if server:
        server = server if server.endswith('.') else server + '.'
    endpoint = f'https://{server}scicrunch.org/api/1/'

    #
    interlex_remote = InterLexRemote()

    # setup inheritance classes
    interlex_remote.setup(instrumented=OntTerm)
    interlex_remote.apiEndpoint = endpoint

    return interlex_remote
