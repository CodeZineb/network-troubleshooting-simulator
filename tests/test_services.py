"""Tests for simulated DHCP and DNS services."""

import unittest

from src.services import (
    DHCPServer,
    DNSServer,
    format_service_status,
    get_service_status,
)
from src.subnetting import get_ip_network


class TestServices(unittest.TestCase):
    """Test suite validating simulated DHCP and DNS servers."""

    def setUp(self):
        """Set up fresh DHCP and DNS server instances for each test."""
        self.dhcp = DHCPServer()
        self.dns = DNSServer()

    # -----------------------------------------------------------------------
    # DHCP Tests
    # -----------------------------------------------------------------------

    def test_dhcp_can_allocate_ip(self):
        """1. DHCP can allocate an IP."""
        response = self.dhcp.request_ip("PC-IT-03", vlan_id=10)
        self.assertTrue(response.success)
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.ip_address, "192.168.10.100")
        self.assertEqual(response.client_id, "PC-IT-03")
        self.assertEqual(response.vlan_id, 10)

    def test_allocated_ip_belongs_to_correct_vlan(self):
        """2. Allocated IP belongs to the correct VLAN network."""
        response = self.dhcp.request_ip("PC-HR-03", vlan_id=20)
        self.assertTrue(response.success)
        self.assertTrue(get_ip_network(response.ip_address, "192.168.20.0/24"))
        self.assertEqual(response.subnet_mask, "255.255.255.0")

    def test_gateway_is_correctly_returned(self):
        """3. Gateway is correctly returned."""
        it_resp = self.dhcp.request_ip("PC-IT-03", vlan_id=10)
        self.assertEqual(it_resp.default_gateway, "192.168.10.1")
        self.assertEqual(it_resp.gateway, "192.168.10.1")

        guest_resp = self.dhcp.request_ip("PC-GUEST-03", vlan_id=40)
        self.assertEqual(guest_resp.default_gateway, "192.168.40.1")
        self.assertEqual(guest_resp.gateway, "192.168.40.1")

    def test_multiple_clients_receive_different_ips(self):
        """4. Multiple clients receive different IPs."""
        client1 = self.dhcp.request_ip("PC-IT-03", vlan_id=10)
        client2 = self.dhcp.request_ip("PC-IT-04", vlan_id=10)
        client3 = self.dhcp.request_ip("PC-IT-05", vlan_id=10)

        self.assertTrue(client1.success)
        self.assertTrue(client2.success)
        self.assertTrue(client3.success)

        self.assertNotEqual(client1.ip_address, client2.ip_address)
        self.assertNotEqual(client2.ip_address, client3.ip_address)
        self.assertEqual(client1.ip_address, "192.168.10.100")
        self.assertEqual(client2.ip_address, "192.168.10.101")
        self.assertEqual(client3.ip_address, "192.168.10.102")

    def test_released_ip_becomes_available_again(self):
        """5. Released IP becomes available again."""
        client1 = self.dhcp.request_ip("PC-IT-03", vlan_id=10)
        allocated_ip = client1.ip_address

        released = self.dhcp.release_ip("PC-IT-03", vlan_id=10)
        self.assertTrue(released)

        # Allocate for a new client; the deterministic strategy reuses the lowest available IP
        new_client = self.dhcp.request_ip("PC-IT-99", vlan_id=10)
        self.assertEqual(new_client.ip_address, allocated_ip)

    def test_dhcp_failure_returns_failure_result(self):
        """6. DHCP failure returns an appropriate failure result."""
        self.dhcp.set_status("DOWN")
        self.assertFalse(self.dhcp.is_available())

        response = self.dhcp.request_ip("PC-IT-03", vlan_id=10)
        self.assertFalse(response.success)
        self.assertEqual(response.status, "SERVICE_DOWN")
        self.assertIsNone(response.ip_address)
        self.assertIsNotNone(response.error_message)

    # -----------------------------------------------------------------------
    # DNS Tests
    # -----------------------------------------------------------------------

    def test_known_hostname_resolves_correctly(self):
        """7. Known hostname resolves correctly."""
        resp1 = self.dns.resolve("PC-IT-01")
        self.assertTrue(resp1.success)
        self.assertEqual(resp1.ip_address, "192.168.10.10")

        # Case-insensitive resolution
        resp2 = self.dns.resolve("srv-01")
        self.assertTrue(resp2.success)
        self.assertEqual(resp2.ip_address, "192.168.30.10")

    def test_reverse_lookup_resolves_correctly(self):
        """8. Reverse lookup resolves correctly."""
        resp = self.dns.reverse_lookup("192.168.20.10")
        self.assertTrue(resp.success)
        self.assertEqual(resp.hostname, "PC-HR-01")

        resp_srv = self.dns.reverse_lookup("192.168.30.11")
        self.assertTrue(resp_srv.success)
        self.assertEqual(resp_srv.hostname, "SRV-02")

    def test_unknown_hostname_returns_not_found(self):
        """9. Unknown hostname returns NOT_FOUND."""
        resp = self.dns.resolve("NON-EXISTENT-HOST")
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, "NOT_FOUND")
        self.assertIsNone(resp.ip_address)

        resp_rev = self.dns.reverse_lookup("192.168.99.99")
        self.assertFalse(resp_rev.success)
        self.assertEqual(resp_rev.status, "NOT_FOUND")

    def test_dns_failure_returns_failure_result(self):
        """10. DNS failure returns an appropriate failure result."""
        self.dns.set_status("DOWN")
        self.assertFalse(self.dns.is_available())

        resp = self.dns.resolve("PC-IT-01")
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, "SERVICE_DOWN")
        self.assertIsNone(resp.ip_address)

        resp_rev = self.dns.reverse_lookup("192.168.10.10")
        self.assertFalse(resp_rev.success)
        self.assertEqual(resp_rev.status, "SERVICE_DOWN")

    def test_new_dns_record_can_be_added(self):
        """11. A new DNS record can be added."""
        added = self.dns.add_record("PRINTER-IT-01", "192.168.10.50")
        self.assertTrue(added)

        resp = self.dns.resolve("PRINTER-IT-01")
        self.assertTrue(resp.success)
        self.assertEqual(resp.ip_address, "192.168.10.50")

        # Also test reverse lookup of newly added record
        rev_resp = self.dns.reverse_lookup("192.168.10.50")
        self.assertTrue(rev_resp.success)
        self.assertEqual(rev_resp.hostname, "PRINTER-IT-01")

    def test_dns_record_can_be_removed(self):
        """12. A DNS record can be removed."""
        self.dns.add_record("TEMP-PC", "192.168.10.99")
        self.assertTrue(self.dns.resolve("TEMP-PC").success)

        removed = self.dns.remove_record("TEMP-PC")
        self.assertTrue(removed)

        resp = self.dns.resolve("TEMP-PC")
        self.assertEqual(resp.status, "NOT_FOUND")

    # -----------------------------------------------------------------------
    # Status Representation Tests
    # -----------------------------------------------------------------------

    def test_service_status_representation(self):
        """Test status dictionary and text formatting."""
        status = get_service_status(self.dhcp, self.dns)
        self.assertEqual(status, {"DHCP": "UP", "DNS": "UP"})
        self.assertEqual(
            format_service_status(self.dhcp, self.dns), "DHCP: UP\nDNS: UP"
        )

        self.dhcp.set_status("DOWN")
        self.dns.set_status("DOWN")
        self.assertEqual(
            format_service_status(self.dhcp, self.dns), "DHCP: DOWN\nDNS: DOWN"
        )


if __name__ == "__main__":
    unittest.main()
