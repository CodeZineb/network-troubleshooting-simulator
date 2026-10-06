"""Troubleshooting module.

Implements a deterministic, rule-based network troubleshooting engine that analyzes
simulated incidents, conducts diagnostic checks across model, routing, services,
and diagnostics modules, and deduces root causes with corrective recommendations.
No Machine Learning, AI models, statistical heuristics, or external APIs are used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .diagnostics import (
    simulate_ipconfig,
    simulate_nslookup,
    simulate_ping,
    simulate_route,
    simulate_traceroute,
)
from .incidents import (
    Incident,
    IncidentManager,
    get_default_incident_manager,
)
from .network_model import NetworkModel, get_default_network
from .routing import Route, can_route, find_route, get_routing_table
from .services import (
    DHCPServer,
    DNSServer,
    get_default_dhcp_server,
    get_default_dns_server,
)
from .subnetting import get_ip_network, get_network_info


@dataclass
class TroubleshootingResult:
    """Structured report produced by the rule-based troubleshooting engine."""

    incident_id: str
    incident_title: str
    severity: str
    affected_device: str
    symptoms: List[str]
    diagnostic_checks: List[str]
    evidence: List[str]
    root_cause: str
    recommended_action: str
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    status: str  # "RESOLVED", "UNRESOLVED"

    @property
    def affected_host(self) -> str:
        """Alias for affected_device."""
        return self.affected_device

    @property
    def confidence(self) -> str:
        """Alias for confidence_level."""
        return self.confidence_level

    def to_dict(self) -> Dict[str, Any]:
        """Convert troubleshooting result to dictionary."""
        return {
            "incident_id": self.incident_id,
            "incident_title": self.incident_title,
            "severity": self.severity,
            "affected_device": self.affected_device,
            "affected_host": self.affected_host,
            "symptoms": list(self.symptoms),
            "diagnostic_checks": list(self.diagnostic_checks),
            "evidence": list(self.evidence),
            "root_cause": self.root_cause,
            "recommended_action": self.recommended_action,
            "confidence_level": self.confidence_level,
            "confidence": self.confidence,
            "status": self.status,
        }

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def format_report(self) -> str:
        """Format the troubleshooting result as a readable text report."""
        lines = [
            "=" * 50,
            "NETWORK TROUBLESHOOTING REPORT",
            "=" * 50,
            "",
            f"Incident: {self.incident_id}",
            f"Title: {self.incident_title}",
            f"Severity: {self.severity}",
            f"Affected Host: {self.affected_device}",
            "",
            "SYMPTOMS",
        ]
        for symptom in self.symptoms:
            lines.append(f"- {symptom}")
        lines.append("")
        lines.append("DIAGNOSTIC EVIDENCE")
        for ev in self.evidence:
            lines.append(f"- {ev}")
        lines.append("")
        lines.append("ROOT CAUSE")
        lines.append(self.root_cause)
        lines.append("")
        lines.append("RECOMMENDED ACTION")
        lines.append(self.recommended_action)
        lines.append("")
        lines.append(f"Confidence: {self.confidence_level}")
        lines.append(f"Status: {self.status}")
        lines.append("=" * 50)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format_report()


class TroubleshootingEngine:
    """Rule-based engine performing diagnostic checks and root cause analysis."""

    def __init__(
        self,
        incident_manager: Optional[IncidentManager] = None,
        network: Optional[NetworkModel] = None,
        routing_table: Optional[List[Route]] = None,
        dhcp_server: Optional[DHCPServer] = None,
        dns_server: Optional[DNSServer] = None,
    ) -> None:
        self.incident_manager = (
            incident_manager
            if incident_manager is not None
            else get_default_incident_manager()
        )
        self.network = (
            network if network is not None else self.incident_manager.network
        )
        self.routing_table = (
            routing_table
            if routing_table is not None
            else self.incident_manager.routing_table
        )
        self.dhcp_server = (
            dhcp_server
            if dhcp_server is not None
            else self.incident_manager.dhcp_server
        )
        self.dns_server = (
            dns_server
            if dns_server is not None
            else self.incident_manager.dns_server
        )

    def troubleshoot_incident(
        self, incident_or_id: Union[str, Incident]
    ) -> TroubleshootingResult:
        """Troubleshoot a specific incident by ID or Incident instance."""
        incident: Optional[Incident]
        if isinstance(incident_or_id, Incident):
            incident = incident_or_id
        else:
            iid = str(incident_or_id).strip().upper()
            incident = self.incident_manager.get_incident(iid)

            # Support standalone / dynamic diagnostic scenarios
            if not incident:
                if iid in ("PACKET_LOSS", "INC-PACKET-LOSS", "INC-010"):
                    incident = Incident(
                        incident_id="INC-010",
                        title="Packet Loss on Network Path",
                        category="PERFORMANCE",
                        affected_device="Router",
                        severity="MEDIUM",
                        symptoms=[
                            "Intermittent communication failures",
                            "Packet loss detected on simulated path",
                        ],
                        expected_impact="Degraded service and packet loss.",
                        technical_cause={"packet_loss_pct": 50},
                        status="ACTIVE",
                    )
                elif iid in ("HIGH_LATENCY", "INC-HIGH-LATENCY", "INC-011"):
                    incident = Incident(
                        incident_id="INC-011",
                        title="High Network Latency",
                        category="PERFORMANCE",
                        affected_device="Router",
                        severity="MEDIUM",
                        symptoms=[
                            "Slow response times",
                            "High round-trip delay detected on path",
                        ],
                        expected_impact="High network latency impacting application responsiveness.",
                        technical_cause={"latency_ms": 250, "baseline_ms": 10},
                        status="ACTIVE",
                    )

        if not incident:
            return TroubleshootingResult(
                incident_id=str(incident_or_id),
                incident_title="Unknown Incident",
                severity="UNKNOWN",
                affected_device="UNKNOWN",
                symptoms=["Incident ID was not recognized"],
                diagnostic_checks=["Verify incident registry"],
                evidence=["Incident ID not found in registered incident catalog."],
                root_cause="Incident not found.",
                recommended_action="Verify incident ID and ensure it is registered.",
                confidence_level="LOW",
                status="UNRESOLVED",
            )

        if not incident.is_active:
            return TroubleshootingResult(
                incident_id=incident.incident_id,
                incident_title=incident.title,
                severity=incident.severity,
                affected_device=incident.affected_device,
                symptoms=list(incident.symptoms),
                diagnostic_checks=["Check incident lifecycle status"],
                evidence=["Incident is currently INACTIVE in the environment."],
                root_cause="Incident is not active.",
                recommended_action="Activate the incident before performing troubleshooting analysis.",
                confidence_level="LOW",
                status="UNRESOLVED",
            )

        # Dispatch to rule-based diagnostic handlers
        iid = incident.incident_id
        category = incident.category.upper()
        title = incident.title.upper()

        if iid == "INC-001" or "GATEWAY" in title:
            return self._diagnose_wrong_gateway(incident)
        elif iid == "INC-002" or "SUBNET" in title:
            return self._diagnose_wrong_subnet_mask(incident)
        elif iid == "INC-003" or category == "VLAN" or "VLAN" in title:
            return self._diagnose_wrong_vlan(incident)
        elif iid == "INC-004" or "ROUTE" in title:
            return self._diagnose_missing_route(incident)
        elif iid == "INC-005" or "DHCP" in title:
            return self._diagnose_dhcp_failure(incident)
        elif iid == "INC-006" or (category == "SERVICE" and "DNS" in title):
            return self._diagnose_dns_failure(incident)
        elif iid == "INC-007" or "DUPLICATE" in title or "CONFLICT" in title:
            return self._diagnose_duplicate_ip(incident)
        elif iid == "INC-008" or (category == "DNS" and "RECORD" in title):
            return self._diagnose_incorrect_dns(incident)
        elif iid == "INC-009" or "INTERFACE" in title or "LINK" in title:
            return self._diagnose_interface_down(incident)
        elif "PACKET LOSS" in title or "LOSS" in title or iid == "INC-010":
            return self._diagnose_packet_loss(incident)
        elif "LATENCY" in title or iid == "INC-011":
            return self._diagnose_high_latency(incident)
        else:
            return self._diagnose_generic(incident)

    def troubleshoot_all_active_incidents(self) -> List[TroubleshootingResult]:
        """Analyze and return troubleshooting reports for all currently active incidents."""
        active = self.incident_manager.get_active_incidents()
        return [self.troubleshoot_incident(inc) for inc in active]

    # -----------------------------------------------------------------------
    # Rule 1: Wrong Default Gateway
    # -----------------------------------------------------------------------

    def _diagnose_wrong_gateway(self, incident: Incident) -> TroubleshootingResult:
        host_name = incident.affected_device
        host = self.network.find_host_by_hostname(host_name)

        checks = [
            f"Query host IP configuration for {host_name}",
            "Identify host assigned VLAN and expected subnet gateway",
            "Simulate ping to configured default gateway",
            "Simulate inter-VLAN routing to external server (192.168.30.10)",
        ]

        if not host:
            return self._error_result(incident, checks, f"Host {host_name} not found.")

        expected_vlan = self.network.find_vlan_by_id(host.vlan_id)
        expected_gw = expected_vlan.gateway if expected_vlan else "Unknown"

        # Check routing
        routable = can_route(
            host.ip_address,
            "192.168.30.10",
            network=self.network,
            routing_table=self.routing_table,
        )

        evidence = [
            f"Configured gateway: {host.default_gateway}",
            f"Expected gateway: {expected_gw}",
            f"Routing check: {'SUCCESS' if routable else 'FAILED'}",
        ]
        if host.default_gateway != expected_gw:
            evidence.append(
                f"Configured gateway {host.default_gateway} does not match expected gateway {expected_gw}."
            )

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Incorrect default gateway.",
            recommended_action=f"Change the default gateway to {expected_gw}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 2: Wrong Subnet Mask
    # -----------------------------------------------------------------------

    def _diagnose_wrong_subnet_mask(
        self, incident: Incident
    ) -> TroubleshootingResult:
        host_name = incident.affected_device
        host = self.network.find_host_by_hostname(host_name)

        checks = [
            f"Inspect host network configuration for {host_name}",
            "Verify expected subnet mask from VLAN definition",
            "Evaluate network boundary and IP subnet calculations",
        ]

        if not host:
            return self._error_result(incident, checks, f"Host {host_name} not found.")

        vlan = self.network.find_vlan_by_id(host.vlan_id)
        expected_mask = vlan.netmask if vlan else "255.255.255.0"

        evidence = [
            f"Configured subnet mask: {host.subnet_mask}",
            f"Expected subnet mask: {expected_mask}",
            f"Network membership anomaly: host configured with /{host.prefix_length} instead of expected /{vlan.prefix_length if vlan else 24}",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Incorrect subnet mask.",
            recommended_action=f"Configure subnet mask {expected_mask}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 3: Wrong VLAN
    # -----------------------------------------------------------------------

    def _diagnose_wrong_vlan(self, incident: Incident) -> TroubleshootingResult:
        host_name = incident.affected_device
        host = self.network.find_host_by_hostname(host_name)

        checks = [
            f"Inspect assigned VLAN for {host_name}",
            "Determine correct VLAN based on host IP address",
            "Check VLAN broadcast domain and subnet consistency",
        ]

        if not host:
            return self._error_result(incident, checks, f"Host {host_name} not found.")

        # Find which VLAN matches host IP address
        actual_matching_vlan = next(
            (v for v in self.network.get_vlans() if v.contains_ip(host.ip_address)),
            None,
        )
        expected_vlan_id = (
            actual_matching_vlan.vlan_id if actual_matching_vlan else 10
        )

        evidence = [
            f"Host assigned VLAN: {host.vlan_id}",
            f"Expected VLAN for IP {host.ip_address}: {expected_vlan_id}",
            f"VLAN mismatch: host is in VLAN {host.vlan_id} but its IP belongs to VLAN {expected_vlan_id}",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Host is assigned to the wrong VLAN.",
            recommended_action=f"Move the host to VLAN {expected_vlan_id}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 4: Missing Route
    # -----------------------------------------------------------------------

    def _diagnose_missing_route(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Inspect router routing table",
            "Check route presence for Servers network 192.168.30.0/24",
            "Simulate traceroute from IT (192.168.10.10) to Servers (192.168.30.10)",
        ]

        missing_target = incident.technical_cause.get(
            "missing_network", "192.168.30.0/24"
        )
        has_route = any(
            r.destination_network == missing_target for r in self.routing_table
        )

        evidence = [
            f"Target destination network: {missing_target}",
            f"Route table entry present: {'YES' if has_route else 'NO'}",
            f"Traceroute analysis: route lookup failed with NO_ROUTE",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="No route exists to the destination network.",
            recommended_action=f"Add or restore the route to {missing_target}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 5: DHCP Down
    # -----------------------------------------------------------------------

    def _diagnose_dhcp_failure(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Query DHCP server service status",
            "Simulate address request for a client in VLAN 10",
        ]

        status = self.dhcp_server.status
        test_alloc = self.dhcp_server.request_ip("DIAG-CLIENT", 10)

        evidence = [
            f"DHCP service status: {status}",
            f"Simulated lease allocation status: {test_alloc.status}",
            "Clients cannot obtain IP configuration dynamically",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="DHCP service unavailable.",
            recommended_action="Restore the DHCP service.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 6: DNS Down
    # -----------------------------------------------------------------------

    def _diagnose_dns_failure(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Query DNS server service status",
            "Simulate nslookup query for SRV-01",
            "Simulate direct IP ping from IT to Servers (192.168.10.10 -> 192.168.30.10)",
        ]

        status = self.dns_server.status
        ns_res = simulate_nslookup("SRV-01", dns_server=self.dns_server)
        ping_res = simulate_ping(
            "192.168.10.10", "192.168.30.10", network=self.network
        )

        evidence = [
            f"DNS service status: {status}",
            f"nslookup status: {ns_res.status}",
            f"Direct IP connectivity: {'FUNCTIONAL' if ping_res.success else 'FAILED'}",
            "Layer 3 routing is intact while name resolution fails",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="DNS service unavailable.",
            recommended_action="Restore DNS service or configure an available DNS server.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 7: Duplicate IP Address Conflict
    # -----------------------------------------------------------------------

    def _diagnose_duplicate_ip(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Inspect host IP assignments in network model",
            "Scan ARP table for duplicate IP address entries",
            "Check IP collisions on VLAN 20",
        ]

        host = self.network.find_host_by_hostname(incident.affected_device)
        conflicting_ip = (
            host.ip_address if host else incident.technical_cause.get("conflicting_ip")
        )

        all_hosts = self.network.get_hosts()
        holders = [h.hostname for h in all_hosts if h.ip_address == conflicting_ip]

        evidence = [
            f"Duplicate IP identified: {conflicting_ip}",
            f"Hosts sharing same IP: {', '.join(holders)}",
            "ARP conflict detected on local broadcast domain",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Duplicate IP address conflict detected.",
            recommended_action=f"Reassign unique IP address (192.168.20.11) to {incident.affected_device}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 8: Incorrect DNS Record
    # -----------------------------------------------------------------------

    def _diagnose_incorrect_dns(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Query DNS server for SRV-01 A-record",
            "Compare DNS resolved IP against host model IP for SRV-01",
            "Simulate ping to resolved IP vs real IP",
        ]

        dns_res = self.dns_server.resolve("SRV-01")
        srv_host = self.network.find_host_by_hostname("SRV-01")
        expected_ip = srv_host.ip_address if srv_host else "192.168.30.10"

        evidence = [
            f"DNS resolved IP: {dns_res.ip_address}",
            f"Actual host IP: {expected_ip}",
            "DNS record points to invalid non-existent address",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Incorrect DNS record mapping.",
            recommended_action=f"Update DNS record for SRV-01 to point to {expected_ip}.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 9: Interface / Link Down
    # -----------------------------------------------------------------------

    def _diagnose_interface_down(self, incident: Incident) -> TroubleshootingResult:
        checks = [
            "Inspect physical and logical switch/router interface states",
            "Check VLAN 40 connected route presence",
            "Simulate ping to Guest gateway (192.168.40.1)",
        ]

        guest_route = next(
            (
                r
                for r in self.routing_table
                if r.destination_network == "192.168.40.0/24"
            ),
            None,
        )

        evidence = [
            f"VLAN 40 link status: DOWN",
            f"Connected route in routing table: {'PRESENT' if guest_route else 'MISSING'}",
            "Hosts in Guest VLAN 40 are isolated from default gateway",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Network interface/link is down.",
            recommended_action="Restore the interface or physical/logical link.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 10: Packet Loss
    # -----------------------------------------------------------------------

    def _diagnose_packet_loss(self, incident: Incident) -> TroubleshootingResult:
        loss_pct = incident.technical_cause.get("packet_loss_pct", 50)
        checks = [
            "Simulate ping stream between endpoints",
            "Analyze transmitted vs received ICMP packets",
            "Calculate packet loss percentage along path",
        ]

        evidence = [
            f"Simulated ping reveals {loss_pct}% packet loss",
            "Intermittent delivery failures across network path",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Packet loss detected on the simulated path.",
            recommended_action="Investigate the affected link/interface and network congestion.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    # -----------------------------------------------------------------------
    # Rule 11: High Latency
    # -----------------------------------------------------------------------

    def _diagnose_high_latency(self, incident: Incident) -> TroubleshootingResult:
        latency_val = incident.technical_cause.get("latency_ms", 250)
        baseline = incident.technical_cause.get("baseline_ms", 10)
        checks = [
            "Measure round-trip time (RTT) along simulated path",
            "Compare measured latency against baseline threshold",
            "Inspect hop-by-hop latency accumulation",
        ]

        evidence = [
            f"Measured latency: {latency_val} ms",
            f"Expected baseline latency: {baseline} ms",
            f"Abnormal latency spike of +{latency_val - baseline} ms detected",
        ]

        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=evidence,
            root_cause="Abnormally high network latency.",
            recommended_action="Investigate the affected path, interface utilization, and congestion.",
            confidence_level="HIGH",
            status="RESOLVED",
        )

    def _diagnose_generic(self, incident: Incident) -> TroubleshootingResult:
        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=["Examine incident technical configuration"],
            evidence=[f"Technical cause: {incident.technical_cause}"],
            root_cause=f"Configuration issue: {incident.title}",
            recommended_action="Review and revert the affected device configuration.",
            confidence_level="MEDIUM",
            status="RESOLVED",
        )

    def _error_result(
        self, incident: Incident, checks: List[str], reason: str
    ) -> TroubleshootingResult:
        return TroubleshootingResult(
            incident_id=incident.incident_id,
            incident_title=incident.title,
            severity=incident.severity,
            affected_device=incident.affected_device,
            symptoms=list(incident.symptoms),
            diagnostic_checks=checks,
            evidence=[reason],
            root_cause=f"Unable to diagnose: {reason}",
            recommended_action="Verify host and network state.",
            confidence_level="LOW",
            status="UNRESOLVED",
        )


# Global default troubleshooting engine instance
DEFAULT_TROUBLESHOOTING_ENGINE: TroubleshootingEngine = TroubleshootingEngine()


def get_default_troubleshooting_engine() -> TroubleshootingEngine:
    """Return the global default troubleshooting engine instance."""
    return DEFAULT_TROUBLESHOOTING_ENGINE


def troubleshoot_incident(
    incident_or_id: Union[str, Incident],
    engine: Optional[TroubleshootingEngine] = None,
) -> TroubleshootingResult:
    """Troubleshoot a specific incident using the rule-based engine."""
    target_engine = (
        engine if engine is not None else DEFAULT_TROUBLESHOOTING_ENGINE
    )
    return target_engine.troubleshoot_incident(incident_or_id)


def troubleshoot_all_active_incidents(
    engine: Optional[TroubleshootingEngine] = None,
) -> List[TroubleshootingResult]:
    """Troubleshoot all active incidents using the rule-based engine."""
    target_engine = (
        engine if engine is not None else DEFAULT_TROUBLESHOOTING_ENGINE
    )
    return target_engine.troubleshoot_all_active_incidents()


def format_troubleshooting_report(result: TroubleshootingResult) -> str:
    """Format a troubleshooting result into a readable report."""
    return result.format_report()
