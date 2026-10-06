"""Routing module.

Responsible for simulated offline enterprise routing logic, routing table lookup,
and path tracing across VLANs through the simulated router.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .network_model import NetworkModel, get_default_network


def _validate_ip(ip_address: str) -> ipaddress.IPv4Address:
    """Validate and parse an IPv4 address string."""
    if not isinstance(ip_address, str) or not ip_address.strip():
        raise ValueError(f"Invalid IPv4 address: {ip_address!r}")
    cleaned = ip_address.strip()
    try:
        return ipaddress.IPv4Address(cleaned)
    except (ipaddress.AddressValueError, ValueError) as err:
        raise ValueError(f"Invalid IPv4 address '{ip_address}': {err}") from err


@dataclass
class Route:
    """Represents an entry in the simulated routing table."""

    destination_network: str
    next_hop: str
    outgoing_interface: str
    route_type: str  # e.g., "connected", "static"
    description: str = ""

    @property
    def interface(self) -> str:
        """Alias for outgoing_interface."""
        return self.outgoing_interface

    def matches(self, ip: ipaddress.IPv4Address) -> bool:
        """Check if an IPv4Address matches this route's destination network."""
        try:
            net = ipaddress.IPv4Network(self.destination_network, strict=False)
            return ip in net
        except ValueError:
            return False

    def to_dict(self) -> dict:
        """Convert route attributes to a dictionary."""
        return {
            "destination_network": self.destination_network,
            "next_hop": self.next_hop,
            "outgoing_interface": self.outgoing_interface,
            "interface": self.outgoing_interface,
            "route_type": self.route_type,
            "description": self.description,
        }


@dataclass
class RouteSimulationResult:
    """Structured result describing a simulated routing path between two hosts."""

    source_ip: str
    destination_ip: str
    status: str  # "ROUTABLE", "LOCAL", "NO_ROUTE"
    path: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    source_host: Optional[str] = None
    destination_host: Optional[str] = None
    requires_router: bool = False

    @property
    def is_routable(self) -> bool:
        """True if the destination is routable via the router."""
        return self.status == "ROUTABLE"

    @property
    def is_reachable(self) -> bool:
        """True if traffic can reach destination either locally or via routing."""
        return self.status in ("ROUTABLE", "LOCAL")

    def __getitem__(self, item: str) -> Any:
        """Allow dict-like subscripting on the simulation result."""
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert simulation result to a dictionary."""
        return {
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "status": self.status,
            "path": list(self.path),
            "reason": self.reason,
            "source_host": self.source_host,
            "destination_host": self.destination_host,
            "requires_router": self.requires_router,
            "is_reachable": self.is_reachable,
            "is_routable": self.is_routable,
        }

    def __str__(self) -> str:
        """Generate human-readable simulation output."""
        lines = [
            f"Source: {self.source_ip}",
            f"Destination: {self.destination_ip}",
            "",
            "Path:",
        ]
        if self.path:
            lines.append(self.path[0])
            for hop in self.path[1:]:
                lines.append(f"→ {hop}")
        else:
            lines.append("(None)")
        lines.append("")
        lines.append(f"Status: {self.status}")
        if self.reason:
            lines.append(f"Reason: {self.reason}")
        return "\n".join(lines)


def build_default_routing_table(
    network: Optional[NetworkModel] = None,
) -> List[Route]:
    """Build the default routing table from connected VLANs in the network model."""
    target_net = network if network is not None else get_default_network()
    routes: List[Route] = []
    for vlan in target_net.get_vlans():
        routes.append(
            Route(
                destination_network=vlan.network,
                next_hop="connected",
                outgoing_interface=f"VLAN{vlan.vlan_id}",
                route_type="connected",
                description=f"Directly connected network for VLAN {vlan.vlan_id} ({vlan.name})",
            )
        )
    return routes


# Global default routing table instance
DEFAULT_ROUTING_TABLE: List[Route] = build_default_routing_table()


def get_routing_table(
    network: Optional[NetworkModel] = None,
) -> List[Route]:
    """Return the simulated routing table containing connected VLAN networks."""
    if network is not None:
        return build_default_routing_table(network)
    return list(DEFAULT_ROUTING_TABLE)


def find_route(
    destination_ip: str,
    routing_table: Optional[List[Route]] = None,
) -> Optional[Route]:
    """Find the best matching route for a destination IP using longest prefix match."""
    ip = _validate_ip(destination_ip)
    routes = (
        routing_table if routing_table is not None else get_routing_table()
    )

    best_route: Optional[Route] = None
    best_prefix_len = -1

    for route in routes:
        try:
            net = ipaddress.IPv4Network(route.destination_network, strict=False)
            if ip in net and net.prefixlen > best_prefix_len:
                best_prefix_len = net.prefixlen
                best_route = route
        except ValueError:
            continue

    return best_route


# Alias for finding best route
get_best_route = find_route
find_best_route = find_route


def can_route(
    source_ip: str,
    destination_ip: str,
    network: Optional[NetworkModel] = None,
    routing_table: Optional[List[Route]] = None,
) -> bool:
    """Determine whether the simulated router has a route allowing traffic between networks.

    Args:
        source_ip: Source IPv4 address string.
        destination_ip: Destination IPv4 address string.
        network: Optional custom network model.
        routing_table: Optional custom routing table.

    Returns:
        True if traffic can reach destination either within the same VLAN or via routed path.
    """
    src_ip = _validate_ip(source_ip)
    dst_ip = _validate_ip(destination_ip)

    target_net = network if network is not None else get_default_network()
    routes = (
        routing_table
        if routing_table is not None
        else get_routing_table(target_net)
    )

    # Find VLANs for source and destination
    src_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(str(src_ip))),
        None,
    )
    if not src_vlan:
        return False

    # Check host configuration (VLAN and Gateway)
    src_host_obj = target_net.find_host_by_ip(str(src_ip))
    if src_host_obj:
        if src_host_obj.vlan_id != src_vlan.vlan_id:
            return False
        dst_vlan = next(
            (v for v in target_net.get_vlans() if v.contains_ip(str(dst_ip))),
            None,
        )
        if dst_vlan and dst_vlan.vlan_id != src_vlan.vlan_id:
            if src_host_obj.default_gateway != src_vlan.gateway:
                return False

    # Check if a route exists for the destination
    dst_route = find_route(str(dst_ip), routes)
    if not dst_route:
        return False

    return True


def simulate_route(
    source_ip: str,
    destination_ip: str,
    network: Optional[NetworkModel] = None,
    routing_table: Optional[List[Route]] = None,
) -> RouteSimulationResult:
    """Simulate the path and routing decision between source and destination IP addresses.

    Args:
        source_ip: Source IPv4 address string.
        destination_ip: Destination IPv4 address string.
        network: Optional custom network model.
        routing_table: Optional custom routing table.

    Returns:
        RouteSimulationResult detailing status, path hops, and device names.
    """
    src_ip_obj = _validate_ip(source_ip)
    dst_ip_obj = _validate_ip(destination_ip)

    src_ip_str = str(src_ip_obj)
    dst_ip_str = str(dst_ip_obj)

    target_net = network if network is not None else get_default_network()
    routes = (
        routing_table
        if routing_table is not None
        else get_routing_table(target_net)
    )

    # Identify source host and source VLAN
    src_host_obj = target_net.find_host_by_ip(src_ip_str)
    src_host_name = src_host_obj.hostname if src_host_obj else src_ip_str

    src_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(src_ip_str)),
        None,
    )

    # Identify destination host and destination VLAN
    dst_host_obj = target_net.find_host_by_ip(dst_ip_str)
    dst_host_name = dst_host_obj.hostname if dst_host_obj else dst_ip_str

    dst_vlan = next(
        (v for v in target_net.get_vlans() if v.contains_ip(dst_ip_str)),
        None,
    )

    # Check destination route in routing table
    dest_route = find_route(dst_ip_str, routes)

    # 1. Source network not recognized
    if not src_vlan:
        return RouteSimulationResult(
            source_ip=src_ip_str,
            destination_ip=dst_ip_str,
            status="NO_ROUTE",
            path=[],
            reason=f"Source IP {src_ip_str} does not belong to any known network.",
            source_host=src_host_name,
            destination_host=dst_host_name,
            requires_router=False,
        )

    # 2. Destination network has no route in routing table
    if not dest_route:
        return RouteSimulationResult(
            source_ip=src_ip_str,
            destination_ip=dst_ip_str,
            status="NO_ROUTE",
            path=[],
            reason="No route exists for destination network.",
            source_host=src_host_name,
            destination_host=dst_host_name,
            requires_router=False,
        )

    # 3. Source host VLAN misconfiguration check
    if src_host_obj and src_host_obj.vlan_id != src_vlan.vlan_id:
        return RouteSimulationResult(
            source_ip=src_ip_str,
            destination_ip=dst_ip_str,
            status="NO_ROUTE",
            path=[],
            reason=f"Host {src_host_name} assigned to VLAN {src_host_obj.vlan_id}, mismatch with network VLAN {src_vlan.vlan_id}.",
            source_host=src_host_name,
            destination_host=dst_host_name,
            requires_router=False,
        )

    # 4. Inter-VLAN routing default gateway check
    if dst_vlan and src_vlan.vlan_id != dst_vlan.vlan_id and src_host_obj:
        if src_host_obj.default_gateway != src_vlan.gateway:
            return RouteSimulationResult(
                source_ip=src_ip_str,
                destination_ip=dst_ip_str,
                status="NO_ROUTE",
                path=[src_host_name, f"Gateway {src_host_obj.default_gateway} (Unreachable)"],
                reason=f"Default gateway {src_host_obj.default_gateway} is invalid (expected {src_vlan.gateway}).",
                source_host=src_host_name,
                destination_host=dst_host_name,
                requires_router=True,
            )

    # 5. Same VLAN - Layer 2 local switching (does NOT require inter-VLAN routing)
    if dst_vlan and src_vlan.vlan_id == dst_vlan.vlan_id:
        path = [
            src_host_name,
            "Core Switch",
            dst_host_name,
        ]
        return RouteSimulationResult(
            source_ip=src_ip_str,
            destination_ip=dst_ip_str,
            status="LOCAL",
            path=path,
            reason=None,
            source_host=src_host_name,
            destination_host=dst_host_name,
            requires_router=False,
        )

    # 4. Inter-VLAN routing through the router
    dst_gateway_str = dst_vlan.gateway if dst_vlan else dest_route.next_hop
    path = [
        src_host_name,
        f"Gateway {src_vlan.gateway}",
        "Router",
        f"Gateway {dst_gateway_str}",
        dst_host_name,
    ]
    return RouteSimulationResult(
        source_ip=src_ip_str,
        destination_ip=dst_ip_str,
        status="ROUTABLE",
        path=path,
        reason=None,
        source_host=src_host_name,
        destination_host=dst_host_name,
        requires_router=True,
    )
