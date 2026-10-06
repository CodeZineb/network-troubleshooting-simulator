"""Subnetting module.

Responsible for IPv4 address and subnet calculations, validations, and
network detail extraction using Python's standard ipaddress library.
"""

from __future__ import annotations

import ipaddress
from typing import Any, Dict


def _validate_and_parse_ip(ip_address: str) -> ipaddress.IPv4Address:
    """Validate and parse an IPv4 address string.

    Raises:
        ValueError: If the address is invalid, empty, or not an IPv4 address.
    """
    if not isinstance(ip_address, str) or not ip_address.strip():
        raise ValueError(f"Invalid IPv4 address: {ip_address!r}")

    cleaned = ip_address.strip()
    try:
        return ipaddress.IPv4Address(cleaned)
    except (ipaddress.AddressValueError, ValueError) as err:
        raise ValueError(f"Invalid IPv4 address '{ip_address}': {err}") from err


def _validate_and_parse_network(cidr: str) -> ipaddress.IPv4Network:
    """Validate and parse an IPv4 network CIDR string.

    Raises:
        ValueError: If the CIDR string is invalid, missing prefix length, or not IPv4.
    """
    if not isinstance(cidr, str) or not cidr.strip():
        raise ValueError(f"Invalid CIDR notation: {cidr!r}")

    cleaned = cidr.strip()
    if "/" not in cleaned:
        raise ValueError(
            f"Invalid CIDR notation '{cidr}': missing prefix length (e.g., '/24')"
        )

    try:
        return ipaddress.IPv4Network(cleaned, strict=False)
    except (
        ipaddress.AddressValueError,
        ipaddress.NetmaskValueError,
        ValueError,
    ) as err:
        raise ValueError(f"Invalid IPv4 CIDR notation '{cidr}': {err}") from err


def get_network_info(cidr: str) -> Dict[str, Any]:
    """Calculate and return network parameters for a given IPv4 CIDR prefix.

    Args:
        cidr: Network in CIDR notation (e.g. '192.168.10.0/24').

    Returns:
        Dictionary containing:
            - network_address: Network base address
            - broadcast_address: Broadcast address
            - subnet_mask: Subnet mask string
            - prefix_length: Prefix length integer
            - first_usable_host: First usable host IP address string
            - last_usable_host: Last usable host IP address string
            - number_of_usable_hosts: Total usable host addresses count
    """
    net = _validate_and_parse_network(cidr)
    prefix_length = net.prefixlen
    num_addresses = net.num_addresses

    if prefix_length <= 30:
        first_usable = str(net.network_address + 1)
        last_usable = str(net.broadcast_address - 1)
        usable_hosts = num_addresses - 2
    elif prefix_length == 31:
        # RFC 3021: Point-to-point links with 31-bit prefixes
        first_usable = str(net.network_address)
        last_usable = str(net.broadcast_address)
        usable_hosts = 2
    else:  # /32 host route
        first_usable = str(net.network_address)
        last_usable = str(net.network_address)
        usable_hosts = 1

    return {
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
        "subnet_mask": str(net.netmask),
        "prefix_length": prefix_length,
        "first_usable_host": first_usable,
        "last_usable_host": last_usable,
        "number_of_usable_hosts": usable_hosts,
        "num_usable_hosts": usable_hosts,
    }


def get_ip_network(ip_address: str, cidr: str) -> bool:
    """Determine whether an IP address belongs to the specified CIDR network.

    Args:
        ip_address: IPv4 address string.
        cidr: Network in CIDR notation.

    Returns:
        True if the IP address is within the network, False otherwise.
    """
    ip = _validate_and_parse_ip(ip_address)
    net = _validate_and_parse_network(cidr)
    return ip in net


def get_ip_details(ip_address: str, cidr: str) -> Dict[str, Any]:
    """Return detailed status of an IP address relative to a given CIDR network.

    Args:
        ip_address: IPv4 address string.
        cidr: Network in CIDR notation.

    Returns:
        Dictionary containing:
            - ip_address: IP address string
            - network_address: Network base address string
            - broadcast_address: Broadcast address string
            - subnet_mask: Subnet mask string
            - prefix_length: Prefix length integer
            - is_network_address: True if the IP matches network address
            - is_broadcast_address: True if the IP matches broadcast address
            - is_usable_host: True if usable as a host within the network
            - belongs_to_network: True if the IP is inside the network
    """
    ip = _validate_and_parse_ip(ip_address)
    net = _validate_and_parse_network(cidr)

    in_net = ip in net
    is_network = ip == net.network_address
    is_broadcast = ip == net.broadcast_address

    if in_net:
        if net.prefixlen <= 30:
            is_usable = not is_network and not is_broadcast
        elif net.prefixlen == 31:
            is_usable = True
        else:  # /32
            is_usable = True
    else:
        is_usable = False

    return {
        "ip_address": str(ip),
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
        "subnet_mask": str(net.netmask),
        "prefix_length": net.prefixlen,
        "is_network_address": is_network,
        "is_broadcast_address": is_broadcast,
        "is_usable_host": is_usable,
        "is_usable": is_usable,
        "belongs_to_network": in_net,
    }


def calculate_subnet(cidr: str) -> Dict[str, Any]:
    """Convenient wrapper around get_network_info to calculate subnet parameters."""
    return get_network_info(cidr)


# Aliases for convenience
is_ip_in_network = get_ip_network
