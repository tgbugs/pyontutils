from pyontutils import scigraph
from collections import defaultdict
import pandas as pd
import os

sd = scigraph.Dynamic('https://scicrunch.org/api/1/sparc-scigraph')
sd.api_key = os.environ.get('INTERLEX_API_KEY')

organ_records = {}

organList = sd.prod_sparc_organList()
organList_label_curies = [(node['lbl'], node['id']) for node in organList['nodes']]

for ol_label, ol_curie in organList_label_curies:
    organParts = sd.prod_sparc_organParts_id(ol_curie)
    organParts_label_curies= [organPart['lbl']+' | '+organPart['id'] for organPart in organParts['nodes']]
    organ_records[ol_label+' | '+ol_curie] = organParts_label_curies

organ_df = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in organ_records.items() ]))
# organ_df.to_csv('/home/tmsincomb/Desktop/organList.csv', index=None, columns=sorted(organ_df.columns))
