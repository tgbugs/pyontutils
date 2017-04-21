#!/usr/bin/env python3

from pyontutils.utils import rowParse

class table1(rowParse):  # TODO decouple input -> tokenization to ontology structuring rules, also incremeting ilx_start is a HORRIBLE way to mint identifiers, holy crap, but to improve this we need all the edge structure and links in place so we can do a substitution
    #species = 'NCBITaxon:10116'
    brain_region = 'UBERON:0008933'
    citation = 'Markhram et al Cell 2015'
    pmid = 'PMID:26451489'
    _sep = '|'
    _edge = '\x00\x01\xde\xad\xee\xef\xfe'
    phenotype_iri_map = {}

    def __init__(self, graph, rows, syn_mappings, ilx_start, species=None):
        self.graph = graph
        self.expand = self.graph.expand
        self.ilx_start = ilx_start
        self.syn_mappings = syn_mappings
        self.plbls = set()
        self.mutually_disjoints = defaultdict(set)
        self.pheno_bags = defaultdict(set)  # TODO this needs to become a dict to handle positive/negative and disjointness... :/

        if species:
            self.species = species
        else:
            self.species = 'NCBITaxon:10116'

        label_species = sgv.findById(self.species)['labels'][0]
        label_brain_region = sgv.findById(self.brain_region)['labels'][0]
        self.labels_extrin = [label_species, label_brain_region]

        order = ['Morphological_type',
            'Other_morphological_classifications',
            'Predominantly_expressed_Ca2_binding_proteins_and_peptides',
            'Other_electrical_classifications',
            'Electrical_types']

        super().__init__(rows, order=order)

    def _make_label(self):
        LABEL = ' '.join(
            self.labels_extrin + \
            self.labels_morpho + \
            self.labels_ephys + \
            sorted(self.labels_expression) + \
            ['neuron'])  # switch on interneuron/ other...
        return rdflib.Literal(LABEL)


    #@use_decorators_to_do_mappings_to_generic_classes   # !
    #@also use decorators to flag output classes as mutually disjoint?
    def Morphological_type(self, value):
        print('--------------------')
        self.ilx_start += 1
        self.id_ = ilx_base.format(self.ilx_start)

        self.pheno_bags[self.expand(self.id_)].add(self.expand(self.species))
        self.pheno_bags[self.expand(self.id_)].add(self.expand(self.brain_region))

        self.Class = infixowl.Class(self.expand(self.id_), graph=self.graph.g)

        species_rest = infixowl.Restriction(self.expand('ilx:hasInstanceInSpecies'),
                                           self.graph.g,
                                           someValuesFrom=self.expand(self.species))
        location_rest = infixowl.Restriction(self.expand('ilx:hasSomaLocatedIn'),
                                           self.graph.g,
                                           someValuesFrom=self.expand(self.brain_region))
        self.Class.subClassOf = [species_rest, location_rest,self.expand(NIFCELL_NEURON)]

        syn, abrv = value.split(' (')
        syn = syn.strip()
        abrv = abrv.rstrip(')').strip()
        #print(value)
        print((syn, abrv))

        self.labels_morpho = [syn.rstrip('cell').rstrip().lower()]

        self.graph.add_node(self.id_, 'OBOANN:abbrev', abrv)

        v = syn.rstrip('cell').strip()
        if v not in self.phenotype_iri_map:
            id_ = self.graph.expand('ilx:' + ''.join([_.capitalize() for _ in v.split(' ')]) + 'Phenotype')
            #id_ = self._make_phenotype(v, morpho_phenotype, morpho_edge, morpho_defined)
            self.phenotype_iri_map[v] = id_
        else:
            id_ = self.phenotype_iri_map[v]

        restriction = infixowl.Restriction(self.expand(morpho_edge), graph=self.graph.g, someValuesFrom=id_)
        self.Class.subClassOf = [restriction]

        self.pheno_bags[id_].add(id_)

        """
        BREAKSTUFF
        ARE YOU SURE?
        """

        #restriction = infixowl.Restriction(self.expand(morpho_edge), graph=self.graph.g, someValuesFrom=id_)
        #self.Class.subClassOf = [restriction]

        #self.mutually_disjoints[morpho_phenotype].add(id_)  # done in phenotypes

        self._morpho_parent_id = id_


    def Other_morphological_classifications(self, value):
        return  #  skipping all of this for now due to bitufted nonsense etc
        values = value.split(self._sep)
        output = []
        callbacks = []

        for v in values:
            if '/' in v:
                prefix, a_b = v.split(' ')
                a, b = a_b.split('/')
                #output.append(prefix + ' ' + a)
                #output.append(prefix + ' ' + b)
            else:
                prefix = v.rstrip('cell').strip()
                #output.append(v)

            label = prefix + ' phenotype'
            output.append(label)

        for v in output:
            self.graph.add_node(self._morpho_parent_id, 'OBOANN:synonym', v)

        #print(value)
        print(output)

    def Predominantly_expressed_Ca2_binding_proteins_and_peptides(self, value):
        CB = self.syn_mappings['calbindin']
        PV = self.syn_mappings['Parvalbumin']
        CR = self.syn_mappings['calretinin']
        NPY = self.syn_mappings['neuropeptide Y']
        VIP = self.syn_mappings['VIP peptides']
        SOM = self.syn_mappings['somatostatin']
        p_edge = 'ilx:hasExpressionPhenotype'
        p_map = {
            'CB':CB,
            'PV':PV,
            'CR':CR,
            'NPY':NPY,
            'VIP':VIP,
            'SOM':SOM,
            self._edge:p_edge,
        }
        NEGATIVE = False
        POSITIVE = True  # FIXME this requires more processing prior to dispatch...
        e_edge = ''
        e_map = {
            '-':NEGATIVE,
            '+':POSITIVE,
            '++':POSITIVE,
            '+++':POSITIVE,
            self._edge:e_edge,
        }
        NONE = 0
        LOW = 1
        MED = 2
        HIGH = 3
        s_edge = None #''  # TODO this needs to be an annotation on the (self.id_, ixl:hasExpressionPhenotype, molecule) triple
        s_map = {
            '-':NONE,
            '+':LOW,
            '++':MED,
            '+++':HIGH,
            self._edge:s_edge,
        }

        def apply(map_, val):  # XXX this turns out to be a bad idea :/
            s = self.id_  # FIXME this is what breaks things
            p = map_[self._edge]
            o = map_[val]
            if type(o) == types.FunctionType:
                o = o(val)
            if o and p:
                self.graph.add_node(s, p, o)
            return o

        self.labels_expression = []
        values = value.split(self._sep)
        output = []
        for v in values:
            abrv, score_paren = v.split(' (')
            score = score_paren.rstrip(')')
            molecule = p_map[abrv]
            muri = molecule
            #muri = rdflib.URIRef('http://' + molecule.replace(' ','-') + '.org')  # FIXME rearchitect so that uris are already in place at map creation
            exists = e_map[score]
            score = s_map[score]

            #if abrv not in table1.phenotype_iri_map:
                #defined class
                #self.ilx_start += 1
                #id_ = ilx_base.format(self.ilx_start)
                #id_ = self.expand(id_)
                #self.phenotype_iri_map[abrv] = id_
                #restriction = infixowl.Restriction(self.expand(expression_edge), graph=self.graph.g, someValuesFrom=muri)
                #defined = infixowl.Class(id_, graph=self.graph.g)
                #defined.label = rdflib.Literal(abrv + '+ neuron')

                #intersection = infixowl.BooleanClass(members=(self.graph.expand(NIFCELL_NEURON), restriction), graph=self.graph.g)
                ##intersection = infixowl.BooleanClass(members=(restriction,), graph=self.graph.g)
                #defined.equivalentClass = [intersection]
                #defined.subClassOf = [self.graph.expand('ilx:ExpressionClassifiedNeuron')]


            if exists:
                restriction = infixowl.Restriction(self.expand(p_edge), graph=self.graph.g, someValuesFrom=muri)
                self.Class.subClassOf = [restriction]
            else:
                # disjointness
                restriction = infixowl.Restriction(self.expand(p_edge), graph=self.graph.g, someValuesFrom=muri)
                self.Class.disjointWith = [restriction]  # TODO do we need to manually add existing?
            output.append((molecule, exists, score))

            label = ('+' if exists else '-') + abrv
            self.labels_expression.append(label)  # TODO
        #print(value)
        #print(output)

    def Electrical_types(self, value):  # FIXME these are mutually exclusive types, so they force the creation of subClasses so we can't apply?
        b = self.syn_mappings['petilla b']
        c = self.syn_mappings['petilla c']  # XXX CHECK
        d = self.syn_mappings['petilla d']
        e_edge = 'ilx:hasSpikingPhenotype'
        #e_edge = 'ilx:hasInitialSpikingPhenotype'  # XXX edge level?
        #e_edge = 'ilx:hasElectrophysiologicalPhenotype'
        e_map = {
            'b':b,
            'c':c,
            'd':d,
            self._edge:e_edge,
        }
        AC = self.syn_mappings['petilla ac']
        NAC = self.syn_mappings['petilla nac']
        STUT = self.syn_mappings['petilla stut']
        IR = self.syn_mappings['petilla ir']
        l_edge = 'ilx:hasSpikingPhenotype'
        #l_edge = 'ilx:hasSustainedSpikingPhenotype'  # XXX these should not be handled at the edge level?
        #l_edge = 'ilx:hasElectrophysiologicalPhenotype'
        l_map = {
            'AC':AC,
            'NAC':NAC,
            'STUT':STUT,
            'IR':IR,
            self._edge:l_edge,
        }

        def apply(map_, val):  # doesn't work, requires many subclasses
            s = self.id_
            p = map_[self._edge]
            o = map_[val]
            if o:
                self.graph.add_node(s, p, o)
            return o

        values = value.split(self._sep)
        output = []
        for v in values:
            early_late, score_pct_paren = v.split(' (')
            score = int(score_pct_paren.rstrip('%)'))
            #early = apply(e_map, early_late[0])
            #late = apply(l_map, early_late[1:])
            e_name, l_name = early_late[0], early_late[1:]
            early, late = e_map[e_name], l_map[l_name]
            # create electrical subclasses
            output.append((early, late, score, (e_name, l_name)))

        # TODO convert this to use unionOf?
        disjoints = []
        for early, late, _, names in output:  # make more CELLS mappings are done above

            e_res = infixowl.Restriction(self.expand(e_edge), graph=self.graph.g, someValuesFrom=early)
            l_res = infixowl.Restriction(self.expand(l_edge), graph=self.graph.g, someValuesFrom=late)

            self.ilx_start += 1  # FIXME the other option here is to try disjoint union???
            id_ = ilx_base.format(self.ilx_start)
            id_ = self.expand(id_)
            disjoints.append(id_)
            c = infixowl.Class(id_, graph=self.graph.g)
            intersection = infixowl.BooleanClass(operator=rdflib.OWL.intersectionOf, members=(e_res, l_res), graph=self.graph.g)
            #c.subClassOf = [e_res, l_res]  # handy that...
            c.subClassOf = [intersection]
            self.graph.add_node(id_, rdflib.RDFS.subClassOf, self.id_)  # how to do this with c.subClassOf...

            #self.mutually_disjoints[i_spiking_phenotype].add(early)  # done in phenotypes
            #self.mutually_disjoints[s_spiking_phenotype].add(late)  # done in phenotypes

            # a terrible way to set labels here  FIXME
            outer_ephys = tuple(self.labels_ephys)
            self.labels_ephys.append(''.join(names))  # join early and late into a single name
            c.label = self._make_label()
            self.labels_ephys = list(outer_ephys)




        disjointunion = disjointUnionOf(graph=self.graph.g, members=disjoints)
        self.graph.add_node(self.id_, rdflib.OWL.disjointUnionOf, disjointunion)

        #print(value)
        #print(output)

    def Other_electrical_classifications(self, value):
        values = value.split(self._sep)
        output = []
        for v in values:
            output.append(v)

        valid_mappings = {'Fast spiking':fast_phenotype,
                          'Non-fast spiking':reg_phenotype,  # only in this very limited context
                          'Regular spiking non-pyramidal':reg_phenotype}
        for v in output:
            # TODO these need to map to fast spiking or
            # regular spiking interneuron (need a better name that only depends on ephys)
            if v in valid_mappings:
                id_ = self.graph.expand(valid_mappings[v])
                restriction = infixowl.Restriction(self.expand(spiking_edge), graph=self.graph.g, someValuesFrom=id_)
                self.Class.subClassOf = [restriction]
                self.labels_ephys = ['fast spiking' if v == 'Fast spiking' else 'regular spiking non pyramidal'] # TODO need the above as well but trickier to do that

            
            #if v not in self.phenotype_iri_map:
                #id_ = self._make_phenotype(v, spiking_phenotype, spiking_edge, ephys_defined)
                #self.phenotype_iri_map[v] = id_
            #else:
                #id_ = self.phenotype_iri_map[v]
                #restriction = infixowl.Restriction(self.expand(spiking_edge), graph=self.graph.g, someValuesFrom=id_)
                #self.Class.subClassOf = [restriction]

        #print(value)
        print(output)

    def _make_phenotype(self, phenotype_lbl, parent_pheno, p_edge, p_defined):
        return 'http://lolwut.com'
        # electrical here? or can we do those as needed above?
        self.ilx_start += 1
        id_ = ilx_base.format(self.ilx_start)
        id_ = self.expand(id_)
        #self.graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
        #self.graph.add_node(id_, rdflib.RDFS.subClassOf, parent_pheno)

        Class = infixowl.Class(id_, graph=self.graph.g)
        Class.subClassOf = [self.expand(parent_pheno)]
        Class.label =  rdflib.Literal(phenotype_lbl + ' phenotype')

        pheno_iri = id_
        return pheno_iri

    def _make_mutually_disjoint(self, things):
        if len(things) > 1:
            first, rest = things[0], things[1:]
            for r in rest:
                print(first, r)
                self.graph.add_node(first, rdflib.OWL.disjointWith, r)
            return self._make_mutually_disjoint(rest)
        else:
            return things

    def _row_post(self):
        self.Class.label = self._make_label()

    def _end(self):
        for superClass, disjoint_things in self.mutually_disjoints.items():
            print(superClass)
            print(disjoint_things)
            make_mutually_disjoint(self.graph, sorted(disjoint_things))

