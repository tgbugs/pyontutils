#!/usr/bin/env python3.5
from rdflib.extras import infixowl
from IPython import embed
from scigraph_client import Graph, Vocabulary
sgv = Vocabulary(cache=True)

if __name__ == '__main__':
    main()
