"""Network model module.

Defines the simulated enterprise network data model, including network devices,
VLANs, and hosts, along with helper functions for querying and validating
network entities.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


@dataclass
class NetworkDevice:
    """Represents a physical or virtual network infrastructure device."""

    name: str
    device_type: str  # e.g., "router", "switch"
    description: str = ""
    management_ip: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert network device attributes to a dictionary."""
        return {
            "name": self.name,
            "device_type": self.device_type,
            "description": self.description,
            "management_ip": self.management_ip,
        }


@dataclass
class VLAN:
    """Represents a Virtual Local Area Network (VLAN)."""

    vlan_id: int
    name: str
    network: str
    gateway: str
    netmask: str = "255.255.255.0"
    prefix_length: int = 24
    description: str = ""

    def contains_ip(self, ip: str) -> bool:
        """Check whether an IP address belongs to this VLAN's network."""
        try:
            target_ip = ipaddress.ip_address(ip.strip())
            net = ipaddress.ip_network(self.network, strict=False)
            return target_ip in net
        except ValueError:
            return False

    def to_dict(self) -> dict:
        """Convert VLAN attributes to a dictionary."""
        return {
            "vlan_id": self.vlan_id,
            "name": self.name,
            "network": self.network,
            "gateway": self.gateway,
            "netmask": self.netmask,
            "prefix_length": self.prefix_length,
            "description": self.description,
        }


@dataclass
class Host:
    """Represents an endpoint host in the simulated network."""

    hostname: str
    ip_address: str
    subnet_mask: str
    default_gateway: str
    vlan_id: int
    device_type: str = "workstation"  # e.g., "workstation", "server"
    prefix_length: int = 24
    mac_address: str = ""

    @property
    def vlan(self) -> int:
        """Convenience property alias for vlan_id."""
        return self.vlan_id

    def to_dict(self) -> dict:
        """Convert host attributes to a dictionary."""
        return {
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "subnet_mask": self.subnet_mask,
            "prefix_length": self.prefix_length,
            "default_gateway": self.default_gateway,
            "vlan_id": self.vlan_id,
            "device_type": self.device_type,
            "mac_address": self.mac_address,
        }


@dataclass
class NetworkModel:
    """Encapsulates the complete simulated network topology and state."""

    devices: List[NetworkDevice] = field(default_factory=list)
    vlans: Dict[int, VLAN] = field(default_factory=dict)
    hosts: Dict[str, Host] = field(default_factory=dict)

    def get_vlans(self) -> List[VLAN]:
        """Return all configured VLANs ordered by VLAN ID."""
        return sorted(self.vlans.values(), key=lambda v: v.vlan_id)

    def get_hosts(self) -> List[Host]:
        """Return all configured hosts ordered by hostname."""
        return sorted(self.hosts.values(), key=lambda h: h.hostname)

    def get_devices(self) -> List[NetworkDevice]:
        """Return all network devices."""
        return list(self.devices)

    def find_vlan_by_id(self, vlan_id: int) -> Optional[VLAN]:
        """Look up a VLAN by its ID."""
        return self.vlans.get(vlan_id)

    def find_host_by_hostname(self, hostname: str) -> Optional[Host]:
        """Find a host by its hostname (case-insensitive)."""
        normalized = hostname.strip().upper()
        for name, host in self.hosts.items():
            if name.upper() == normalized:
                return host
        return None

    def find_host_by_ip(self, ip_address: str) -> Optional[Host]:
        """Find a host by its IP address."""
        cleaned_ip = ip_address.strip()
        for host in self.hosts.values():
            if host.ip_address.strip() == cleaned_ip:
                return host
        return None

    def find_vlan_of_host(self, host: Union[Host, str]) -> Optional[VLAN]:
        """Find the VLAN corresponding to a host instance or hostname."""
        if isinstance(host, str):
            target_host = self.find_host_by_hostname(host)
            if not target_host:
                return None
            return self.find_vlan_by_id(target_host.vlan_id)
        return self.find_vlan_by_id(host.vlan_id)

    def validate_ip_in_vlan(
        self, ip_address: str, vlan: Union[VLAN, int]
    ) -> bool:
        """Validate whether an IP address belongs to the specified VLAN's network."""
        target_vlan: Optional[VLAN]
        if isinstance(vlan, int):
            target_vlan = self.find_vlan_by_id(vlan)
        else:
            target_vlan = vlan

        if not target_vlan:
            return False

        return target_vlan.contains_ip(ip_address)


def build_enterprise_network() -> NetworkModel:
    """Build and return the simulated enterprise network model.

    Topology:
        Internet
           |
        Router
           |
        Core Switch
           |
           +-- VLAN 10: IT (192.168.10.0/24, GW: 192.168.10.1)
           |     +-- PC-IT-01 (192.168.10.10)
           |     +-- PC-IT-02 (192.168.10.11)
           |
           +-- VLAN 20: HR (192.168.20.0/24, GW: 192.168.20.1)
           |     +-- PC-HR-01 (192.168.20.10)
           |     +-- PC-HR-02 (192.168.20.11)
           |
           +-- VLAN 30: Servers (192.168.30.0/24, GW: 192.168.30.1)
           |     +-- SRV-01 (192.168.30.10)
           |     +-- SRV-02 (192.168.30.11)
           |
           +-- VLAN 40: Guest (192.168.40.0/24, GW: 192.168.40.1)
                 +-- PC-GUEST-01 (192.168.40.10)
                 +-- PC-GUEST-02 (192.168.40.11)
    """
    devices = [
        NetworkDevice(
            name="Router",
            device_type="router",
            description="Default Gateway and boundary router connecting VLANs and WAN/Internet",
        ),
        NetworkDevice(
            name="Core Switch",
            device_type="switch",
            description="Core distribution/access switch trunking VLANs 10, 20, 30, and 40",
        ),
    ]

    vlans = {
        10: VLAN(
            vlan_id=10,
            name="IT",
            network="192.168.10.0/24",
            gateway="192.168.10.1",
            netmask="255.255.255.0",
            prefix_length=24,
            description="IT department workstations and management hosts",
        ),
        20: VLAN(
            vlan_id=20,
            name="HR",
            network="192.168.20.0/24",
            gateway="192.168.20.1",
            netmask="255.255.255.0",
            prefix_length=24,
            description="Human Resources department workstations",
        ),
        30: VLAN(
            vlan_id=30,
            name="Servers",
            network="192.168.30.0/24",
            gateway="192.168.30.1",
            netmask="255.255.255.0",
            prefix_length=24,
            description="Internal server farm hosting corporate services",
        ),
        40: VLAN(
            vlan_id=40,
            name="Guest",
            network="192.168.40.0/24",
            gateway="192.168.40.1",
            netmask="255.255.255.0",
            prefix_length=24,
            description="Isolated guest and visitor workstation network",
        ),
    }

    hosts = {
        "PC-IT-01": Host(
            hostname="PC-IT-01",
            ip_address="192.168.10.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.10.1",
            vlan_id=10,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:10:01:01",
        ),
        "PC-IT-02": Host(
            hostname="PC-IT-02",
            ip_address="192.168.10.11",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.10.1",
            vlan_id=10,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:10:01:02",
        ),
        "PC-HR-01": Host(
            hostname="PC-HR-01",
            ip_address="192.168.20.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.20.1",
            vlan_id=20,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:20:01:01",
        ),
        "PC-HR-02": Host(
            hostname="PC-HR-02",
            ip_address="192.168.20.11",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.20.1",
            vlan_id=20,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:20:01:02",
        ),
        "SRV-01": Host(
            hostname="SRV-01",
            ip_address="192.168.30.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.30.1",
            vlan_id=30,
            device_type="server",
            prefix_length=24,
            mac_address="00:50:56:30:01:01",
        ),
        "SRV-02": Host(
            hostname="SRV-02",
            ip_address="192.168.30.11",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.30.1",
            vlan_id=30,
            device_type="server",
            prefix_length=24,
            mac_address="00:50:56:30:01:02",
        ),
        "PC-GUEST-01": Host(
            hostname="PC-GUEST-01",
            ip_address="192.168.40.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.40.1",
            vlan_id=40,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:40:01:01",
        ),
        "PC-GUEST-02": Host(
            hostname="PC-GUEST-02",
            ip_address="192.168.40.11",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.40.1",
            vlan_id=40,
            device_type="workstation",
            prefix_length=24,
            mac_address="00:50:56:40:01:02",
        ),
    }

    return NetworkModel(devices=devices, vlans=vlans, hosts=hosts)


# Module-level default simulated network instance
DEFAULT_NETWORK: NetworkModel = build_enterprise_network()


def get_default_network() -> NetworkModel:
    """Return the global default simulated enterprise network."""
    return DEFAULT_NETWORK


# ---------------------------------------------------------------------------
# Module-level helper functions operating on default or custom network models
# ---------------------------------------------------------------------------


def get_all_vlans(network: Optional[NetworkModel] = None) -> List[VLAN]:
    """Return all VLANs in the network model."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.get_vlans()


def get_all_hosts(network: Optional[NetworkModel] = None) -> List[Host]:
    """Return all hosts in the network model."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.get_hosts()


def find_host_by_hostname(
    hostname: str, network: Optional[NetworkModel] = None
) -> Optional[Host]:
    """Find a host by its hostname (case-insensitive)."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.find_host_by_hostname(hostname)


def find_host_by_ip(
    ip_address: str, network: Optional[NetworkModel] = None
) -> Optional[Host]:
    """Find a host by its IP address."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.find_host_by_ip(ip_address)


def find_vlan_of_host(
    host: Union[Host, str], network: Optional[NetworkModel] = None
) -> Optional[VLAN]:
    """Find the VLAN of a given host instance or hostname."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.find_vlan_of_host(host)


def validate_ip_in_vlan(
    ip_address: str,
    vlan: Union[VLAN, int],
    network: Optional[NetworkModel] = None,
) -> bool:
    """Validate whether an IP address belongs to the configured VLAN network."""
    target_net = network if network is not None else DEFAULT_NETWORK
    return target_net.validate_ip_in_vlan(ip_address, vlan)


# Aliases for convenience
get_vlans = get_all_vlans
get_hosts = get_all_hosts
find_vlan_for_host = find_vlan_of_host
