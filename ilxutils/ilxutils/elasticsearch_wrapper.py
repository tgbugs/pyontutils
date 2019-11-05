from functools import wraps
import json
import os
import subprocess
import docopt
from elasticsearch import Elasticsearch
BASHRC = lambda s: os.environ.get(s)


class ElasticSearchTools:
    """ Shortcuts for common elasticsearch querys. """

    def __init__(self,
                 host: str, index: str, type: str,
                 user: str, password: str,
                 size: int = 10, start: int = 0,
                 scheme: str = 'https',) -> None:
        """
        :param str url: ElasticSearch url endpoint.
        :param str index:
        """
        self.url = f'{scheme}://{host}/{index}'
        self.host, self.index, self.type = host, index, type
        self.es = Elasticsearch(self.url, http_auth=(user, password))

    def search(self, body: dict, **kwargs) -> dict:
        """ Elasticsearch '/_search' feature.

        We use a framented index called a type. The type is the last index
        while the real index becomes part of the host url.

        :param dict body: query dict.
        :return: nested elasticsearch dict where hits are in ['hits']['hits']

        >>>__search(body={ 'query': { 'match_all': {} } })
        """
        return self.es.search(index=self.type, body=body, **kwargs)

    def all_matches(self, sorting: str, size, start) -> dict:
        """First or last set of entities.

        :param str sorting: asc for head or desc for tail.
        :param int size: number of entities you want from head or tails.
        :param int start: position of index you want to start from.
        :return: elasticsearch _search dict
        """
        if sorting.lower().strip() not in ['asc', 'desc']:
            raise ValueError('sorting can only be asc or desc.')
        body = {
            'query': { 'match_all': {} },
            'sort': [ { '_id': sorting } ],
            'size': size,
            'from': start,
        }
        return self.search(body)

    def head(self, size=10, start=0):
        """ See __end doc. """
        return self.all_matches(sorting='asc', size=size, start=start)

    def tail(self, size=10, start=0):
        """ See __end doc. """
        return self.all_matches(sorting='desc', size=size, start=start)


class InterLexES(ElasticSearchTools):

    def __init__(self, beta=True):
        super().__init__(
            host = BASHRC('INTERLEX_ELASTIC_URL'),
            index = 'interlex',
            type = 'term',
            user = BASHRC('INTERLEX_ELASTIC_USER'),
            password = BASHRC('INTERLEX_ELASTIC_PASSWORD'),
        )
        self.beta = beta

    def filter_tmp(self):
        prefix = 'tmp_' if self.beta else 'ilx_'
        return { 'prefix': { 'ilx' : { 'value': prefix } } }

    def all_matches(self, sorting: str, size, start) -> dict:
        """First or last set of entities.

        :param str sorting: asc for head or desc for tail.
        :param int size: number of entities you want from head or tails.
        :param int start: position of index you want to start from.
        :return: elasticsearch _search dict
        """
        if sorting.lower().strip() not in ['asc', 'desc']:
            raise ValueError('sorting can only be asc or desc.')
        body = {
            'query': self.filter_tmp(),
            'sort': [ { '_id': sorting } ],
            'size': size,
            'from': start,
        }
        return self.search(body)


def main():
    ilxes = InterLexES(beta=False)
    print(ilxes.tail(1))


if __name__ == '__main__':
    main()
