{'config-search-paths': ['{:user-config-path}/pyontutils/config.yaml',],
 'auth-variables':
 {'curies': ['../nifstd/scigraph/curie_map.yaml',  # git
             '{:user-config-path}/pyontutils/curie_map.yaml',  # config
             '{:user-data-path}/share/pyontutils/curie_map.yaml',  # pip install --user
             '{:prefix}/share/pyontutils/curie_map.yaml',  # system
             '/usr/share/pyontutils/curie_map.yaml',  # pypy3
             '{:cwd}/share/pyontutils/curie_map.yaml',],  # ebuild testing
  'git-local-base': '../..',
  'git-remote-base': 'https://github.com/',
  'ontology-local-repo': '../../NIF-Ontology',
  'ontology-org': 'SciCrunch',
  'ontology-repo': 'NIF-Ontology',
  'patch-config': '../nifstd/patches/patches.yaml',
  'resources': '../nifstd/resources',

  # google api
  'google-api-store-file': None,
  'google-api-store-file-readonly': None,
  'google-api-creds-file': None,

  #'hypothesis-api-user': 'tgbugs',
  #'scigraph-api-user': 'tgbugs',
  #'hypothesis-api-key':

  'nifstd-checkout-ok': {'environment-variables': 'NIFSTD_CHECKOUT_OK'},
  'scigraph-api': {'default': 'https://scicrunch.org/api/1/scigraph',
                   'environment-variables': 'SCIGRAPH_API',},
  'scigraph-api-key': {'environment-variables': 'SCIGRAPH_API_KEY SCICRUNCH_API_KEY'},

  # scigraph build
  'scigraph-graphload': '../nifstd/scigraph/graphload.yaml',
  'scigraph-java': '../nifstd/scigraph/scigraph-services.conf',
  'scigraph-services': '../nifstd/scigraph/services.yaml',
  'scigraph-start': '../nifstd/scigraph/start.sh',
  'scigraph-stop': '../nifstd/scigraph/stop.sh',
  'scigraph-systemd': '../nifstd/scigraph/scigraph-services.service',
  'zip-location': '/tmp'}
}
