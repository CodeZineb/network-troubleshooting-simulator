"""Tests for simulated network incident scenarios."""

import unittest

from src.incidents import (
    IncidentManager,
    get_all_incidents,
    get_incident,
)
from src.network_model import build_enterprise_network
from src.routing import build_default_routing_table, can_route
from src.services import DHCPServer, DNSServer


class TestIncidents(unittest.TestCase):
    """Test suite validating simulated incident definitions, activation, and recovery."""

    def setUp(self):
        """Set up fresh isolated network and service instances for test isolation."""
        self.network = build_enterprise_network()
        self.routing_table = build_default_routing_table(self.network)
        self.dhcp = DHCPServer()
        self.dns = DNSServer()
        self.manager = IncidentManager(
            network=self.network,
            routing_table=self.routing_table,
            dhcp_server=self.dhcp,
            dns_server=self.dns,
        )

    def tearDown(self):
        """Ensure all incidents are reset after test."""
        self.manager.reset_all_incidents()

    def test_all_nine_incidents_exist_and_configured(self):
        """Verify all 9 required incident scenarios are defined with full metadata."""
        incidents = self.manager.get_all_incidents()
        self.assertEqual(len(incidents), 9)

        expected_ids = [f"INC-00{i}" for i in range(1, 10)]
        for iid in expected_ids:
            inc = self.manager.get_incident(iid)
            self.assertIsNotNone(inc)
            self.assertTrue(len(inc.title) > 0)
            self.assertIn(
                inc.category,
                ["CONFIGURATION", "VLAN", "ROUTING", "SERVICE", "DNS", "CONNECTIVITY"],
            )
            self.assertIn(inc.severity, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertTrue(len(inc.symptoms) >= 1)
            self.assertTrue(len(inc.expected_impact) > 0)
            self.assertTrue(len(inc.technical_cause) > 0)
            self.assertEqual(inc.status, "INACTIVE")
            self.assertFalse(inc.is_active)

    def test_incident_1_wrong_default_gateway(self):
        """1. Wrong Default Gateway on PC-IT-01."""
        host = self.network.find_host_by_hostname("PC-IT-01")
        self.assertEqual(host.default_gateway, "192.168.10.1")

        # Activate incident
        self.assertTrue(self.manager.activate_incident("INC-001"))
        self.assertEqual(host.default_gateway, "192.168.10.254")

        # Routing to another VLAN fails due to invalid gateway
        self.assertFalse(
            can_route(
                "192.168.10.10",
                "192.168.30.10",
                network=self.network,
                routing_table=self.routing_table,
            )
        )

        # Deactivate incident
        self.assertTrue(self.manager.deactivate_incident("INC-001"))
        self.assertEqual(host.default_gateway, "192.168.10.1")
        self.assertTrue(
            can_route(
                "192.168.10.10",
                "192.168.30.10",
                network=self.network,
                routing_table=self.routing_table,
            )
        )

    def test_incident_2_wrong_subnet_mask(self):
        """2. Wrong Subnet Mask on PC-HR-01."""
        host = self.network.find_host_by_hostname("PC-HR-01")
        self.assertEqual(host.subnet_mask, "255.255.255.0")
        self.assertEqual(host.prefix_length, 24)

        self.assertTrue(self.manager.activate_incident("INC-002"))
        self.assertEqual(host.subnet_mask, "255.255.0.0")
        self.assertEqual(host.prefix_length, 16)

        self.assertTrue(self.manager.deactivate_incident("INC-002"))
        self.assertEqual(host.subnet_mask, "255.255.255.0")
        self.assertEqual(host.prefix_length, 24)

    def test_incident_3_wrong_vlan(self):
        """3. Wrong VLAN on PC-IT-02."""
        host = self.network.find_host_by_hostname("PC-IT-02")
        self.assertEqual(host.vlan_id, 10)

        self.assertTrue(self.manager.activate_incident("INC-003"))
        self.assertEqual(host.vlan_id, 20)

        # Mismatch between IP subnet and VLAN causes routing to fail
        self.assertFalse(
            can_route(
                "192.168.10.11",
                "192.168.30.10",
                network=self.network,
                routing_table=self.routing_table,
            )
        )

        self.assertTrue(self.manager.deactivate_incident("INC-003"))
        self.assertEqual(host.vlan_id, 10)

    def test_incident_4_missing_route(self):
        """4. Missing Route to Servers (192.168.30.0/24)."""
        self.assertTrue(
            any(
                r.destination_network == "192.168.30.0/24"
                for r in self.routing_table
            )
        )

        self.assertTrue(self.manager.activate_incident("INC-004"))
        self.assertFalse(
            any(
                r.destination_network == "192.168.30.0/24"
                for r in self.routing_table
            )
        )
        # Servers unreachable
        self.assertFalse(
            can_route(
                "192.168.10.10",
                "192.168.30.10",
                network=self.network,
                routing_table=self.routing_table,
            )
        )

        self.assertTrue(self.manager.deactivate_incident("INC-004"))
        self.assertTrue(
            any(
                r.destination_network == "192.168.30.0/24"
                for r in self.routing_table
            )
        )

    def test_incident_5_dhcp_service_failure(self):
        """5. DHCP Service Failure."""
        self.assertTrue(self.dhcp.is_available())

        self.assertTrue(self.manager.activate_incident("INC-005"))
        self.assertFalse(self.dhcp.is_available())
        response = self.dhcp.request_ip("PC-NEW", 10)
        self.assertFalse(response.success)
        self.assertEqual(response.status, "SERVICE_DOWN")

        self.assertTrue(self.manager.deactivate_incident("INC-005"))
        self.assertTrue(self.dhcp.is_available())

    def test_incident_6_dns_service_failure(self):
        """6. DNS Service Failure."""
        self.assertTrue(self.dns.is_available())

        self.assertTrue(self.manager.activate_incident("INC-006"))
        self.assertFalse(self.dns.is_available())
        resp = self.dns.resolve("SRV-01")
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, "SERVICE_DOWN")

        self.assertTrue(self.manager.deactivate_incident("INC-006"))
        self.assertTrue(self.dns.is_available())

    def test_incident_7_duplicate_ip(self):
        """7. Duplicate IP Address on PC-HR-02."""
        hr2 = self.network.find_host_by_hostname("PC-HR-02")
        self.assertEqual(hr2.ip_address, "192.168.20.11")

        self.assertTrue(self.manager.activate_incident("INC-007"))
        self.assertEqual(hr2.ip_address, "192.168.20.10")

        self.assertTrue(self.manager.deactivate_incident("INC-007"))
        self.assertEqual(hr2.ip_address, "192.168.20.11")

    def test_incident_8_incorrect_dns_record(self):
        """8. Incorrect DNS Record for SRV-01."""
        self.assertEqual(self.dns.resolve("SRV-01").ip_address, "192.168.30.10")

        self.assertTrue(self.manager.activate_incident("INC-008"))
        self.assertEqual(self.dns.resolve("SRV-01").ip_address, "192.168.30.99")

        self.assertTrue(self.manager.deactivate_incident("INC-008"))
        self.assertEqual(self.dns.resolve("SRV-01").ip_address, "192.168.30.10")

    def test_incident_9_guest_vlan_link_down(self):
        """9. Guest VLAN Link Down."""
        self.assertTrue(
            any(
                r.destination_network == "192.168.40.0/24"
                for r in self.routing_table
            )
        )

        self.assertTrue(self.manager.activate_incident("INC-009"))
        self.assertFalse(
            any(
                r.destination_network == "192.168.40.0/24"
                for r in self.routing_table
            )
        )

        self.assertTrue(self.manager.deactivate_incident("INC-009"))
        self.assertTrue(
            any(
                r.destination_network == "192.168.40.0/24"
                for r in self.routing_table
            )
        )

    def test_reset_all_incidents(self):
        """Verify reset_all_incidents deactivates all active incidents."""
        self.manager.activate_incident("INC-001")
        self.manager.activate_incident("INC-005")
        self.assertEqual(len(self.manager.get_active_incidents()), 2)

        self.manager.reset_all_incidents()
        self.assertEqual(len(self.manager.get_active_incidents()), 0)

        host = self.network.find_host_by_hostname("PC-IT-01")
        self.assertEqual(host.default_gateway, "192.168.10.1")
        self.assertTrue(self.dhcp.is_available())


if __name__ == "__main__":
    unittest.main()
