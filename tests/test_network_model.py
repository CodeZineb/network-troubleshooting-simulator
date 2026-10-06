"""Tests for the simulated enterprise network model."""

import unittest

from src.network_model import (
    DEFAULT_NETWORK,
    build_enterprise_network,
    find_host_by_hostname,
    find_host_by_ip,
    find_vlan_for_host,
    find_vlan_of_host,
    get_all_hosts,
    get_all_vlans,
    get_default_network,
    validate_ip_in_vlan,
)


class TestNetworkModel(unittest.TestCase):
    """Test suite validating enterprise network topology and helper methods."""

    def setUp(self):
        self.network = build_enterprise_network()

    def test_devices_present(self):
        devices = self.network.get_devices()
        device_names = [d.name for d in devices]
        self.assertIn("Router", device_names)
        self.assertIn("Core Switch", device_names)

        router = next(d for d in devices if d.name == "Router")
        switch = next(d for d in devices if d.name == "Core Switch")
        self.assertEqual(router.device_type, "router")
        self.assertEqual(switch.device_type, "switch")

    def test_vlans_present_and_configured(self):
        vlans = get_all_vlans(self.network)
        self.assertEqual(len(vlans), 4)

        expected_vlans = {
            10: ("IT", "192.168.10.0/24", "192.168.10.1"),
            20: ("HR", "192.168.20.0/24", "192.168.20.1"),
            30: ("Servers", "192.168.30.0/24", "192.168.30.1"),
            40: ("Guest", "192.168.40.0/24", "192.168.40.1"),
        }

        for vlan in vlans:
            self.assertIn(vlan.vlan_id, expected_vlans)
            name, net, gw = expected_vlans[vlan.vlan_id]
            self.assertEqual(vlan.name, name)
            self.assertEqual(vlan.network, net)
            self.assertEqual(vlan.gateway, gw)
            self.assertEqual(vlan.netmask, "255.255.255.0")
            self.assertEqual(vlan.prefix_length, 24)

    def test_hosts_present_and_configured(self):
        hosts = get_all_hosts(self.network)
        self.assertEqual(len(hosts), 8)

        expected_hosts = {
            "PC-IT-01": ("192.168.10.10", "192.168.10.1", 10, "workstation"),
            "PC-IT-02": ("192.168.10.11", "192.168.10.1", 10, "workstation"),
            "PC-HR-01": ("192.168.20.10", "192.168.20.1", 20, "workstation"),
            "PC-HR-02": ("192.168.20.11", "192.168.20.1", 20, "workstation"),
            "SRV-01": ("192.168.30.10", "192.168.30.1", 30, "server"),
            "SRV-02": ("192.168.30.11", "192.168.30.1", 30, "server"),
            "PC-GUEST-01": ("192.168.40.10", "192.168.40.1", 40, "workstation"),
            "PC-GUEST-02": ("192.168.40.11", "192.168.40.1", 40, "workstation"),
        }

        for host in hosts:
            self.assertIn(host.hostname, expected_hosts)
            ip, gw, vlan_id, dev_type = expected_hosts[host.hostname]
            self.assertEqual(host.ip_address, ip)
            self.assertEqual(host.default_gateway, gw)
            self.assertEqual(host.vlan_id, vlan_id)
            self.assertEqual(host.vlan, vlan_id)
            self.assertEqual(host.device_type, dev_type)
            self.assertEqual(host.subnet_mask, "255.255.255.0")
            self.assertEqual(host.prefix_length, 24)

    def test_find_host_by_hostname(self):
        host = find_host_by_hostname("pc-it-01", self.network)
        self.assertIsNotNone(host)
        self.assertEqual(host.hostname, "PC-IT-01")
        self.assertEqual(host.ip_address, "192.168.10.10")

        self.assertIsNone(find_host_by_hostname("NON-EXISTENT", self.network))

    def test_find_host_by_ip(self):
        host = find_host_by_ip("192.168.30.10", self.network)
        self.assertIsNotNone(host)
        self.assertEqual(host.hostname, "SRV-01")

        self.assertIsNone(find_host_by_ip("10.0.0.1", self.network))

    def test_find_vlan_of_host(self):
        vlan = find_vlan_of_host("PC-HR-02", self.network)
        self.assertIsNotNone(vlan)
        self.assertEqual(vlan.vlan_id, 20)
        self.assertEqual(vlan.name, "HR")

        host = find_host_by_hostname("PC-GUEST-01", self.network)
        vlan_by_obj = find_vlan_for_host(host, self.network)
        self.assertIsNotNone(vlan_by_obj)
        self.assertEqual(vlan_by_obj.vlan_id, 40)

        self.assertIsNone(find_vlan_of_host("UNKNOWN-HOST", self.network))

    def test_validate_ip_in_vlan(self):
        # Valid IPs
        self.assertTrue(validate_ip_in_vlan("192.168.10.50", 10, self.network))
        self.assertTrue(validate_ip_in_vlan("192.168.20.100", 20, self.network))

        # Host IPs within their respective VLAN
        for host in get_all_hosts(self.network):
            self.assertTrue(
                validate_ip_in_vlan(host.ip_address, host.vlan_id, self.network)
            )

        # Invalid IPs for VLAN 10
        self.assertFalse(validate_ip_in_vlan("192.168.20.10", 10, self.network))
        self.assertFalse(validate_ip_in_vlan("10.0.0.1", 10, self.network))
        self.assertFalse(validate_ip_in_vlan("not-an-ip", 10, self.network))

    def test_default_network_instance(self):
        self.assertIs(get_default_network(), DEFAULT_NETWORK)
        self.assertEqual(len(get_all_hosts()), 8)
        self.assertEqual(len(get_all_vlans()), 4)


if __name__ == "__main__":
    unittest.main()
