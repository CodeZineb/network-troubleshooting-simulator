"""Tests for simulated enterprise routing functionality."""

import unittest

from src.routing import (
    Route,
    RouteSimulationResult,
    can_route,
    find_route,
    get_routing_table,
    simulate_route,
)


class TestRouting(unittest.TestCase):
    """Test suite validating simulated routing table, path simulation, and reachability."""

    def test_routing_table_contains_all_four_vlans(self):
        """1. Routing table contains all four connected VLAN networks."""
        table = get_routing_table()
        self.assertEqual(len(table), 4)

        destinations = {route.destination_network for route in table}
        expected_destinations = {
            "192.168.10.0/24",
            "192.168.20.0/24",
            "192.168.30.0/24",
            "192.168.40.0/24",
        }
        self.assertEqual(destinations, expected_destinations)

        interfaces = {route.outgoing_interface for route in table}
        self.assertEqual(interfaces, {"VLAN10", "VLAN20", "VLAN30", "VLAN40"})

        for route in table:
            self.assertEqual(route.next_hop, "connected")
            self.assertEqual(route.route_type, "connected")

    def test_it_to_it_host_is_reachable(self):
        """2. IT -> IT host is reachable."""
        src = "192.168.10.10"  # PC-IT-01
        dst = "192.168.10.11"  # PC-IT-02

        self.assertTrue(can_route(src, dst))
        result = simulate_route(src, dst)

        self.assertTrue(result.is_reachable)
        self.assertEqual(result.status, "LOCAL")
        self.assertIn("PC-IT-01", result.path)
        self.assertIn("PC-IT-02", result.path)

    def test_it_to_servers_is_routable(self):
        """3. IT -> Servers is routable."""
        src = "192.168.10.10"  # PC-IT-01
        dst = "192.168.30.10"  # SRV-01

        self.assertTrue(can_route(src, dst))
        result = simulate_route(src, dst)

        self.assertEqual(result.status, "ROUTABLE")
        self.assertTrue(result.is_routable)
        self.assertTrue(result.is_reachable)
        self.assertTrue(result.requires_router)

        expected_path = [
            "PC-IT-01",
            "Gateway 192.168.10.1",
            "Router",
            "Gateway 192.168.30.1",
            "SRV-01",
        ]
        self.assertEqual(result.path, expected_path)

    def test_hr_to_it_is_routable(self):
        """4. HR -> IT is routable."""
        src = "192.168.20.10"  # PC-HR-01
        dst = "192.168.10.10"  # PC-IT-01

        self.assertTrue(can_route(src, dst))
        result = simulate_route(src, dst)

        self.assertEqual(result.status, "ROUTABLE")
        self.assertTrue(result.is_routable)
        self.assertTrue(result.requires_router)

        expected_path = [
            "PC-HR-01",
            "Gateway 192.168.20.1",
            "Router",
            "Gateway 192.168.10.1",
            "PC-IT-01",
        ]
        self.assertEqual(result.path, expected_path)

    def test_guest_to_servers_is_routable(self):
        """5. Guest -> Servers is routable at the routing layer."""
        src = "192.168.40.10"  # PC-GUEST-01
        dst = "192.168.30.10"  # SRV-01

        self.assertTrue(can_route(src, dst))
        result = simulate_route(src, dst)

        self.assertEqual(result.status, "ROUTABLE")
        self.assertTrue(result.is_routable)
        self.assertTrue(result.requires_router)

        expected_path = [
            "PC-GUEST-01",
            "Gateway 192.168.40.1",
            "Router",
            "Gateway 192.168.30.1",
            "SRV-01",
        ]
        self.assertEqual(result.path, expected_path)

    def test_unknown_destination_returns_no_route(self):
        """6. Unknown destination network returns NO_ROUTE."""
        src = "192.168.10.10"
        dst = "8.8.8.8"

        self.assertFalse(can_route(src, dst))
        result = simulate_route(src, dst)

        self.assertEqual(result.status, "NO_ROUTE")
        self.assertFalse(result.is_routable)
        self.assertFalse(result.is_reachable)
        self.assertEqual(
            result.reason, "No route exists for destination network."
        )
        self.assertEqual(result.path, [])

    def test_same_vlan_does_not_require_inter_vlan_routing(self):
        """7. Same-VLAN traffic does not incorrectly require inter-VLAN routing."""
        src = "192.168.20.10"  # PC-HR-01
        dst = "192.168.20.11"  # PC-HR-02

        result = simulate_route(src, dst)

        self.assertFalse(result.requires_router)
        self.assertNotIn("Router", result.path)
        self.assertNotIn("Gateway 192.168.20.1", result.path)
        self.assertEqual(result.path, ["PC-HR-01", "Core Switch", "PC-HR-02"])

    def test_find_route_longest_prefix_match(self):
        route = find_route("192.168.10.50")
        self.assertIsNotNone(route)
        self.assertEqual(route.destination_network, "192.168.10.0/24")
        self.assertEqual(route.outgoing_interface, "VLAN10")

        self.assertIsNone(find_route("10.100.1.1"))

    def test_invalid_ips_raise_value_error(self):
        with self.assertRaises(ValueError):
            can_route("invalid_ip", "192.168.10.10")

        with self.assertRaises(ValueError):
            simulate_route("192.168.10.10", "999.999.999.999")

        with self.assertRaises(ValueError):
            find_route("not_an_ip")

    def test_result_string_representation(self):
        result = simulate_route("192.168.10.10", "192.168.30.10")
        output = str(result)
        self.assertIn("Source: 192.168.10.10", output)
        self.assertIn("Destination: 192.168.30.10", output)
        self.assertIn("Status: ROUTABLE", output)
        self.assertIn("→ Router", output)


if __name__ == "__main__":
    unittest.main()
