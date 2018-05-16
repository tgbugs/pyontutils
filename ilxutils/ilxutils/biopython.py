from Bio import Entrez, SeqIO
import json
Entrez.email = 'troysincomb@gmail.com'
handle = Entrez.efetch(db="taxonomy", id="6420", idtype="acc")#rettype="gb", retmode="text")
record = Entrez.read(handle)
handle.close()
print(record[0]['ScientificName'])
