"""Incidents module.

Defines realistic network failure scenarios for the simulated enterprise network,
including configuration mistakes, service outages, routing failures, and link drops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .network_model import NetworkModel, get_default_network
from .routing import Route, get_routing_table
from .services import (
    DHCPServer,
    DNSServer,
    get_default_dhcp_server,
    get_default_dns_server,
)


@dataclass
class Incident:
    """Represents a simulated network incident / failure scenario."""

    incident_id: str
    title: str
    category: str
    affected_device: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    symptoms: List[str]
    expected_impact: str
    technical_cause: Dict[str, Any]
    status: str = "INACTIVE"  # "INACTIVE", "ACTIVE", "RESOLVED"
    description: str = ""

    @property
    def id(self) -> str:
        """Alias for incident_id."""
        return self.incident_id

    @property
    def affected_host(self) -> str:
        """Alias for affected_device."""
        return self.affected_device

    @property
    def is_active(self) -> bool:
        """True if incident is currently active."""
        return self.status == "ACTIVE"

    def to_dict(self) -> dict:
        """Convert incident to dictionary representation."""
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "category": self.category,
            "affected_device": self.affected_device,
            "affected_host": self.affected_host,
            "severity": self.severity,
            "symptoms": list(self.symptoms),
            "expected_impact": self.expected_impact,
            "technical_cause": dict(self.technical_cause),
            "status": self.status,
            "description": self.description,
            "is_active": self.is_active,
        }


def _build_default_incidents() -> Dict[str, Incident]:
    """Instantiate the 9 canonical simulated network incident scenarios."""
    scenarios = [
        Incident(
            incident_id="INC-001",
            title="Wrong Default Gateway",
            category="CONFIGURATION",
            affected_device="PC-IT-01",
            severity="HIGH",
            symptoms=[
                "Local configuration appears valid",
                "Communication outside the local network fails",
                "Ping to another VLAN fails",
            ],
            expected_impact="PC-IT-01 cannot forward packets outside local VLAN 10.",
            technical_cause={
                "configured_gateway": "192.168.10.254",
                "expected_gateway": "192.168.10.1",
            },
            description="PC-IT-01 is configured with incorrect default gateway 192.168.10.254 instead of 192.168.10.1.",
        ),
        Incident(
            incident_id="INC-002",
            title="Wrong Subnet Mask",
            category="CONFIGURATION",
            affected_device="PC-HR-01",
            severity="MEDIUM",
            symptoms=[
                "Incorrect network membership",
                "Unexpected connectivity behavior",
                "Communication problems with other hosts",
            ],
            expected_impact="PC-HR-01 treats all 192.168.0.0/16 addresses as local, failing to route to default gateway.",
            technical_cause={
                "configured_mask": "255.255.0.0",
                "expected_mask": "255.255.255.0",
            },
            description="PC-HR-01 is configured with subnet mask 255.255.0.0 instead of 255.255.255.0.",
        ),
        Incident(
            incident_id="INC-003",
            title="Wrong VLAN",
            category="VLAN",
            affected_device="PC-IT-02",
            severity="HIGH",
            symptoms=[
                "Incorrect network addressing",
                "Connectivity problems",
                "Possible inability to reach intended resources",
            ],
            expected_impact="PC-IT-02 is connected to VLAN 20 switch port while maintaining 192.168.10.0/24 addressing.",
            technical_cause={
                "actual_vlan": 20,
                "expected_vlan": 10,
            },
            description="PC-IT-02 assigned to VLAN 20 instead of VLAN 10, resulting in broadcast domain mismatch.",
        ),
        Incident(
            incident_id="INC-004",
            title="Missing Route to Servers",
            category="ROUTING",
            affected_device="Router",
            severity="CRITICAL",
            symptoms=[
                "Traffic to Servers VLAN fails with NO_ROUTE",
                "Ping and traceroute to SRV-01 and SRV-02 fail",
                "Other VLANs remain routable",
            ],
            expected_impact="Entire Servers farm (192.168.30.0/24) is unreachable from IT, HR, and Guest VLANs.",
            technical_cause={
                "missing_network": "192.168.30.0/24",
            },
            description="Router routing table is missing the route entry for 192.168.30.0/24.",
        ),
        Incident(
            incident_id="INC-005",
            title="DHCP Service Failure",
            category="SERVICE",
            affected_device="DHCPServer",
            severity="HIGH",
            symptoms=[
                "Dynamic clients fail to lease IP addresses",
                "DHCP requests return SERVICE_DOWN",
                "Existing static configurations remain operational",
            ],
            expected_impact="Clients requesting dynamic IP allocations receive no lease.",
            technical_cause={
                "service_status": "DOWN",
            },
            description="Enterprise DHCP service is down; IP address requests fail.",
        ),
        Incident(
            incident_id="INC-006",
            title="DNS Service Failure",
            category="SERVICE",
            affected_device="DNSServer",
            severity="HIGH",
            symptoms=[
                "nslookup queries fail with SERVICE_DOWN",
                "Hostname resolution fails across all VLANs",
                "Direct IP-based communication continues to function",
            ],
            expected_impact="Hostnames cannot be resolved to IP addresses across the organization.",
            technical_cause={
                "service_status": "DOWN",
            },
            description="Enterprise DNS service is down; hostname lookups fail.",
        ),
        Incident(
            incident_id="INC-007",
            title="Duplicate IP Address",
            category="CONFIGURATION",
            affected_device="PC-HR-02",
            severity="HIGH",
            symptoms=[
                "Multiple hosts claim IP 192.168.20.10",
                "ARP table conflict detected on VLAN 20",
                "Intermittent and dropped communication for HR workstations",
            ],
            expected_impact="IP address collision causes traffic misdirection between PC-HR-01 and PC-HR-02.",
            technical_cause={
                "conflicting_ip": "192.168.20.10",
                "expected_ip": "192.168.20.11",
            },
            description="PC-HR-02 mistakenly configured with duplicate IP 192.168.20.10.",
        ),
        Incident(
            incident_id="INC-008",
            title="Incorrect DNS Record",
            category="DNS",
            affected_device="DNSServer",
            severity="MEDIUM",
            symptoms=[
                "nslookup for SRV-01 resolves to wrong IP address (192.168.30.99)",
                "Connections to hostname SRV-01 fail or timeout",
                "Direct IP ping to 192.168.30.10 succeeds",
            ],
            expected_impact="Clients attempting to contact SRV-01 by name are routed to a non-existent IP.",
            technical_cause={
                "hostname": "SRV-01",
                "corrupt_ip": "192.168.30.99",
                "expected_ip": "192.168.30.10",
            },
            description="DNS record for SRV-01 points to invalid address 192.168.30.99.",
        ),
        Incident(
            incident_id="INC-009",
            title="Guest VLAN Link Down",
            category="CONNECTIVITY",
            affected_device="Core Switch",
            severity="MEDIUM",
            symptoms=[
                "Guest workstations cannot communicate with gateway 192.168.40.1",
                "Guest VLAN 40 completely isolated",
                "Routing table entry for VLAN 40 down or removed",
            ],
            expected_impact="All devices in Guest network are disconnected from enterprise network and internet.",
            technical_cause={
                "vlan_id": 40,
                "link_status": "DOWN",
            },
            description="Core switch trunk port or interface for VLAN 40 is down.",
        ),
    ]
    return {inc.incident_id: inc for inc in scenarios}


class IncidentManager:
    """Manages creation, activation, deactivation, and state changes for network incidents."""

    def __init__(
        self,
        network: Optional[NetworkModel] = None,
        routing_table: Optional[List[Route]] = None,
        dhcp_server: Optional[DHCPServer] = None,
        dns_server: Optional[DNSServer] = None,
    ) -> None:
        self.network = network if network is not None else get_default_network()
        self.routing_table = (
            routing_table if routing_table is not None else get_routing_table()
        )
        self.dhcp_server = (
            dhcp_server if dhcp_server is not None else get_default_dhcp_server()
        )
        self.dns_server = (
            dns_server if dns_server is not None else get_default_dns_server()
        )

        self._incidents = _build_default_incidents()
        # Storage to restore clean configurations upon deactivation
        self._saved_states: Dict[str, Any] = {}

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Look up an incident by ID (e.g., 'INC-001')."""
        return self._incidents.get(incident_id.strip().upper())

    def get_all_incidents(self) -> List[Incident]:
        """Return all available incident scenarios."""
        return sorted(self._incidents.values(), key=lambda i: i.incident_id)

    def get_active_incidents(self) -> List[Incident]:
        """Return all currently active incidents."""
        return [i for i in self.get_all_incidents() if i.is_active]

    def activate_incident(self, incident_id: str) -> bool:
        """Activate a specific incident, applying technical misconfigurations to the state."""
        incident = self.get_incident(incident_id)
        if not incident or incident.is_active:
            return False

        iid = incident.incident_id

        if iid == "INC-001":
            # Wrong Default Gateway on PC-IT-01
            host = self.network.find_host_by_hostname("PC-IT-01")
            if host:
                self._saved_states[iid] = host.default_gateway
                host.default_gateway = "192.168.10.254"

        elif iid == "INC-002":
            # Wrong Subnet Mask on PC-HR-01
            host = self.network.find_host_by_hostname("PC-HR-01")
            if host:
                self._saved_states[iid] = (host.subnet_mask, host.prefix_length)
                host.subnet_mask = "255.255.0.0"
                host.prefix_length = 16

        elif iid == "INC-003":
            # Wrong VLAN on PC-IT-02
            host = self.network.find_host_by_hostname("PC-IT-02")
            if host:
                self._saved_states[iid] = host.vlan_id
                host.vlan_id = 20

        elif iid == "INC-004":
            # Missing Route to Servers (192.168.30.0/24)
            target_route = next(
                (
                    r
                    for r in self.routing_table
                    if r.destination_network == "192.168.30.0/24"
                ),
                None,
            )
            if target_route:
                self._saved_states[iid] = target_route
                self.routing_table.remove(target_route)

        elif iid == "INC-005":
            # DHCP Service Failure
            self._saved_states[iid] = self.dhcp_server.status
            self.dhcp_server.set_status("DOWN")

        elif iid == "INC-006":
            # DNS Service Failure
            self._saved_states[iid] = self.dns_server.status
            self.dns_server.set_status("DOWN")

        elif iid == "INC-007":
            # Duplicate IP on PC-HR-02
            host = self.network.find_host_by_hostname("PC-HR-02")
            if host:
                self._saved_states[iid] = host.ip_address
                host.ip_address = "192.168.20.10"

        elif iid == "INC-008":
            # Incorrect DNS record for SRV-01
            records = self.dns_server.get_records()
            self._saved_states[iid] = records.get("SRV-01", "192.168.30.10")
            self.dns_server.add_record("SRV-01", "192.168.30.99")

        elif iid == "INC-009":
            # Guest VLAN Link Down
            target_route = next(
                (
                    r
                    for r in self.routing_table
                    if r.destination_network == "192.168.40.0/24"
                ),
                None,
            )
            if target_route:
                self._saved_states[iid] = target_route
                self.routing_table.remove(target_route)

        incident.status = "ACTIVE"
        return True

    def deactivate_incident(self, incident_id: str) -> bool:
        """Deactivate an incident, restoring previous configuration state."""
        incident = self.get_incident(incident_id)
        if not incident or not incident.is_active:
            return False

        iid = incident.incident_id

        if iid == "INC-001":
            host = self.network.find_host_by_hostname("PC-IT-01")
            if host and iid in self._saved_states:
                host.default_gateway = self._saved_states.pop(iid)

        elif iid == "INC-002":
            host = self.network.find_host_by_hostname("PC-HR-01")
            if host and iid in self._saved_states:
                mask, prefix = self._saved_states.pop(iid)
                host.subnet_mask = mask
                host.prefix_length = prefix

        elif iid == "INC-003":
            host = self.network.find_host_by_hostname("PC-IT-02")
            if host and iid in self._saved_states:
                host.vlan_id = self._saved_states.pop(iid)

        elif iid == "INC-004":
            if iid in self._saved_states:
                route = self._saved_states.pop(iid)
                if route not in self.routing_table:
                    self.routing_table.append(route)

        elif iid == "INC-005":
            if iid in self._saved_states:
                orig = self._saved_states.pop(iid)
                self.dhcp_server.set_status(orig)

        elif iid == "INC-006":
            if iid in self._saved_states:
                orig = self._saved_states.pop(iid)
                self.dns_server.set_status(orig)

        elif iid == "INC-007":
            host = self.network.find_host_by_hostname("PC-HR-02")
            if host and iid in self._saved_states:
                host.ip_address = self._saved_states.pop(iid)

        elif iid == "INC-008":
            if iid in self._saved_states:
                orig_ip = self._saved_states.pop(iid)
                self.dns_server.add_record("SRV-01", orig_ip)

        elif iid == "INC-009":
            if iid in self._saved_states:
                route = self._saved_states.pop(iid)
                if route not in self.routing_table:
                    self.routing_table.append(route)

        incident.status = "INACTIVE"
        return True

    def reset_all_incidents(self) -> None:
        """Deactivate all active incidents and restore original baseline state."""
        for inc in list(self.get_active_incidents()):
            self.deactivate_incident(inc.incident_id)


# Global default incident manager
DEFAULT_INCIDENT_MANAGER: IncidentManager = IncidentManager()


def get_default_incident_manager() -> IncidentManager:
    """Return the global default incident manager instance."""
    return DEFAULT_INCIDENT_MANAGER


def get_all_incidents() -> List[Incident]:
    """Return all defined incident scenarios."""
    return DEFAULT_INCIDENT_MANAGER.get_all_incidents()


def get_incident(incident_id: str) -> Optional[Incident]:
    """Look up an incident by ID."""
    return DEFAULT_INCIDENT_MANAGER.get_incident(incident_id)


def activate_incident(incident_id: str) -> bool:
    """Activate an incident in the global environment."""
    return DEFAULT_INCIDENT_MANAGER.activate_incident(incident_id)


def deactivate_incident(incident_id: str) -> bool:
    """Deactivate an incident in the global environment."""
    return DEFAULT_INCIDENT_MANAGER.deactivate_incident(incident_id)


def reset_all_incidents() -> None:
    """Reset all active incidents to baseline state."""
    DEFAULT_INCIDENT_MANAGER.reset_all_incidents()


def get_active_incidents() -> List[Incident]:
    """Return all currently active incidents in the global environment."""
    return DEFAULT_INCIDENT_MANAGER.get_active_incidents()
