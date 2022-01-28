import rdflib

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer,
                       'ttlser', 'CustomTurtleSerializer')
rdflib.plugin.register('cmpttl', rdflib.serializer.Serializer,
                       'ttlser', 'CompactTurtleSerializer')
rdflib.plugin.register('uncmpttl', rdflib.serializer.Serializer,
                       'ttlser', 'UncompactTurtleSerializer')
rdflib.plugin.register('scottl', rdflib.serializer.Serializer,
                       'ttlser', 'SubClassOfTurtleSerializer')
rdflib.plugin.register('rktttl', rdflib.serializer.Serializer,
                       'ttlser', 'RacketTurtleSerializer')
rdflib.plugin.register('htmlttl', rdflib.serializer.Serializer,
                       'ttlser', 'HtmlTurtleSerializer')


def readFromStdIn(stdin=None):
    from select import select
    if stdin is None:
        from sys import stdin
    if select([stdin], [], [], 0.0)[0]:
        return stdin


def subclasses(start):
    for sc in start.__subclasses__():
        yield sc
        yield from subclasses(sc)
