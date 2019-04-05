# Specification for the serialization produced by ttlser.py

## Introduction
ttlser is the product of long frustration with the majority of commonly used
turtle serializers due to their reordering of triples on additions or deletions
which leads to spurious diffs (see
[this blog post](https://douroucouli.wordpress.com/2014/03/30/the-perils-of-managing-owl-in-a-version-control-system/)
for an overview of the issues).
The main use case motivating ttlser is to produce human readable diffs of ontology
files that display the meaningful changes and not reorderings. Specifically ttlser
was developed to minimize diffs for ttl files that are stored in git.
For additional information on turtle see [the grammar](https://www.w3.org/TR/turtle/#sec-grammar-grammar).

## High level formatting
1. A single newline `\n` occurs after all lines.
2. A second newline shall occur only in the following cases.
    1. After the last line of the prefix section.
    2. After every section header.
    3. After the closing line (the one with a period `.`) of a `rdf:type` block.
3. Indentation.
	1. There shall be no indentation for `@prefix` lines.
	2. There shall be no indentation for lines representing top level triples (e.g. `rdf:type` lines).
	3. There shall be no indentation for section header lines.
	4. Lines representing triples with lower priority predicates (e.g. `rdfs:subClassOf`) shall have one additional indentation block of 4 spaces preceeding them in addition to the number of indentation blocks preceeding the line for the highest priority triple with which they share their subject. For example a `rdfs:subClassOf` triple line sharing a subject with a top level `owl:Class` triple line should have exactly 1 indentation block of 4 spaces preceeding the `r` in `rdfs:subClassOf`.
	5. Elements of an `rdf:List` shall all have only 1 additional indentation block beyond that of a normal object.
4. All opening parenthesis shall occur on the same line as the subject they represent.
5. All closing parenthesis and brackets shall occur on the same line, each separated by a single space (lisp style).
6. Opening parenthesis of an `rdf:List` shall be follow by a newline.
7. Opening brackets shall NOT be followed by a newline.
8. There shall be 1 space between subject, predicate, object, parenthesis, square brackets, `;`, and `.`.
9. There shall be NO space preceding a comma `,` separating a list of predicate-objects sharing the same subject.

## Alphabetical ordering
Alphabetical ordering in this document means the following.
* Orderings are defined over a set of string representations of the qname forms of subjects, predicates, or objects. Anonymous BNodes should be considered to be null thus should not be considered when sorting alphabetically.
* Values that do not have a qname representation (e.g. `<http://example.org>` or `"Hello world"`) and that are not BNodes shall be taken as is.
* The ordering shall be a natural sort (such that `'a9'` comes before `'a10'` and `'a11111111'`) with an exception describe in the next point.
* The ordering shall put `'a'` after `'A'` but before `'B'`. Essentially this can be interpreted to mean that capital vs lowercase should be ignored when ordering between different letters (e.g. `A` vs `B` or `c` vs `D`) but should be taken into account when breaking ties where there are two identical strings that differ only in their capitalization. This means that `'bb'` comes before `'BBb'`.

## Ordering rules
1. Class orderings and predicate orderings are as listed at the start of `CustomTurtleSerializer`. In theory these orderings could be maintained in a separate file that any conforming serializer could import.
2. Likewise section headers are as specified in the `SECTIONS` portion of `CustomTurtleSerializer`.
3. `@prefix` lines shall be ordered alphabetically by `(prefix, namespace)` pairs. For example `@prefix c: <http://c.org>` will precede `@prefix C: <http://cc.org>`. Another way to get the same ordering as using prefix namespace pairs is to sort the set of whole prefix lines alphabetically.
4. Within a section (demarcated by a header) the ordering of entries shall first be in order of their top level class and then alphabetically.
5. Orderings of the contents of `rdf:List`s shall be alphabetical.
6. Orderings of `owl:Restriction`s shall be alphabetically first by the object of their `owl:onProperty` statement, then alphabetically by `owl:allValuesFrom` vs `owl:someValuesFrom`, then alphabetically by the `*ValuesFrom` object.
7. Ordering of literals shall be by type in the following order BooleanLiteral, NumericLiteral, RDFLiteral.
8. Ordering of BooleanLiterals shall be false, true.
9. Ordering of NumericLiterals shall be by pairs of `(numeric value, original string representation)`.
10. Ordering of RDFLiterals shall be alphabetical by the triple `(value, datatype, language)` with the empty string `''` being substituted for either datatype or language if either is missing.
11. Ordering of elements at any given nesting level (skipping invalid combinations such as a literal as a subject) shall be, literal, iri, blankNodePropertyList, collection.
    For example in a collection the order would be `(true 1 1.0 1.00 1e+00 "1" A:1 <http://a.org/1> [ a owl:Thing ] (1 "1"))`.
12. Ordering of `owl:Axiom`s shall be by the triple of objects for `(owl:annotatedSource owl:annotatedProperty owl:annotatedTarget)`.

## Implementation note
This is currently implemented in [serializers.py](./../ttlser/serializers.py) by finding a total ordering on all URIs and Literals, and then using the ranks on those nodes to calculate ranks for any BNode that is their parent. This is done using a fixedpoint function on the ranks of BNodes. This provides a global total ordering for all triples than can then be used to produce deterministic output recursively. Ordering rules involving predicate precidence are implemented by selecting the order in which predicates or groups of predicates appear in the list at the beginning of `CustomTurtleSerializer`.
