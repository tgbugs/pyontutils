{'config-search-paths': ['{:user-config-path}/pyontutils/config.yaml',],
 'auth-variables':
 {'curies': ['../nifstd/scigraph/curie_map.yaml',  # git
             '{:user-config-path}/pyontutils/curie_map.yaml',  # config
             '{:user-data-path}/pyontutils/curie_map.yaml',  # pip install --user
             '{:prefix}/share/pyontutils/curie_map.yaml',  # system
             '/usr/share/pyontutils/curie_map.yaml',  # pypy3
             '{:cwd}/share/pyontutils/curie_map.yaml',],  # ebuild testing
  'git-local-base': '../..',
  'git-remote-base': 'https://github.com/',
  'ontology-local-repo': {'default': '../../NIF-Ontology',
                          'environment-variables': ['PYONTUTILS_ONTOLOGY_LOCAL_REPO',
                                                    'ONTOLOGY_LOCAL_REPO',
                                                    'ONTOLOGY_REPO',]},
  'ontology-org': {'default': 'SciCrunch',
                   'environment-variables': 'NIFSTD_ONTOLOGY_ORG ONTOLOGY_ORG'},
  'ontology-repo': {'default': 'NIF-Ontology',
                    'environment-variables': 'ONTOLOGY_REPO_NAME ONTOLOGY_NAME'},
  'patch-config': {'default': '../nifstd/patches/patches.yaml',
                   'environment-variables': 'ONTOLOGY_PATCH_CONFIG PATCH_CONFIG'},
  'resources': {'default': '../nifstd/resources',
                'environment-variables': 'NIFSTD_RESOURCES ONTOLOGY_RESOURCES RESOURCES'},

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
  'scigraph-api-key': {'environment-variables': 'SCICRUNCH_API_KEY SCIGRAPH_API_KEY'},

  # scigraph build
  'scigraph-graphload': '../nifstd/scigraph/graphload.yaml',
  'scigraph-java': '../nifstd/scigraph/scigraph-services.conf',
  'scigraph-services': '../nifstd/scigraph/services.yaml',
  'scigraph-start': '../nifstd/scigraph/start.sh',
  'scigraph-stop': '../nifstd/scigraph/stop.sh',
  'scigraph-systemd': '../nifstd/scigraph/scigraph-services.service',
  'zip-location': '/tmp'}
}
