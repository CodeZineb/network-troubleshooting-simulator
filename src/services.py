"""Services module.

Responsible for simulated offline DHCP and DNS services for the enterprise
network model. Everything is simulated locally in-memory without real network calls.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .network_model import NetworkModel, get_default_network


# ===========================================================================
# Part 1 — Simulated DHCP
# ===========================================================================


@dataclass
class DHCPLease:
    """Represents an active DHCP address lease."""

    client_id: str
    ip_address: str
    subnet_mask: str
    default_gateway: str
    vlan_id: int

    @property
    def gateway(self) -> str:
        """Alias for default_gateway."""
        return self.default_gateway

    def to_dict(self) -> dict:
        """Convert lease to dictionary representation."""
        return {
            "client_id": self.client_id,
            "ip_address": self.ip_address,
            "subnet_mask": self.subnet_mask,
            "default_gateway": self.default_gateway,
            "gateway": self.gateway,
            "vlan_id": self.vlan_id,
        }


@dataclass
class DHCPResponse:
    """Structured response for a DHCP lease request."""

    success: bool
    status: str  # "SUCCESS", "SERVICE_DOWN", "POOL_EXHAUSTED", "VLAN_NOT_FOUND"
    client_id: str
    vlan_id: int
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    default_gateway: Optional[str] = None
    lease: Optional[DHCPLease] = None
    error_message: Optional[str] = None

    @property
    def gateway(self) -> Optional[str]:
        """Convenience alias for default_gateway."""
        return self.default_gateway

    def __getitem__(self, item: str) -> Any:
        """Allow subscript access."""
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "status": self.status,
            "client_id": self.client_id,
            "vlan_id": self.vlan_id,
            "ip_address": self.ip_address,
            "subnet_mask": self.subnet_mask,
            "default_gateway": self.default_gateway,
            "gateway": self.gateway,
            "error_message": self.error_message,
        }


@dataclass
class DHCPPool:
    """Represents a DHCP address pool and lease state for a specific VLAN."""

    vlan_id: int
    network: str
    gateway: str
    dhcp_pool: List[str] = field(default_factory=list)
    available_addresses: List[str] = field(default_factory=list)
    allocated_addresses: Dict[str, str] = field(default_factory=dict)
    service_status: str = "UP"  # "UP" or "DOWN"
    subnet_mask: str = "255.255.255.0"
    leases: Dict[str, DHCPLease] = field(default_factory=dict)

    def request_ip(self, client_id: str) -> DHCPResponse:
        """Allocate an IP address to a client from this pool."""
        client_key = client_id.strip().upper()

        if self.service_status.upper() != "UP":
            return DHCPResponse(
                success=False,
                status="SERVICE_DOWN",
                client_id=client_id,
                vlan_id=self.vlan_id,
                error_message=f"DHCP service for VLAN {self.vlan_id} is currently DOWN.",
            )

        # If client already has an active lease in this pool, return it
        if client_key in self.leases:
            existing = self.leases[client_key]
            return DHCPResponse(
                success=True,
                status="SUCCESS",
                client_id=client_id,
                vlan_id=self.vlan_id,
                ip_address=existing.ip_address,
                subnet_mask=existing.subnet_mask,
                default_gateway=existing.default_gateway,
                lease=existing,
            )

        if not self.available_addresses:
            return DHCPResponse(
                success=False,
                status="POOL_EXHAUSTED",
                client_id=client_id,
                vlan_id=self.vlan_id,
                error_message=f"DHCP pool for VLAN {self.vlan_id} is exhausted.",
            )

        # Allocate lowest available address deterministically
        allocated_ip = self.available_addresses.pop(0)
        self.allocated_addresses[client_key] = allocated_ip

        lease = DHCPLease(
            client_id=client_id,
            ip_address=allocated_ip,
            subnet_mask=self.subnet_mask,
            default_gateway=self.gateway,
            vlan_id=self.vlan_id,
        )
        self.leases[client_key] = lease

        return DHCPResponse(
            success=True,
            status="SUCCESS",
            client_id=client_id,
            vlan_id=self.vlan_id,
            ip_address=allocated_ip,
            subnet_mask=self.subnet_mask,
            default_gateway=self.gateway,
            lease=lease,
        )

    def release_ip(self, client_id_or_ip: str) -> bool:
        """Release an allocated IP address and return it to the available pool."""
        target = client_id_or_ip.strip()
        client_key = target.upper()

        found_client = None
        found_ip = None

        if client_key in self.allocated_addresses:
            found_client = client_key
            found_ip = self.allocated_addresses[client_key]
        else:
            for client, ip in list(self.allocated_addresses.items()):
                if ip == target:
                    found_client = client
                    found_ip = ip
                    break

        if not found_client or not found_ip:
            return False

        del self.allocated_addresses[found_client]
        if found_client in self.leases:
            del self.leases[found_client]

        if found_ip not in self.available_addresses:
            self.available_addresses.append(found_ip)
            # Maintain sorted order by IP integer value
            self.available_addresses.sort(
                key=lambda ip_str: int(ipaddress.IPv4Address(ip_str))
            )

        return True


class DHCPServer:
    """Simulated enterprise DHCP server managing pools across all VLANs."""

    def __init__(self, pools: Optional[Dict[int, DHCPPool]] = None) -> None:
        self.status: str = "UP"  # "UP" or "DOWN"
        self.pools: Dict[int, DHCPPool] = (
            pools if pools is not None else self._build_default_pools()
        )

    def _build_default_pools(self) -> Dict[int, DHCPPool]:
        """Construct default DHCP pools (e.g. .100 - .200) for all 4 enterprise VLANs."""
        network_model = get_default_network()
        pools: Dict[int, DHCPPool] = {}

        for vlan in network_model.get_vlans():
            base_parts = vlan.gateway.rsplit(".", 1)[0]  # e.g., "192.168.10"
            # Address range .100 to .200 (avoids gateway .1 and static hosts .10/.11)
            pool_ips = [f"{base_parts}.{i}" for i in range(100, 201)]
            available = list(pool_ips)

            pools[vlan.vlan_id] = DHCPPool(
                vlan_id=vlan.vlan_id,
                network=vlan.network,
                gateway=vlan.gateway,
                dhcp_pool=pool_ips,
                available_addresses=available,
                allocated_addresses={},
                service_status="UP",
                subnet_mask=vlan.netmask,
                leases={},
            )
        return pools

    def is_available(self) -> bool:
        """Check whether the DHCP service is operational."""
        return self.status.upper() == "UP"

    def set_status(self, status: str) -> None:
        """Set service status ('UP' or 'DOWN') across server and all pools."""
        normalized = status.strip().upper()
        self.status = normalized
        for pool in self.pools.values():
            pool.service_status = normalized

    def request_ip(self, client_id: str, vlan_id: int) -> DHCPResponse:
        """Request an IP address for a client in the specified VLAN."""
        if not self.is_available():
            return DHCPResponse(
                success=False,
                status="SERVICE_DOWN",
                client_id=client_id,
                vlan_id=vlan_id,
                error_message="DHCP server is currently DOWN.",
            )

        pool = self.pools.get(vlan_id)
        if not pool:
            return DHCPResponse(
                success=False,
                status="VLAN_NOT_FOUND",
                client_id=client_id,
                vlan_id=vlan_id,
                error_message=f"No DHCP pool configured for VLAN {vlan_id}.",
            )

        return pool.request_ip(client_id)

    def allocate_ip(self, client_id: str, vlan_id: int) -> DHCPResponse:
        """Alias for request_ip."""
        return self.request_ip(client_id, vlan_id)

    def release_ip(
        self, client_id_or_ip: str, vlan_id: Optional[int] = None
    ) -> bool:
        """Release an allocated IP address from a specific or all pools."""
        if vlan_id is not None:
            pool = self.pools.get(vlan_id)
            return pool.release_ip(client_id_or_ip) if pool else False

        # If vlan_id is omitted, search all pools
        for pool in self.pools.values():
            if pool.release_ip(client_id_or_ip):
                return True
        return False

    def get_leases(
        self, vlan_id: Optional[int] = None
    ) -> Dict[str, DHCPLease]:
        """Return active DHCP leases for a specific VLAN or across all VLANs."""
        if vlan_id is not None:
            pool = self.pools.get(vlan_id)
            return dict(pool.leases) if pool else {}

        all_leases: Dict[str, DHCPLease] = {}
        for pool in self.pools.values():
            all_leases.update(pool.leases)
        return all_leases


# ===========================================================================
# Part 2 — Simulated DNS
# ===========================================================================


@dataclass
class DNSResponse:
    """Structured result of a simulated DNS query."""

    success: bool
    status: str  # "SUCCESS", "NOT_FOUND", "SERVICE_DOWN"
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    record_type: str = "A"
    error_message: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        """Allow subscript access."""
        return getattr(self, item)

    def to_dict(self) -> dict:
        """Convert DNS response to dictionary."""
        return {
            "success": self.success,
            "status": self.status,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "record_type": self.record_type,
            "error_message": self.error_message,
        }


class DNSServer:
    """Simulated enterprise DNS server maintaining forward and reverse host records."""

    def __init__(self, records: Optional[Dict[str, str]] = None) -> None:
        self.status: str = "UP"  # "UP" or "DOWN"
        self._records: Dict[str, str] = {}
        if records is not None:
            for host, ip in records.items():
                self.add_record(host, ip)
        else:
            self._load_default_records()

    def _load_default_records(self) -> None:
        """Populate DNS records from the simulated enterprise network hosts."""
        network_model = get_default_network()
        for host in network_model.get_hosts():
            self._records[host.hostname.upper()] = host.ip_address

    def is_available(self) -> bool:
        """Check whether the DNS service is operational."""
        return self.status.upper() == "UP"

    def set_status(self, status: str) -> None:
        """Set DNS service status ('UP' or 'DOWN')."""
        self.status = status.strip().upper()

    def resolve(self, hostname: str) -> DNSResponse:
        """Perform forward DNS lookup (hostname -> IP)."""
        if not self.is_available():
            return DNSResponse(
                success=False,
                status="SERVICE_DOWN",
                hostname=hostname,
                error_message="DNS service is currently DOWN.",
            )

        clean_host = hostname.strip().upper()
        if clean_host in self._records:
            return DNSResponse(
                success=True,
                status="SUCCESS",
                hostname=hostname.strip(),
                ip_address=self._records[clean_host],
            )

        return DNSResponse(
            success=False,
            status="NOT_FOUND",
            hostname=hostname.strip(),
            error_message=f"DNS record not found for hostname '{hostname}'.",
        )

    def lookup(self, hostname: str) -> DNSResponse:
        """Alias for resolve."""
        return self.resolve(hostname)

    def reverse_lookup(self, ip_address: str) -> DNSResponse:
        """Perform reverse DNS lookup (IP -> hostname)."""
        if not self.is_available():
            return DNSResponse(
                success=False,
                status="SERVICE_DOWN",
                ip_address=ip_address,
                error_message="DNS service is currently DOWN.",
            )

        clean_ip = ip_address.strip()
        for host, ip in self._records.items():
            if ip == clean_ip:
                return DNSResponse(
                    success=True,
                    status="SUCCESS",
                    hostname=host,
                    ip_address=clean_ip,
                )

        return DNSResponse(
            success=False,
            status="NOT_FOUND",
            ip_address=clean_ip,
            error_message=f"No reverse DNS record found for IP '{ip_address}'.",
        )

    def add_record(self, hostname: str, ip_address: str) -> bool:
        """Add or update a DNS record."""
        # Validate IPv4 format
        try:
            ipaddress.IPv4Address(ip_address.strip())
        except ValueError:
            return False

        clean_host = hostname.strip().upper()
        self._records[clean_host] = ip_address.strip()
        return True

    def remove_record(self, hostname: str) -> bool:
        """Remove a DNS record by hostname."""
        clean_host = hostname.strip().upper()
        if clean_host in self._records:
            del self._records[clean_host]
            return True
        return False

    def get_records(self) -> Dict[str, str]:
        """Return a copy of all current DNS records."""
        return dict(self._records)


# ===========================================================================
# Part 3 — Service status & Default Instances
# ===========================================================================


DEFAULT_DHCP_SERVER: DHCPServer = DHCPServer()
DEFAULT_DNS_SERVER: DNSServer = DNSServer()


def get_default_dhcp_server() -> DHCPServer:
    """Return the global default DHCP server instance."""
    return DEFAULT_DHCP_SERVER


def get_default_dns_server() -> DNSServer:
    """Return the global default DNS server instance."""
    return DEFAULT_DNS_SERVER


def get_service_status(
    dhcp_server: Optional[DHCPServer] = None,
    dns_server: Optional[DNSServer] = None,
) -> Dict[str, str]:
    """Return the service status dictionary for DHCP and DNS."""
    dhcp = dhcp_server if dhcp_server is not None else DEFAULT_DHCP_SERVER
    dns = dns_server if dns_server is not None else DEFAULT_DNS_SERVER
    return {
        "DHCP": dhcp.status,
        "DNS": dns.status,
    }


def format_service_status(
    dhcp_server: Optional[DHCPServer] = None,
    dns_server: Optional[DNSServer] = None,
) -> str:
    """Format service status as plain text string."""
    status = get_service_status(dhcp_server, dns_server)
    return f"DHCP: {status['DHCP']}\nDNS: {status['DNS']}"


# Convenience module-level wrappers


def request_dhcp_ip(
    client_id: str,
    vlan_id: int,
    dhcp_server: Optional[DHCPServer] = None,
) -> DHCPResponse:
    """Request a DHCP IP allocation for a client."""
    dhcp = dhcp_server if dhcp_server is not None else DEFAULT_DHCP_SERVER
    return dhcp.request_ip(client_id, vlan_id)


def release_dhcp_ip(
    client_id_or_ip: str,
    vlan_id: Optional[int] = None,
    dhcp_server: Optional[DHCPServer] = None,
) -> bool:
    """Release a DHCP IP lease."""
    dhcp = dhcp_server if dhcp_server is not None else DEFAULT_DHCP_SERVER
    return dhcp.release_ip(client_id_or_ip, vlan_id)


def resolve_dns(
    hostname: str, dns_server: Optional[DNSServer] = None
) -> DNSResponse:
    """Perform forward DNS lookup."""
    dns = dns_server if dns_server is not None else DEFAULT_DNS_SERVER
    return dns.resolve(hostname)


def reverse_dns_lookup(
    ip_address: str, dns_server: Optional[DNSServer] = None
) -> DNSResponse:
    """Perform reverse DNS lookup."""
    dns = dns_server if dns_server is not None else DEFAULT_DNS_SERVER
    return dns.reverse_lookup(ip_address)
