"""
ini_set('display_errors', true);
error_reporting(E_ALL);
// Put these befor the line to display complete errors!
"""

import requests
import json
import os

base_url = 'http://localhost:8080/api/1/'
prime_term_url = base_url + 'ilx/add'
add_term_url = base_url + 'term/add'
api_key = os.environ.get('LOCAL_SCICRUNCH_API_KEY')

def test_local_host_url():
    search_term_via_ilx_url = base_url + 'ilx/search/identifier/{ilx_id}?key={api_key}'
    search_term_via_ilx_url = search_term_via_ilx_url.format(ilx_id='ilx_0100000', api_key=api_key)
    print(search_term_via_ilx_url)
    response = requests.get(search_term_via_ilx_url, headers = {'Content-type': 'application/json'})
    print(response.status_code)
    print(response.json())
# test_local_host_url()

data = {
    'term': 'test_100',
    'type': 'term',
    'key': api_key,
}

response = requests.post(prime_term_url, data=json.dumps(data), headers = {'Content-type': 'application/json'})
print(response.status_code)
print(response.json())

data.update({
    'label': data.pop('term'),
    'ilx': response.json()['data']['fragment'],
})

print(data, 'pre-import')

response = requests.post(add_term_url, data=json.dumps(data), headers = {'Content-type': 'application/json'})
print(response.status_code)
try:
    print(response.json(), 'post-import')
except:
    print(response.text, 'post broke')
