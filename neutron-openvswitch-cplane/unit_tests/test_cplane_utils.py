#!/usr/bin/python
from mock import MagicMock, patch, call
from collections import OrderedDict 
from test_utils import CharmTestCase, unittest
import charmhelpers.core.hookenv as hookenv
import charmhelpers
charmhelpers.core.hookenv.config = MagicMock()
import cplane_utils
from cplane_package_manager import(
    CPlanePackageManager
)


TO_PATCH = [
    'relation_ids',
    'related_units',
    'relation_get',
    'juju_log',
    'config',
    'add_bridge',
    'check_interface',
]

CPLANE_URL = "https://www.dropbox.com/s/h2edle1o0jj1btt/cplane_metadata.json?dl=1"
class CplaneUtilsTest(CharmTestCase):

    def setUp(self):
        super(CplaneUtilsTest, self).setUp(cplane_utils, TO_PATCH)
        self.relation_ids.return_value = ['random_rid']
        self.related_units.return_value = ['random_unit']
        self.relation_get.return_value = True
        self.config.return_value = 'random_interface'

    def tearDown(self):
        super(CplaneUtilsTest, self).tearDown()
        call(["rm", "-f", "/tmp/cplane.ini"])

    def test_determine_packages(self):
        self.assertEqual(cplane_utils.determine_packages(),
                         ['neutron-metadata-agent', 'neutron-plugin-ml2', 'crudini', 'dkms', 'iputils-arping', 'dnsmasq'])

    def test_crudini_set(self):
        call(["echo", "[DEFAULT]", ">", "/tmp/cplane.init"])
        call(["echo", "TEST = TEST", ">>", "/tmp/cplane.init"]) 
        cplane_utils.crudini_set('/tmp/cplane.ini', 'DEFAULT', 'TEST', 'CPLANE')
        self.assertEqual('TEST = CPLANE' in open('/tmp/cplane.ini').read(), True)

    def test_manage_fip(self):
        
        # Check for correct fip interface
        self.check_interface.return_value = True
        
        cplane_utils.manage_fip()
        
        self.relation_ids.assert_called_with('cplane-controller-ovs')
        self.related_units.assert_called_with('random_rid')
        self.relation_get.assert_called_with(attribute='fip-set', unit='random_unit', rid='random_rid')
        self.config.assert_called_with('fip-interface')
        self.check_interface.assert_called_with('random_interface')    
        self.add_bridge.assert_called_with('br-fip', 'random_interface')
        
        # Check for incorrect fip interface
        self.check_interface.return_value = False
        
        cplane_utils.manage_fip()
        
        self.relation_ids.assert_called_with('cplane-controller-ovs')
        self.related_units.assert_called_with('random_rid')
        self.relation_get.assert_called_with(attribute='fip-set', unit='random_unit', rid='random_rid')
        self.config.assert_called_with('fip-interface')
        self.check_interface.assert_called_with('random_interface')
        self.juju_log.assert_called_with('Fip interface doesnt exist, and will be used by default by Cplane controller')

    @patch("subprocess.check_call")
    def test_set_cp_agent(self, m_check_call):
        #Check if valid port is returned
        self.relation_get.return_value = "9000"        
        cplane_utils.set_cp_agent()

        self.relation_ids.assert_called_with('cplane-controller-ovs')
        self.related_units.assert_called_with('random_rid')
        self.relation_get.assert_called_with('private-address')
        self.assertEqual(m_check_call.call_args, call(['cp-agentd', 'set-config', 'log-level=file:random_interface']))

        #Check if invallid port is returned

        self.relation_get.return_value = "0"
        cplane_utils.set_cp_agent()

        self.relation_ids.assert_called_with('cplane-controller-ovs')
        self.related_units.assert_called_with('random_rid')
        self.relation_get.assert_called_with('private-address')
        self.assertEqual(m_check_call.call_args, call(['cp-agentd', 'set-config', 'log-level=file:random_interface']))

    @patch("subprocess.check_call")
    def test_restart_services(self, m_check_call):
        cplane_utils.restart_services()
        self.assertEqual(m_check_call.call_args, call(['update-rc.d', 'cp-agentd', 'enable']))


suite = unittest.TestLoader().loadTestsFromTestCase(CplaneUtilsTest)
unittest.TextTestRunner(verbosity=2).run(suite)
