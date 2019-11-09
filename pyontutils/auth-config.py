{'config-search-paths': ['{:user-config-path}/pyontutils/config.yaml',],
 'auth-variables':
 {'curies': ['../nifstd/scigraph/curie_map.yaml',  # git
             '{:user-config-path}/pyontutils/curie_map.yaml',  # config
             '{:prefix}/share/pyontutils/curie_map.yaml.example',  # system
             '/usr/share/pyontutils/curie_map.yaml.example',  # pypy3
             'share/pyontutils/curie_map.yaml.example',],  # ebuild testing
  'git-local-base': '../..',
  'git-remote-base': 'https://github.com/',
  'ilx-host': 'uri.interlex.org',
  'ilx-port': '',
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
  'scigraph-api': 'https://scicrunch.org/api/1/scigraph',
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
