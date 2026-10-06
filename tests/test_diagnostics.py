"""Tests for simulated network diagnostic commands."""

import unittest

from src.diagnostics import (
    simulate_arp,
    simulate_ipconfig,
    simulate_nslookup,
    simulate_ping,
    simulate_route,
    simulate_traceroute,
)
from src.services import DNSServer


class TestDiagnostics(unittest.TestCase):
    """Test suite validating simulated ping, traceroute, nslookup, ipconfig, route, and arp."""

    def test_successful_ping_between_simulated_hosts(self):
        """1. Successful ping between simulated hosts."""
        # Inter-VLAN ping (IT to Servers)
        result = simulate_ping("192.168.10.10", "192.168.30.10")
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.success)
        self.assertEqual(result.packet_loss, "0%")
        self.assertEqual(result.latency, "10 ms")
        self.assertEqual(result.latency_ms, 10)
        self.assertEqual(result.reply_from, "192.168.30.10")

        # Intra-VLAN ping (IT to IT)
        same_vlan = simulate_ping("192.168.10.10", "192.168.10.11")
        self.assertEqual(same_vlan.status, "SUCCESS")
        self.assertEqual(same_vlan.latency, "2 ms")
        self.assertEqual(same_vlan.latency_ms, 2)
        self.assertEqual(same_vlan.packet_loss, "0%")

    def test_failed_ping_for_unknown_or_unroutable_destination(self):
        """2. Failed ping for an unknown/unroutable destination."""
        # Unroutable public/external IP (no default route configured)
        result = simulate_ping("192.168.10.10", "8.8.8.8")
        self.assertEqual(result.status, "FAILED")
        self.assertFalse(result.success)
        self.assertEqual(result.packet_loss, "100%")
        self.assertEqual(result.reason, "No route to destination")

        # Invalid IP string does not crash
        invalid_result = simulate_ping("192.168.10.10", "999.999.999.999")
        self.assertEqual(invalid_result.status, "FAILED")
        self.assertEqual(invalid_result.packet_loss, "100%")
        self.assertIn("Invalid IP", invalid_result.reason)

    def test_traceroute_between_two_vlans(self):
        """3. Traceroute between two VLANs."""
        result = simulate_traceroute("192.168.10.10", "192.168.30.10")
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.success)
        self.assertEqual(len(result.hops), 4)

        # Hop 1: Gateway
        self.assertEqual(result.hops[0].hop, 1)
        self.assertEqual(result.hops[0].address, "192.168.10.1")
        self.assertEqual(result.hops[0].name, "Gateway")

        # Hop 2: Router
        self.assertEqual(result.hops[1].hop, 2)
        self.assertEqual(result.hops[1].address, "Router")
        self.assertEqual(result.hops[1].name, "Router")

        # Hop 3: Destination Gateway
        self.assertEqual(result.hops[2].hop, 3)
        self.assertEqual(result.hops[2].address, "192.168.30.1")
        self.assertEqual(result.hops[2].name, "Destination Gateway")

        # Hop 4: Destination host
        self.assertEqual(result.hops[3].hop, 4)
        self.assertEqual(result.hops[3].address, "192.168.30.10")
        self.assertEqual(result.hops[3].name, "Destination")

        # Unroutable traceroute shows failure
        unroutable = simulate_traceroute("192.168.10.10", "10.0.0.99")
        self.assertEqual(unroutable.status, "FAILED")
        self.assertIn("No route exists", unroutable.reason)

    def test_successful_dns_lookup_nslookup(self):
        """4. Successful DNS lookup through simulated nslookup."""
        result = simulate_nslookup("SRV-01")
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.success)
        self.assertEqual(result.name, "SRV-01")
        self.assertEqual(result.address, "192.168.30.10")
        self.assertEqual(result.server, "Simulated-DNS")

        # Case-insensitive resolution
        hr_result = simulate_nslookup("pc-hr-02")
        self.assertEqual(hr_result.status, "SUCCESS")
        self.assertEqual(hr_result.address, "192.168.20.11")

    def test_unknown_hostname_nslookup(self):
        """5. Unknown hostname in nslookup."""
        result = simulate_nslookup("NON-EXISTENT-HOST")
        self.assertEqual(result.status, "NOT_FOUND")
        self.assertFalse(result.success)
        self.assertIsNone(result.address)
        self.assertIn("does not exist", result.reason)

        # Service down handling
        dns_down = DNSServer()
        dns_down.set_status("DOWN")
        down_result = simulate_nslookup("SRV-01", dns_server=dns_down)
        self.assertEqual(down_result.status, "SERVICE_DOWN")
        self.assertFalse(down_result.success)
        self.assertIn("unavailable", down_result.reason)

    def test_ipconfig_for_known_host(self):
        """6. ipconfig for a known host."""
        # By hostname
        result = simulate_ipconfig("PC-IT-01")
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.success)
        self.assertEqual(result.hostname, "PC-IT-01")
        self.assertEqual(result.ip_address, "192.168.10.10")
        self.assertEqual(result.subnet_mask, "255.255.255.0")
        self.assertEqual(result.default_gateway, "192.168.10.1")
        self.assertEqual(result.vlan, 10)
        self.assertEqual(result.network_address, "192.168.10.0")
        self.assertEqual(result.broadcast_address, "192.168.10.255")
        self.assertEqual(result.mac_address, "00:50:56:10:01:01")

        # By IP address
        by_ip = simulate_ipconfig("192.168.30.11")
        self.assertEqual(by_ip.status, "SUCCESS")
        self.assertEqual(by_ip.hostname, "SRV-02")
        self.assertEqual(by_ip.vlan, 30)

        # Unknown host handling
        unknown = simulate_ipconfig("UNKNOWN-MACHINE")
        self.assertEqual(unknown.status, "NOT_FOUND")
        self.assertFalse(unknown.success)

    def test_simulated_routing_table(self):
        """7. Simulated routing table."""
        table = simulate_route()
        self.assertEqual(len(table), 4)

        destinations = [r.destination_network for r in table]
        expected_destinations = [
            "192.168.10.0/24",
            "192.168.20.0/24",
            "192.168.30.0/24",
            "192.168.40.0/24",
        ]
        for dest in expected_destinations:
            self.assertIn(dest, destinations)

        for r in table:
            self.assertEqual(r.next_hop, "connected")
            self.assertEqual(r.route_type, "connected")
            self.assertIn(r.interface, ["VLAN10", "VLAN20", "VLAN30", "VLAN40"])

    def test_simulated_arp_table(self):
        """8. Simulated ARP table."""
        arp_table = simulate_arp()
        self.assertEqual(len(arp_table), 8)

        ips = [entry.ip_address for entry in arp_table]
        self.assertIn("192.168.10.10", ips)
        self.assertIn("192.168.20.10", ips)
        self.assertIn("192.168.30.10", ips)
        self.assertIn("192.168.40.10", ips)

        for entry in arp_table:
            self.assertTrue(entry.mac_address.startswith("00:50:56:"))
            self.assertIn(entry.vlan, [10, 20, 30, 40])
            self.assertTrue(len(entry.hostname) > 0)


if __name__ == "__main__":
    unittest.main()
