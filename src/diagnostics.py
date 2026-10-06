"""Diagnostics module.

Simulates common network diagnostic commands (ping, traceroute, nslookup,
ipconfig, route, arp) entirely offline using simulated network state.
No operating system commands or real network requests are executed.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .network_model import Host, NetworkModel, get_default_network
from .routing import Route, can_route, find_route, get_routing_table
from .services import DNSServer, get_default_dns_server
from .subnetting import get_network_info


# ===========================================================================
# 1. Simulated ping
# ===========================================================================


@dataclass
class PingResult:
    """Structured result of a simulated ping command."""

    source_ip: str
    destination_ip: str
    status: str  # "SUCCESS" or "FAILED"
    latency: str  # e.g., "10 ms" or "N/A"
    packet_loss: str  # e.g., "0%" or "100%"
    latency_ms: Optional[int] = None
    packet_loss_pct: int = 0
    reason: Optional[str] = None
    reply_from: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if the simulated ping succeeded."""
        return self.status == "SUCCESS"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "status": self.status,
            "latency": self.latency,
            "latency_ms": self.latency_ms,
            "packet_loss": self.packet_loss,
            "packet_loss_pct": self.packet_loss_pct,
            "reason": self.reason,
            "reply_from": self.reply_from,
            "success": self.success,
        }

    def __str__(self) -> str:
        lines = [
            f"Source: {self.source_ip}",
            f"Destination: {self.destination_ip}",
            "",
        ]
        if self.status == "SUCCESS":
            reply_target = self.reply_from or self.destination_ip
            lines.append(f"Reply from {reply_target}")
            lines.append(f"Status: {self.status}")
            lines.append(f"Latency: {self.latency}")
            lines.append(f"Packet loss: {self.packet_loss}")
        else:
            lines.append(f"Status: {self.status}")
            lines.append(f"Packet loss: {self.packet_loss}")
            if self.reason:
                lines.append(f"Reason: {self.reason}")
        return "\n".join(lines)


def _resolve_host_or_ip(
    target: str, network: NetworkModel
) -> Optional[str]:
    """Helper to resolve a hostname or validate an IP address."""
    clean = target.strip()
    # Check if target is known hostname
    host = network.find_host_by_hostname(clean)
    if host:
        return host.ip_address

    # Check if target is a valid IPv4 address
    try:
        ipaddress.IPv4Address(clean)
        return clean
    except ValueError:
        return None


def simulate_ping(
    source_ip: str,
    destination_ip: str,
    network: Optional[NetworkModel] = None,
) -> PingResult:
    """Simulate the ping command between two endpoints.

    Args:
        source_ip: Source IPv4 address or hostname.
        destination_ip: Destination IPv4 address or hostname.
        network: Optional custom network model.

    Returns:
        PingResult containing status, latency, packet loss, and reason.
    """
    target_net = network if network is not None else get_default_network()

    src_resolved = _resolve_host_or_ip(source_ip, target_net)
    dst_resolved = _resolve_host_or_ip(destination_ip, target_net)

    if not src_resolved or not dst_resolved:
        invalid_target = source_ip if not src_resolved else destination_ip
        return PingResult(
            source_ip=source_ip,
            destination_ip=destination_ip,
            status="FAILED",
            latency="N/A",
            packet_loss="100%",
            latency_ms=None,
            packet_loss_pct=100,
            reason=f"Invalid IP address or unresolved host: {invalid_target}",
        )

    # Check routing eligibility
    try:
        routable = can_route(src_resolved, dst_resolved, network=target_net)
    except ValueError as err:
        return PingResult(
            source_ip=src_resolved,
            destination_ip=dst_resolved,
            status="FAILED",
            latency="N/A",
            packet_loss="100%",
            latency_ms=None,
            packet_loss_pct=100,
            reason=str(err),
        )

    if not routable:
        return PingResult(
            source_ip=src_resolved,
            destination_ip=dst_resolved,
            status="FAILED",
            latency="N/A",
            packet_loss="100%",
            latency_ms=None,
            packet_loss_pct=100,
            reason="No route to destination",
        )

    # Determine whether intra-VLAN or inter-VLAN for deterministic latency
    src_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(src_resolved)),
        None,
    )
    dst_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(dst_resolved)),
        None,
    )

    if src_vlan and dst_vlan and src_vlan.vlan_id == dst_vlan.vlan_id:
        latency_val = 2
    else:
        latency_val = 10

    return PingResult(
        source_ip=src_resolved,
        destination_ip=dst_resolved,
        status="SUCCESS",
        latency=f"{latency_val} ms",
        latency_ms=latency_val,
        packet_loss="0%",
        packet_loss_pct=0,
        reply_from=dst_resolved,
    )


# ===========================================================================
# 2. Simulated traceroute
# ===========================================================================


@dataclass
class TracerouteHop:
    """Represents a single hop along a simulated traceroute path."""

    hop: int
    address: str
    name: str
    rtt: str = "1 ms"

    def to_dict(self) -> dict:
        """Convert hop to dictionary."""
        return {
            "hop": self.hop,
            "address": self.address,
            "name": self.name,
            "rtt": self.rtt,
        }

    def __str__(self) -> str:
        return f"{self.hop:<3} {self.address:<18} {self.name}"


@dataclass
class TracerouteResult:
    """Structured result of a simulated traceroute command."""

    source_ip: str
    destination_ip: str
    status: str  # "SUCCESS" or "FAILED"
    hops: List[TracerouteHop] = field(default_factory=list)
    reason: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if the destination was reached."""
        return self.status == "SUCCESS"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert traceroute result to dictionary."""
        return {
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "status": self.status,
            "hops": [h.to_dict() for h in self.hops],
            "reason": self.reason,
            "success": self.success,
        }

    def __str__(self) -> str:
        lines = [
            f"Traceroute from {self.source_ip} to {self.destination_ip}:",
            "",
        ]
        for hop in self.hops:
            lines.append(str(hop))
        if self.status != "SUCCESS" and self.reason:
            lines.append(f"Status: {self.status} - {self.reason}")
        return "\n".join(lines)


def simulate_traceroute(
    source_ip: str,
    destination_ip: str,
    network: Optional[NetworkModel] = None,
) -> TracerouteResult:
    """Simulate traceroute path tracing between two endpoints.

    Args:
        source_ip: Source IPv4 address or hostname.
        destination_ip: Destination IPv4 address or hostname.
        network: Optional custom network model.

    Returns:
        TracerouteResult containing list of TracerouteHop items.
    """
    target_net = network if network is not None else get_default_network()

    src_resolved = _resolve_host_or_ip(source_ip, target_net)
    dst_resolved = _resolve_host_or_ip(destination_ip, target_net)

    if not src_resolved or not dst_resolved:
        invalid_target = source_ip if not src_resolved else destination_ip
        return TracerouteResult(
            source_ip=source_ip,
            destination_ip=destination_ip,
            status="FAILED",
            hops=[],
            reason=f"Invalid IP address or unresolved host: {invalid_target}",
        )

    src_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(src_resolved)),
        None,
    )
    dst_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(dst_resolved)),
        None,
    )

    if not src_vlan:
        return TracerouteResult(
            source_ip=src_resolved,
            destination_ip=dst_resolved,
            status="FAILED",
            hops=[],
            reason=f"Source IP {src_resolved} does not belong to any local network.",
        )

    dst_route = find_route(dst_resolved)
    if not dst_route:
        # Trace up to router where routing fails
        hops = [
            TracerouteHop(hop=1, address=src_vlan.gateway, name="Gateway", rtt="1 ms"),
            TracerouteHop(
                hop=2,
                address="Router",
                name="Router (No route to destination)",
                rtt="* * *",
            ),
        ]
        return TracerouteResult(
            source_ip=src_resolved,
            destination_ip=dst_resolved,
            status="FAILED",
            hops=hops,
            reason="No route exists for destination network.",
        )

    # Same VLAN: local switching
    if dst_vlan and src_vlan.vlan_id == dst_vlan.vlan_id:
        hops = [
            TracerouteHop(
                hop=1, address="Core Switch", name="Core Switch", rtt="1 ms"
            ),
            TracerouteHop(
                hop=2, address=dst_resolved, name="Destination", rtt="2 ms"
            ),
        ]
        return TracerouteResult(
            source_ip=src_resolved,
            destination_ip=dst_resolved,
            status="SUCCESS",
            hops=hops,
        )

    # Inter-VLAN routing
    dst_gw = dst_vlan.gateway if dst_vlan else dst_route.next_hop
    hops = [
        TracerouteHop(hop=1, address=src_vlan.gateway, name="Gateway", rtt="1 ms"),
        TracerouteHop(hop=2, address="Router", name="Router", rtt="3 ms"),
        TracerouteHop(
            hop=3, address=dst_gw, name="Destination Gateway", rtt="6 ms"
        ),
        TracerouteHop(
            hop=4, address=dst_resolved, name="Destination", rtt="10 ms"
        ),
    ]

    return TracerouteResult(
        source_ip=src_resolved,
        destination_ip=dst_resolved,
        status="SUCCESS",
        hops=hops,
    )


# ===========================================================================
# 3. Simulated nslookup
# ===========================================================================


@dataclass
class NSLookupResult:
    """Structured result of a simulated nslookup command."""

    server: str
    name: str
    address: Optional[str] = None
    status: str = "SUCCESS"  # "SUCCESS", "NOT_FOUND", "SERVICE_DOWN"
    reason: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if lookup succeeded."""
        return self.status == "SUCCESS"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "server": self.server,
            "name": self.name,
            "address": self.address,
            "status": self.status,
            "reason": self.reason,
            "success": self.success,
        }

    def __str__(self) -> str:
        lines = [
            f"Server: {self.server}",
            f"Name: {self.name}",
        ]
        if self.address:
            lines.append(f"Address: {self.address}")
        lines.append("")
        lines.append(f"Status: {self.status}")
        if self.reason:
            lines.append(f"Reason: {self.reason}")
        return "\n".join(lines)


def simulate_nslookup(
    hostname: str,
    dns_server: Optional[DNSServer] = None,
) -> NSLookupResult:
    """Simulate DNS name resolution using the simulated DNS service.

    Args:
        hostname: Name of the host to resolve.
        dns_server: Optional custom DNSServer instance.

    Returns:
        NSLookupResult containing resolution details or failure reason.
    """
    server = dns_server if dns_server is not None else get_default_dns_server()
    clean_host = hostname.strip()
    resp = server.resolve(clean_host)

    if resp.status == "SUCCESS":
        return NSLookupResult(
            server="Simulated-DNS",
            name=clean_host,
            address=resp.ip_address,
            status="SUCCESS",
            reason=None,
        )
    elif resp.status == "SERVICE_DOWN":
        return NSLookupResult(
            server="Simulated-DNS",
            name=clean_host,
            address=None,
            status="SERVICE_DOWN",
            reason="DNS service is currently unavailable.",
        )
    else:
        return NSLookupResult(
            server="Simulated-DNS",
            name=clean_host,
            address=None,
            status="NOT_FOUND",
            reason=f"Hostname '{clean_host}' does not exist in DNS records.",
        )


# ===========================================================================
# 4. Simulated ipconfig
# ===========================================================================


@dataclass
class IPConfigResult:
    """Structured result of a simulated ipconfig command."""

    hostname: str
    ip_address: str
    subnet_mask: str
    default_gateway: str
    vlan: int
    mac_address: str
    network_address: str
    broadcast_address: str
    status: str = "SUCCESS"  # "SUCCESS" or "NOT_FOUND"
    reason: Optional[str] = None

    @property
    def success(self) -> bool:
        """True if host was found and configured."""
        return self.status == "SUCCESS"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert ipconfig result to dictionary."""
        return {
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "subnet_mask": self.subnet_mask,
            "default_gateway": self.default_gateway,
            "vlan": self.vlan,
            "mac_address": self.mac_address,
            "network_address": self.network_address,
            "broadcast_address": self.broadcast_address,
            "status": self.status,
            "reason": self.reason,
            "success": self.success,
        }

    def __str__(self) -> str:
        if self.status != "SUCCESS":
            return f"Status: {self.status}\nReason: {self.reason}"
        return (
            f"Hostname: {self.hostname}\n"
            f"IPv4 Address: {self.ip_address}\n"
            f"Subnet Mask: {self.subnet_mask}\n"
            f"Default Gateway: {self.default_gateway}\n"
            f"VLAN: {self.vlan}\n"
            f"MAC Address: {self.mac_address}\n"
            f"Network Address: {self.network_address}\n"
            f"Broadcast Address: {self.broadcast_address}"
        )


def simulate_ipconfig(
    hostname_or_ip: str,
    network: Optional[NetworkModel] = None,
) -> IPConfigResult:
    """Simulate ipconfig command inspecting a host's network configuration.

    Args:
        hostname_or_ip: Hostname or IPv4 address of the target machine.
        network: Optional custom network model.

    Returns:
        IPConfigResult containing network interface settings.
    """
    target_net = network if network is not None else get_default_network()
    clean_target = hostname_or_ip.strip()

    host: Optional[Host] = target_net.find_host_by_hostname(clean_target)
    if not host:
        host = target_net.find_host_by_ip(clean_target)

    if not host:
        return IPConfigResult(
            hostname=clean_target,
            ip_address="",
            subnet_mask="",
            default_gateway="",
            vlan=0,
            mac_address="",
            network_address="",
            broadcast_address="",
            status="NOT_FOUND",
            reason=f"Host or IP '{clean_target}' not found in network model.",
        )

    vlan = target_net.find_vlan_by_id(host.vlan_id)
    if vlan:
        net_info = get_network_info(vlan.network)
        net_addr = net_info["network_address"]
        bcast_addr = net_info["broadcast_address"]
    else:
        net_addr = ""
        bcast_addr = ""

    return IPConfigResult(
        hostname=host.hostname,
        ip_address=host.ip_address,
        subnet_mask=host.subnet_mask,
        default_gateway=host.default_gateway,
        vlan=host.vlan_id,
        mac_address=host.mac_address,
        network_address=net_addr,
        broadcast_address=bcast_addr,
        status="SUCCESS",
    )


# ===========================================================================
# 5. Simulated route
# ===========================================================================


@dataclass
class RouteTableResult:
    """Structured representation of the simulated routing table."""

    routes: List[Route]

    def __iter__(self):
        return iter(self.routes)

    def __len__(self) -> int:
        return len(self.routes)

    def __getitem__(self, idx: int) -> Route:
        return self.routes[idx]

    def to_dict(self) -> List[dict]:
        """Convert routes to list of dictionaries."""
        return [r.to_dict() for r in self.routes]

    def __str__(self) -> str:
        lines = [
            f"{'Destination':<18} {'Next Hop':<15} {'Interface':<12} {'Type':<10}",
            "-" * 55,
        ]
        for r in self.routes:
            lines.append(
                f"{r.destination_network:<18} {r.next_hop:<15} {r.interface:<12} {r.route_type:<10}"
            )
        return "\n".join(lines)


def simulate_route(
    network: Optional[NetworkModel] = None,
) -> RouteTableResult:
    """Return the current simulated routing table.

    Args:
        network: Optional custom network model.

    Returns:
        RouteTableResult containing list of Route entries.
    """
    routes = get_routing_table(network)
    return RouteTableResult(routes=routes)


# ===========================================================================
# 6. Simulated ARP
# ===========================================================================


@dataclass
class ARPEntry:
    """Represents an entry in the simulated ARP cache."""

    ip_address: str
    mac_address: str
    vlan: int
    hostname: str

    def to_dict(self) -> dict:
        """Convert entry to dictionary."""
        return {
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "vlan": self.vlan,
            "hostname": self.hostname,
        }

    def __str__(self) -> str:
        return f"{self.ip_address:<16} {self.mac_address:<20} {self.vlan:<6} {self.hostname}"


@dataclass
class ARPTableResult:
    """Structured representation of the simulated ARP table."""

    entries: List[ARPEntry]

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, idx: int) -> ARPEntry:
        return self.entries[idx]

    def to_dict(self) -> List[dict]:
        """Convert ARP entries to list of dictionaries."""
        return [e.to_dict() for e in self.entries]

    def __str__(self) -> str:
        lines = [
            f"{'IP Address':<16} {'MAC Address':<20} {'VLAN':<6} {'Hostname'}",
            "-" * 55,
        ]
        for e in self.entries:
            lines.append(str(e))
        return "\n".join(lines)


def simulate_arp(
    network: Optional[NetworkModel] = None,
) -> ARPTableResult:
    """Build and return the simulated ARP table from hosts in the network model.

    Args:
        network: Optional custom network model.

    Returns:
        ARPTableResult containing active host ARP mappings.
    """
    target_net = network if network is not None else get_default_network()
    entries: List[ARPEntry] = []

    for host in target_net.get_hosts():
        entries.append(
            ARPEntry(
                ip_address=host.ip_address,
                mac_address=host.mac_address,
                vlan=host.vlan_id,
                hostname=host.hostname,
            )
        )

    # Sort deterministically by IP integer address
    entries.sort(key=lambda e: int(ipaddress.IPv4Address(e.ip_address)))
    return ARPTableResult(entries=entries)
