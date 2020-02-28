#!/usr/bin/env python3
import csv
import pickle
from os.path import expanduser
import requests
from pyontutils.utils import chunk_list
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


def main():

    with open('nlx_properties', 'rt') as f:
        properties = [l.strip() for l in f.readlines() if not l.startswith('#')]

    print(properties)

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
    # see https://www.semantic-mediawiki.org/wiki/Help:Configuration#Query_settings
    for props in chunk_list(properties, 10):  # 20 too long :/ may be able to fix via $smwgQMaxSize which defaults to 12
        all_rows = []
        for start in range(0, 30001, result_step):  # offset limit is fixed via $smwgQMaxLimit in SMW_Settings.php
            url = url_prefix + '/?'.join(props) + url_suffix.format(start, result_step)  # crazy stuff when you leave out the ?
            try:
                data = requests.get(furl(url))
            except:
                print('FAILED on URL =', furl(url))
                #breakpoint()
                # data is already defined it will just duplicated the previous block
            reader = csv.reader(data.text.splitlines())
            rows = [r for r in reader]
            all_rows.extend(rows)

        results.append(all_rows)

    with open(expanduser('~/files/nlx_dump_results.pickle'), 'wb') as f:
        pickle.dump(results, f)

    full_rows = []
    for rows in zip(*results):
        outrow = []
        for row in rows:
            if outrow:
                #assert outrow[0] == row[0], "ROW MISMATCH %s %s" % (outrow, row)
                if outrow[0] != row[0]:
                    print("ROW MISMATCH")
                    print(outrow)
                    print(row)
                    print()
                outrow.extend(row[1:])  # already got the category
            else:
                outrow.extend(row)
        full_rows.append(outrow)

    with open('/tmp/neurolex_full.csv', 'wt', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerows(full_rows)

    breakpoint()

if __name__ == '__main__':
    main()
