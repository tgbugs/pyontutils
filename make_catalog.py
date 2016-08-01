#!/usr/bin/env python3
import os
import glob


urlbase = 'http://ontology.neuinfo.org/NIF/ttl/'
base = '~/git/NIF-Ontology/ttl/'
#list of all nif ontologies
fs = glob.glob(os.path.expanduser(base) + '*')
fs += glob.glob(os.path.expanduser(base) + '*/*')

mapping = [(urlbase + file.split('/ttl/', 1)[-1], file.split('/ttl/', 1)[-1]) for file in fs if file.endswith('.ttl')]

# make a protege catalog file to simplify life
uriline = '  <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'

xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
'<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
[uriline.format(ontid=ont, filename=file) for ont,file in mapping] + \
['  <group id="Folder Repository, directory=, recursive=true, Auto-Update=true, version=2" prefer="public" xml:base=""/>',
'</catalog>',]
xml = '\n'.join(xmllines)
with open('/tmp/nif-catalog-v001.xml','wt') as f:
    f.write(xml)

