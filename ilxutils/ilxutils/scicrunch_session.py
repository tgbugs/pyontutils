import json
import requests
from typing import Union, Dict, List
from urllib.parse import urljoin


class ScicrunchSession:
    """ Boiler plate for SciCrunch server responses. """

    def __init__(self,
                 key: str,
                 host: str = 'scicrunch.org',
                 auth: tuple = (None, None)) -> None:
        """ Initialize Session with SciCrunch Server.

        :param str key: API key for SciCrunch [should work for test hosts].
        :param str host: Base url for hosting server [can take localhost:8080].
        :param str user: username for test server.
        :param str password: password for test server.
        """
        self.key = key
        self.host = host

        # https is only for security level environments
        if self.host.startswith('localhost'):
            self.api = "http://" + self.host + '/api/1/'
        else:
            self.api = "https://" + self.host + '/api/1/'

        self.session = requests.Session()
        self.session.auth = auth
        self.session.headers.update({'Content-type': 'application/json'})

    def __session_shortcut(self, endpoint: str, data: dict, session_type: str = 'GET') -> dict:
        """ Short for both GET and POST.

        Will only crash if success is False or if there a 400+ error.
        """
        def _prepare_data(data: dict) -> dict:
            """ Check if request data inputed has key and proper format. """
            if data is None:
                data = {'key': self.key}
            elif isinstance(data, dict):
                data.update({'key': self.key})
            else:
                raise ValueError('request session data must be of type dictionary')
            return json.dumps(data)

        url = urljoin(self.api, endpoint)
        data = _prepare_data(data)
        try:
            # TODO: Could use a Request here to shorten code.
            if session_type == 'GET':
                response = self.session.get(url, data=data)
            else:
                response = self.session.post(url, data=data)
            # crashes if success on the server side is False
            if not response.json()['success']:
                raise ValueError(response.text + f' -> STATUS CODE: {response.status_code}')
            response.raise_for_status()
        # crashes if the server couldn't use it or it never made it.
        except requests.exceptions.HTTPError as error:
            raise error

        # {'data':{}, 'success':bool}
        return response.json()['data']

    def get(self, endpoint: str, data: dict = None) -> dict:
        """ Quick GET for SciCrunch. """
        return self.__session_shortcut(endpoint, data, 'GET')

    def post(self, endpoint: str , data: dict = None) -> dict:
        """ Quick POST for SciCrunch. """
        return self.__session_shortcut(endpoint, data, 'POST')
