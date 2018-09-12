from nose.tools import assert_raises
from ilxutils.ilx_pred_map import IlxPredMap


class TestILXPredMap:

    def setup(self):
        self.ipm = IlxPredMap()

    def teardown(self):
        pass

    def test_create_ext2ilx_map(self):
        # Checking if each accepted predicate is in the mapping correctly
        for common_name, accepted_preds in self.ipm.common2preds.items():
            for acc_pred in accepted_preds:

                if acc_pred[-1] == ':': # "prefix:" only
                    curie_acc_pred = acc_pred
                else:
                    curie_acc_pred = 'ns:' + acc_pred
                iri_acc_pred = 'http/scicrunch.org/pred/' + acc_pred

                assert self.ipm.get_common_pred(curie_acc_pred) == common_name
                assert self.ipm.get_common_pred(iri_acc_pred) == common_name

        # Badly formated predicate
        with assert_raises(SystemExit):
            self.ipm.get_common_pred('label')

        # Unacceptable predicate
        assert self.ipm.get_common_pred('ns1:example') == None
