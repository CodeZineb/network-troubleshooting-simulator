"""Tests for IPv4 subnetting and address calculation functions."""

import unittest

from src.subnetting import (
    calculate_subnet,
    get_ip_details,
    get_ip_network,
    get_network_info,
    is_ip_in_network,
)


class TestSubnetting(unittest.TestCase):
    """Test suite validating IPv4 calculations, boundary conditions, and error handling."""

    def test_network_info_192_168_10_0_24(self):
        info = get_network_info("192.168.10.0/24")
        self.assertEqual(info["network_address"], "192.168.10.0")
        self.assertEqual(info["broadcast_address"], "192.168.10.255")
        self.assertEqual(info["subnet_mask"], "255.255.255.0")
        self.assertEqual(info["prefix_length"], 24)
        self.assertEqual(info["first_usable_host"], "192.168.10.1")
        self.assertEqual(info["last_usable_host"], "192.168.10.254")
        self.assertEqual(info["number_of_usable_hosts"], 254)

    def test_network_info_192_168_20_0_24(self):
        info = get_network_info("192.168.20.0/24")
        self.assertEqual(info["network_address"], "192.168.20.0")
        self.assertEqual(info["broadcast_address"], "192.168.20.255")
        self.assertEqual(info["subnet_mask"], "255.255.255.0")
        self.assertEqual(info["prefix_length"], 24)
        self.assertEqual(info["first_usable_host"], "192.168.20.1")
        self.assertEqual(info["last_usable_host"], "192.168.20.254")
        self.assertEqual(info["number_of_usable_hosts"], 254)

    def test_network_info_slash_30(self):
        info = get_network_info("10.0.0.0/30")
        self.assertEqual(info["network_address"], "10.0.0.0")
        self.assertEqual(info["broadcast_address"], "10.0.0.3")
        self.assertEqual(info["subnet_mask"], "255.255.255.252")
        self.assertEqual(info["prefix_length"], 30)
        self.assertEqual(info["first_usable_host"], "10.0.0.1")
        self.assertEqual(info["last_usable_host"], "10.0.0.2")
        self.assertEqual(info["number_of_usable_hosts"], 2)

    def test_network_info_slash_31(self):
        info = get_network_info("10.0.0.0/31")
        self.assertEqual(info["network_address"], "10.0.0.0")
        self.assertEqual(info["broadcast_address"], "10.0.0.1")
        self.assertEqual(info["subnet_mask"], "255.255.255.254")
        self.assertEqual(info["prefix_length"], 31)
        self.assertEqual(info["first_usable_host"], "10.0.0.0")
        self.assertEqual(info["last_usable_host"], "10.0.0.1")
        self.assertEqual(info["number_of_usable_hosts"], 2)

    def test_ip_belongs_to_network(self):
        # Belongs to 192.168.10.0/24
        self.assertTrue(get_ip_network("192.168.10.1", "192.168.10.0/24"))
        self.assertTrue(get_ip_network("192.168.10.50", "192.168.10.0/24"))
        self.assertTrue(is_ip_in_network("192.168.10.254", "192.168.10.0/24"))

    def test_ip_does_not_belong_to_network(self):
        # Does not belong to 192.168.10.0/24
        self.assertFalse(get_ip_network("192.168.20.10", "192.168.10.0/24"))
        self.assertFalse(get_ip_network("10.0.0.1", "192.168.10.0/24"))
        self.assertFalse(is_ip_in_network("172.16.0.1", "192.168.10.0/24"))

    def test_network_address_detection(self):
        details = get_ip_details("192.168.10.0", "192.168.10.0/24")
        self.assertTrue(details["is_network_address"])
        self.assertFalse(details["is_broadcast_address"])
        self.assertFalse(details["is_usable_host"])
        self.assertTrue(details["belongs_to_network"])

    def test_broadcast_address_detection(self):
        details = get_ip_details("192.168.10.255", "192.168.10.0/24")
        self.assertFalse(details["is_network_address"])
        self.assertTrue(details["is_broadcast_address"])
        self.assertFalse(details["is_usable_host"])
        self.assertTrue(details["belongs_to_network"])

    def test_usable_host_detection(self):
        details = get_ip_details("192.168.10.15", "192.168.10.0/24")
        self.assertFalse(details["is_network_address"])
        self.assertFalse(details["is_broadcast_address"])
        self.assertTrue(details["is_usable_host"])
        self.assertTrue(details["belongs_to_network"])

    def test_ip_details_outside_network(self):
        details = get_ip_details("10.0.0.5", "192.168.10.0/24")
        self.assertFalse(details["is_network_address"])
        self.assertFalse(details["is_broadcast_address"])
        self.assertFalse(details["is_usable_host"])
        self.assertFalse(details["belongs_to_network"])

    def test_calculate_subnet_wrapper(self):
        direct = get_network_info("192.168.30.0/24")
        wrapped = calculate_subnet("192.168.30.0/24")
        self.assertEqual(direct, wrapped)

    def test_invalid_ip_and_cidr_inputs(self):
        # Invalid CIDR inputs
        with self.assertRaises(ValueError):
            get_network_info("invalid_cidr")

        with self.assertRaises(ValueError):
            get_network_info("192.168.1.1/33")

        with self.assertRaises(ValueError):
            get_network_info("192.168.1.1")  # missing prefix length

        with self.assertRaises(ValueError):
            get_network_info("2001:db8::/32")  # IPv6 not allowed

        with self.assertRaises(ValueError):
            get_network_info("")

        # Invalid IP addresses
        with self.assertRaises(ValueError):
            get_ip_network("invalid_ip", "192.168.10.0/24")

        with self.assertRaises(ValueError):
            get_ip_network("999.999.999.999", "192.168.10.0/24")

        with self.assertRaises(ValueError):
            get_ip_details("invalid_ip", "192.168.10.0/24")

        with self.assertRaises(ValueError):
            calculate_subnet("999.999.999.0/24")


if __name__ == "__main__":
    unittest.main()
