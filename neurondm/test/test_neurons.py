import pytest
from test.common import _TestNeuronsBase, pyel, tel
from neurondm.core import UnionOf, IntersectionOf, IntersectionOfPartOf
'''
class TestNeurons(_TestNeuronsBase):
    # TODO make sure this runs after cli test? it should ...
    # but then we need to keep the output of ndl around

    def test_load_existing(self):
        from neurondm.lang import Neuron, Config
        config = Config('neuron_data_lifted')
        config.load_existing()
        assert len(Neuron.load_graph)
        neurons = Neuron.neurons()
        assert neurons

    def test_zz_adopt(self):
        from neurondm.lang import Neuron, Phenotype, Config
        ndl_config = Config('neuron_data_lifted')
        ndl_config.load_existing()
        bn_config = Config('basic-neurons')
        bn_config.load_existing()
        ndl_neurons = ndl_config.neurons()
        bn_neurons = bn_config.neurons()
        config = Config('__test_output', ttl_export_dir=tel)
        shapeshifter = Neuron(Phenotype('TEMP:soul-stealer'))
        for n in ndl_neurons:
            shapeshifter.adopt_meta(n)

        assert list(n.synonyms)
        assert list(n.definitions)
        n.write()

        assert list(shapeshifter.synonyms)
        assert list(shapeshifter.definitions)
        shapeshifter.write()

        # it eats _all_ of them
        allsyns = set(shapeshifter.synonyms)
        alldefs = set(shapeshifter.definitions)
        assert all(s in allsyns for s in n.synonyms)
        assert all(s in alldefs for s in n.definitions)

    def test_fail(self):
        from neurondm.lang import Neuron, Phenotype, Config
        bn_config = Config('basic-neurons')
        # TODO config.activate()? context manager for config ... too ...
        Neuron(Phenotype('TEMP:test'))
        try:
            bn_config.load_existing()
            raise AssertionError('Should have failed because a neuron has been created')
        except Config.ExistingNeuronsError as e:
            pass

    def test_0_equality(self):
        """ make sure that __eq__ and __hash__ are implmented correctly """
        from neurondm import Config, Neuron, Phenotype, NegPhenotype
        from neurondm import LogicalPhenotype, AND, OR, ilxtr
        from neurondm import NeuronCUT, NeuronEBM

        config = Config('test-equality', ttl_export_dir=tel, py_export_dir=pyel)

        pp = Phenotype(ilxtr.a)
        pn = NegPhenotype(ilxtr.a)
        assert pp != pn
        assert hash(pp) != hash(pn)

        assert Phenotype(ilxtr.c) == Phenotype(ilxtr.c)
        assert NegPhenotype(ilxtr.c) == NegPhenotype(ilxtr.c)
        assert hash(Phenotype(ilxtr.c)) == hash(Phenotype(ilxtr.c))
        assert hash(NegPhenotype(ilxtr.c)) == hash(NegPhenotype(ilxtr.c))

        lppo = LogicalPhenotype(OR, pp, Phenotype(ilxtr.b))
        lppa = LogicalPhenotype(AND, pp, Phenotype(ilxtr.b))
        lpno = LogicalPhenotype(OR, pn, NegPhenotype(ilxtr.b))
        assert lppo != lppa
        assert lppo != lpno
        assert lppa != lpno
        assert hash(lppo) != hash(lppa)
        assert hash(lppo) != hash(lpno)
        assert hash(lppa) != hash(lpno)

        lpe1 = LogicalPhenotype(OR, Phenotype(ilxtr.c), Phenotype(ilxtr.d))
        lpe2 = LogicalPhenotype(OR, Phenotype(ilxtr.c), Phenotype(ilxtr.d))
        assert lpe1 == lpe2
        assert hash(lpe1) == hash(lpe2)

        # make sure that self.pes equality works
        assert (pp, pn, lppo, lppa, lpno) == (pp, pn, lppo, lppa, lpno)

        npp = Neuron(pp)
        npn = Neuron(pn)
        assert npp != npn
        assert hash(npp) != hash(npn)

        nlppo = Neuron(lppo)
        nlppa = Neuron(lppa)
        nlpno = Neuron(lpno)

        assert nlppo != nlppa
        assert nlppo != nlpno
        assert nlppa != nlpno
        assert hash(nlppo) != hash(nlppa)
        assert hash(nlppo) != hash(nlpno)
        assert hash(nlppa) != hash(nlpno)

        assert Neuron(pp) == Neuron(pp)
        assert Neuron(pn) == Neuron(pn)
        assert hash(Neuron(pp)) == hash(Neuron(pp))
        assert hash(Neuron(pn)) == hash(Neuron(pn))

        assert NeuronCUT(pp) != NeuronEBM(pp)
        assert hash(NeuronCUT(pp)) != hash(NeuronEBM(pp))


'''

class TestRoundtrip(_TestNeuronsBase):
    # need to test other more complex constructs

    pyname = 'test-py'
    ttlname = 'test-ttl'

    phn_py = 'TEMP:python-phenotype'
    phn_py_loc = 'TEMP:python-location'
    phn_ttl = 'TEMP:turtle-phenotype'
    phn_ttl_loc = 'TEMP:turtle-location'

    def setUp(self):
        super().setUp()
        from neurondm import Config, Neuron, Phenotype, NegPhenotype
        from neurondm import EntailedPhenotype, NegEntailedPhenotype
        from neurondm import core
        self.Config = Config
        self.Neuron = Neuron
        self.Phenotype = Phenotype
        self.NegPhenotype = NegPhenotype
        self.EntailedPhenotype = EntailedPhenotype
        self.NegEntailedPhenotype = NegEntailedPhenotype

        if core.offline:
            import augpathlib as aug
            rptel = aug.RepoPath(tel)
            rpsrc = aug.RepoPath('~/git/NIF-Ontology').expanduser().resolve()
            self.ont_repo = rptel.clone_from(rpsrc)
        else:
            self.ont_repo = tel

    def tearDown(self):
        super().tearDown()

    def test_neurdf(self):
        config = self.Config(self.pyname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        n1 = self.Neuron(self.Phenotype(self.phn_py))
        n2 = self.Neuron(self.NegPhenotype(self.phn_py))
        assert n1 != n2
        self.Neuron(self.Phenotype(self.phn_py_loc, 'ilxtr:hasLocationPhenotype'))
        self.Neuron(self.NegPhenotype(self.phn_py_loc, 'ilxtr:hasLocationPhenotype'))
        out = config.neurdf_ttl()
        print(out)

    def test_py_simple(self):

        # FIXME conflation of read location and write location for
        # ontology, esp annoying when offline
        config = self.Config(self.pyname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        n1 = self.Neuron(self.Phenotype(self.phn_py))
        n2 = self.Neuron(self.NegPhenotype(self.phn_py))
        assert n1 != n2
        self.Neuron(self.Phenotype(self.phn_py_loc, 'ilxtr:hasLocationPhenotype'))
        self.Neuron(self.NegPhenotype(self.phn_py_loc, 'ilxtr:hasLocationPhenotype'))
        config.write_python()
        config.ttl()  # populate out_graph for later debug
        py1 = config.python()

        config2 = self.Config(self.pyname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        try:
            config2.load_python()  # FIXME load existing python ... FIXME nasty network issues
        except Exception as e:
            breakpoint()
            raise e

        py2 = config2.python()

        assert config.existing_pes is not config2.existing_pes
        assert config.neurons() == config2.neurons(), (config.out_graph.debug(), config2.out_graph.debug(),
                                                       print('py1\n', py1), print('py2\n', py2),
                                                       breakpoint())

        config2.write()
        #config2.out_graph.debug()

        config3 = self.Config(self.pyname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        config3.load_existing()
        py3 = config3.python()

        assert config2.existing_pes is not config3.existing_pes
        assert config2.neurons() == config3.neurons(), (config2.out_graph.debug(), config3.out_graph.debug(),
                                                        print('py2\n', py2), print('py3\n', py3),
                                                        breakpoint())

    def test_ttl_simple(self):
        # madness spreads apparently, here is a minimal repro for the issue
        # pytest test/test_madness.py test/test_neurons.py -k 'test_ttl_simple or test_entailed_predicate'
        # The other classes in this file can be commented out
        # an even more specific repro
        # pytest test/test_madness.py test/test_neurons.py \
        # -k 'test_madness and test_ttl_simple or
        #     test_neurons and test_entailed_predicate or
        #     test_neurons and test_ttl_simple'

        config = self.Config(self.ttlname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        self.Neuron(self.Phenotype(self.phn_ttl))
        self.Neuron(self.NegPhenotype(self.phn_ttl))
        self.Neuron(self.Phenotype(self.phn_ttl_loc, 'ilxtr:hasLocationPhenotype'))
        self.Neuron(self.NegPhenotype(self.phn_ttl_loc, 'ilxtr:hasLocationPhenotype'))
        config.write()
        a = config.neurons()

        config2 = self.Config(self.ttlname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        config2.load_existing()
        config2.write_python()
        b = config2.neurons()

        config3 = self.Config(self.ttlname, ttl_export_dir=self.ont_repo, py_export_dir=pyel)
        config3.load_python()
        c = config3.neurons()

        print(a, b, c)
        assert config.existing_pes is not config2.existing_pes is not config3.existing_pes
        if not a == b == c:
            breakpoint()
        # so somehow when test_entailed_predicate is called along with test_ttl_simple
        # n1 from that sneeks into config3, but ONLY when this class is imported into
        # another file AND that file is run, so this seems like it is happening because
        # somehow the tep neuron persists through the tearDown, and for some reason
        # importing a testing module into another file is sufficient to keep the
        # garbage collector from collecting between runs or something ??!?
        assert a == b == c

    def test_entailed_predicate(self):
        p1 = self.Phenotype('ilxtr:somewhere', 'ilxtr:hasLocationPhenotype')
        p2 = self.EntailedPhenotype('ilxtr:somewhere', 'ilxtr:hasLocationPhenotype')
        n1 = self.Neuron(p1, p2)
        n1._graphify()
        # TODO assert to make sure the pattern is right


class TestEntailedRoundtrip(TestRoundtrip):

    phn_py = 'TEMP:python-phenotype-ent'
    phn_py_loc = 'TEMP:python-location-ent'
    phn_ttl = 'TEMP:turtle-phenotype-ent'
    phn_ttl_loc = 'TEMP:turtle-location-ent'

    def setUp(self):
        # LOL PYTHON
        super().setUp()
        self.Phenotype = self.EntailedPhenotype
        self.NegPhenotype = self.NegEntailedPhenotype


class TestOwlObjectRoundtrip(TestRoundtrip):

    op = UnionOf
    phn_py = op('TEMP:python-phenotype-1', 'TEMP:python-phenotype-2')
    phn_py_loc = op('TEMP:python-location-1', 'TEMP:python-location-2')
    phn_ttl = op('TEMP:turtle-phenotype-1', 'TEMP:turtle-phenotype-2')
    phn_ttl_loc = op('TEMP:turtle-location-1', 'TEMP:turtle-location-2')


class TestEntailedOwlObjectRoundtrip(TestRoundtrip):

    op = UnionOf
    phn_py = op('TEMP:python-phenotype-ent-1', 'TEMP:python-phenotype-ent-2')
    phn_py_loc = op('TEMP:python-location-ent-1', 'TEMP:python-location-ent-2')
    phn_ttl = op('TEMP:turtle-phenotype-ent-1', 'TEMP:turtle-phenotype-ent-2')
    phn_ttl_loc = op('TEMP:turtle-location-ent-1', 'TEMP:turtle-location-ent-2')

    def setUp(self):
        # LOL PYTHON
        super().setUp()
        self.Phenotype = self.EntailedPhenotype
        self.NegPhenotype = self.NegEntailedPhenotype


class TestNestOwlObjectRoundtrip(TestRoundtrip):

    op = UnionOf
    opn = IntersectionOf
    phn_py = op(opn('TEMP:python-phenotype-1', 'TEMP:python-phenotype-2'), opn('TEMP:python-phenotype-3', 'TEMP:python-phenotype-4'))
    phn_py_loc = op(opn('TEMP:python-location-1', 'TEMP:python-location-2'),   opn('TEMP:python-location-3', 'TEMP:python-location-4'))
    phn_ttl = op(opn('TEMP:turtle-phenotype-1', 'TEMP:turtle-phenotype-2'), opn('TEMP:turtle-phenotype-3', 'TEMP:turtle-phenotype-4'))
    phn_ttl_loc = op(opn('TEMP:turtle-location-1', 'TEMP:turtle-location-2'),   opn('TEMP:turtle-location-3', 'TEMP:turtle-location-4'))

    @pytest.mark.xfail
    def test_neurdf(self):
        super().test_neurdf()


class TestEntailedNestOwlObjectRoundtrip(TestRoundtrip):

    op = UnionOf
    opn = IntersectionOf
    phn_py = op(opn('TEMP:python-phenotype-ent-1', 'TEMP:python-phenotype-ent-2'), opn('TEMP:python-phenotype-ent-3', 'TEMP:python-phenotype-ent-4'))
    phn_py_loc = op(opn('TEMP:python-location-ent-1', 'TEMP:python-location-ent-2'),   opn('TEMP:python-location-ent-3', 'TEMP:python-location-ent-4'))
    phn_ttl = op(opn('TEMP:turtle-phenotype-ent-1', 'TEMP:turtle-phenotype-ent-2'), opn('TEMP:turtle-phenotype-ent-3', 'TEMP:turtle-phenotype-ent-4'))
    phn_ttl_loc = op(opn('TEMP:turtle-location-ent-1', 'TEMP:turtle-location-ent-2'),   opn('TEMP:turtle-location-ent-3', 'TEMP:turtle-location-ent-4'))

    def setUp(self):
        # LOL PYTHON
        super().setUp()
        self.Phenotype = self.EntailedPhenotype
        self.NegPhenotype = self.NegEntailedPhenotype

    @pytest.mark.xfail
    def test_neurdf(self):
        super().test_neurdf()


class TestRoundtripCUT(TestRoundtrip):

    pyname = 'test-cut-py'  # can't import the same module name twice
    ttlname = 'test-cut-ttl'

    def setUp(self):
        super().setUp()
        from neurondm import NeuronCUT
        self.Neuron = NeuronCUT



class TestLabels(_TestNeuronsBase):
    def setUp(self):
        super().setUp()
        from neurondm import Config, Neuron, Phenotype, NegPhenotype
        from neurondm import EntailedPhenotype, LogicalPhenotype, AND
        self.AND = AND
        self.Config = Config
        self.Neuron = Neuron
        self.Phenotype = Phenotype
        self.NegPhenotype = NegPhenotype
        self.EntailedPhenotype = EntailedPhenotype
        self.LogicalPhenotype = LogicalPhenotype

    def test_nest_logical(self):
        AND = self.AND
        Neuron = self.Neuron
        LogicalPhenotype = self.LogicalPhenotype
        Phenotype = self.Phenotype
        n1 = Neuron(Phenotype('NCBITaxon:10090',
                              'ilxtr:hasInstanceInTaxon',
                              label='Mus musculus'),
                    LogicalPhenotype(AND,
                                     Phenotype('NCBIGene:50779',
                                               'ilxtr:hasExpressionPhenotype',
                                               label='Rgs6'),
                                     LogicalPhenotype(AND,
                                                      Phenotype('ilxtr:GABAReceptor',
                                                                'ilxtr:hasExpressionPhenotype',
                                                                label='GABAR'))),
                    label='test logical')

        n2 = Neuron(Phenotype('NCBITaxon:10090',
                              'ilxtr:hasInstanceInTaxon',
                              label='Mus musculus'),
                    LogicalPhenotype(AND,
                                     Phenotype('NCBIGene:50779',
                                               'ilxtr:hasExpressionPhenotype',
                                               label='Rgs6'),
                                     Phenotype('ilxtr:GABAReceptor',
                                               'ilxtr:hasExpressionPhenotype',
                                               label='GABAR')),
                    label='test logical')

        n1l = n1.genLabel
        n2l = n2.genLabel
        assert '(intersectionOf' in n1l, n1l
        assert '(intersectionOf' in n2l, n2l
