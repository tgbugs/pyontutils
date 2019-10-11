import ontquery as oq
from pyontutils.core import OntTerm
import os

InterLexRemote = oq.plugin.get('InterLex')

TEST = 'https://test3.scicrunch.org/api/1/'
PRODUCTION = 'https://scicrunch.org/api/1/'

interlex_remote_production = InterLexRemote(
    # When ready, should be changed to 'https://scicrunch.org/api/1/' for production
    apiEndpoint = PRODUCTION
)
interlex_remote_production.setup(instrumented=OntTerm)

interlex_remote_test = InterLexRemote(
    # When ready, should be changed to 'https://scicrunch.org/api/1/' for production
    apiEndpoint = TEST
)
interlex_remote_test.setup(instrumented=OntTerm)
