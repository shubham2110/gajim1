'''
Tests for capabilities and the capabilities cache
'''
import unittest
from unittest.mock import MagicMock, Mock

from nbxmpp import NS_MUC, NS_PING, NS_XHTML_IM, NS_JINGLE_FILE_TRANSFER_5
from nbxmpp.structs import DiscoIdentity
from nbxmpp.structs import DiscoInfo
from gajim.common import caps_cache as caps
from gajim.common.structs import CapsData


class CommonCapsTest(unittest.TestCase):

    def setUp(self):
        self.caps_method = 'sha-1'
        self.caps_hash = 'm3P2WeXPMGVH2tZPe7yITnfY0Dw='
        self.client_caps = (self.caps_method, self.caps_hash)

        self.node = "http://gajim.org"
        self.identity = DiscoIdentity(category='client',
                                      type='pc',
                                      name='Gajim')

        self.identities = [self.identity]
        self.features = [NS_MUC, NS_XHTML_IM, NS_JINGLE_FILE_TRANSFER_5]

        # Simulate a filled db
        db_caps_cache = {
            (self.caps_method, self.caps_hash): CapsData(self.identities, self.features, []),
            ('old', self.node + '#' + self.caps_hash): CapsData(self.identities, self.features, [])
        }

        self.logger = Mock()
        self.logger.load_caps_data = Mock(return_value=db_caps_cache)

        self.cc = caps.CapsCache(self.logger)
        caps.capscache = self.cc


class TestCapsCache(CommonCapsTest):

    def test_set_retrieve(self):
        ''' Test basic set / retrieve cycle '''

        self.cc[self.client_caps].identities = self.identities
        self.cc[self.client_caps].features = self.features

        self.assertTrue(NS_MUC in self.cc[self.client_caps].features)
        self.assertTrue(NS_PING not in self.cc[self.client_caps].features)

        identities = self.cc[self.client_caps].identities

        self.assertEqual(1, len(identities))

        identity = identities[0]
        self.assertEqual('client', identity.category)
        self.assertEqual('pc', identity.type)

    def test_set_and_store(self):
        ''' Test client_caps update gets logged into db '''

        disco_info = DiscoInfo(None, self.identities, self.features, [])

        item = self.cc[self.client_caps]
        item.set_and_store(disco_info)

        self.logger.add_caps_entry.assert_called_once_with(self.caps_method,
                                                           self.caps_hash,
                                                           disco_info)

    def test_initialize_from_db(self):
        ''' Read cashed dummy data from db '''
        self.assertEqual(self.cc[self.client_caps].status, caps.NEW)
        self.cc.initialize_from_db()
        self.assertEqual(self.cc[self.client_caps].status, caps.CACHED)

    def test_preload_triggering_query(self):
        ''' Make sure that preload issues a disco '''
        connection = MagicMock()
        client_caps = caps.ClientCaps(self.caps_hash, self.node, self.caps_method)

        self.cc.query_client_of_jid_if_unknown(
            connection, "test@gajim.org", client_caps)

        self.assertEqual(1, connection.get_module('Discovery').disco_contact.call_count)

    def test_no_preload_query_if_cashed(self):
        ''' Preload must not send a query if the data is already cached '''
        connection = MagicMock()
        client_caps = caps.ClientCaps(self.caps_hash, self.node, self.caps_method)

        self.cc.initialize_from_db()
        self.cc.query_client_of_jid_if_unknown(
            connection, "test@gajim.org", client_caps)

        self.assertEqual(0, connection.get_module('Discovery').disco_contact.call_count)


class TestClientCaps(CommonCapsTest):

    def setUp(self):
        CommonCapsTest.setUp(self)
        self.client_caps = caps.ClientCaps(self.caps_hash, self.node, self.caps_method)

    def test_query_by_get_discover_strategy(self):
        ''' Client must be queried if the data is unkown '''
        connection = MagicMock()
        discover = self.client_caps.get_discover_strategy()
        discover(connection, "test@gajim.org")
        connection.get_module('Discovery').disco_contact.assert_called_once_with(
            'test@gajim.org', 'http://gajim.org#m3P2WeXPMGVH2tZPe7yITnfY0Dw=')

    def test_client_supports(self):
        self.assertTrue(caps.client_supports(self.client_caps, NS_PING),
                        msg="Assume supported, if we don't have caps")

        self.assertFalse(caps.client_supports(self.client_caps, NS_JINGLE_FILE_TRANSFER_5),
                msg="Must not assume blacklisted feature is supported on default")

        self.cc.initialize_from_db()

        self.assertFalse(caps.client_supports(self.client_caps, NS_PING),
                        msg="Must return false on unsupported feature")

        self.assertTrue(caps.client_supports(self.client_caps, NS_XHTML_IM),
                        msg="Must return True on supported feature")

        self.assertTrue(caps.client_supports(self.client_caps, NS_MUC),
                        msg="Must return True on supported feature")


class TestOldClientCaps(TestClientCaps):

    def setUp(self):
        TestClientCaps.setUp(self)
        self.client_caps = caps.OldClientCaps(self.caps_hash, self.node)

    def test_query_by_get_discover_strategy(self):
        ''' Client must be queried if the data is unknown '''
        connection = MagicMock()
        discover = self.client_caps.get_discover_strategy()
        discover(connection, "test@gajim.org")

        connection.get_module('Discovery').disco_contact.assert_called_once_with('test@gajim.org')

if __name__ == '__main__':
    unittest.main()
