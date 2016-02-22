#!/usr/bin/env python3
import csv
import requests
from IPython import embed

with open('nlx_properties', 'rt') as f:
    properties = [l.strip() for l in f.readlines() if not l.startswith('#')]

print(properties)

chunk_size = 20

def chunk_list(list_, size):
    ll = len(list_)
    chunks = []
    for start, stop in zip(range(0, ll, size), range(size, ll, size)):
        chunks.append(list_[start:stop])
    chunks.append(list_[stop:])  # snag unaligned chunks from last stop
    return chunks


def furl(url):
    url = url.replace('[','-5B')
    url = url.replace(']','-5D')
    url = url.replace('?','-3F')
    url = url.replace('=','%3D')
    return url

url_prefix = 'http://neurolex.org/wiki/Special:Ask/[[Category:Entity]]/'
url_suffix = '/mainlabel=Categories/format=csv/sep=,/offset={}/limit={}'

results = []
result_step = 2500
for props in chunk_list(properties, 10):  # 20 too long :/
    all_rows = []
    for start in range(0, 10001, result_step):  # offset limited to 10k wtf
        url = url_prefix + '/?'.join(props) + url_suffix.format(start, result_step)  # crazy stuff when you leave out the ?
        data = requests.get(furl(url))
        reader = csv.reader(data.text.splitlines())
        rows = [r for r in reader]
        all_rows.extend(rows)

    results.append(all_rows)

full_rows = []
for rows in zip(*results):
    outrow = []
    for row in rows:
        if outrow:
            assert outrow[0] == row[0], "ROW MISMATCH %s %s" % (outrow, row)
            outrow.extend(row[1:])  # already got the category
        else:
            outrow.extend(row)
    full_rows.append(outrow)

embed()
