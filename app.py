
import streamlit as st
import pandas as pd

from src.network_model import get_default_network
from src.routing import get_routing_table
from src.incidents import get_default_incident_manager
from src.troubleshooting import TroubleshootingEngine


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Network Troubleshooting Simulator",
    page_icon="🌐",
    layout="wide",
)


# ============================================================
# DATA
# ============================================================

network = get_default_network()
incident_manager = get_default_incident_manager()
routing_table = get_routing_table(network)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_items(collection):
    """Return collection values for dictionaries, lists or tuples."""
    if isinstance(collection, dict):
        return list(collection.values())

    return list(collection)


def get_value(obj, attribute, default="N/A"):
    """Safely retrieve an attribute or dictionary key."""
    if isinstance(obj, dict):
        return obj.get(attribute, default)

    return getattr(obj, attribute, default)


def format_value(value):
    """Convert objects such as IP networks to readable strings."""
    if value is None:
        return "N/A"

    return str(value)


# ============================================================
# NETWORK DATA
# ============================================================

devices = get_items(network.devices)
hosts = get_items(network.hosts)
vlans = get_items(network.vlans)


# ============================================================
# HEADER
# ============================================================

st.title("🌐 Network Troubleshooting Simulator")

st.markdown(
    """
    **Educational Network Simulation & Troubleshooting Platform**

    Simulated enterprise network featuring VLANs, IP addressing,
    routing, DHCP, DNS, diagnostics and incident analysis.
    """
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select a section",
    [
        "Overview",
        "Network Devices",
        "VLANs & IP Addressing",
        "Routing Table",
        "Connectivity Tests",
        "Incidents",
        "Troubleshooting",
    ],
)


# ============================================================
# KPI CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Network Devices", len(devices))

with col2:
    st.metric("Hosts", len(hosts))

with col3:
    st.metric("VLANs", len(vlans))

with col4:
    st.metric("Routing Entries", len(routing_table))


st.divider()


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.header("Network Overview")

    st.subheader("Simulated Enterprise Topology")

    st.code(
        """
                         Internet
                            |
                         Router
                            |
                      Core Switch
          ________________|________________
          |              |        |       |
       VLAN 10        VLAN 20   VLAN 30  VLAN 40
          IT             HR     Servers   Guest
        """,
        language="text",
    )

    st.subheader("VLAN Configuration")

    vlan_data = []

    for vlan in vlans:

        vlan_data.append(
            {
                "VLAN ID": get_value(vlan, "vlan_id"),
                "Name": get_value(vlan, "name"),
                "Network": format_value(
                    get_value(vlan, "network")
                ),
                "Gateway": get_value(vlan, "gateway"),
            }
        )

    st.dataframe(
        pd.DataFrame(vlan_data),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Network Hosts")

    host_data = []

    for host in hosts:

        host_data.append(
            {
                "Hostname": get_value(host, "hostname"),
                "IP Address": get_value(host, "ip_address"),
                "VLAN": get_value(host, "vlan_id"),
                "Gateway": get_value(
                    host,
                    "default_gateway",
                    get_value(host, "gateway"),
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(host_data),
        width="stretch",
        hide_index=True,
    )


# ============================================================
# NETWORK DEVICES
# ============================================================

elif page == "Network Devices":

    st.header("🖥️ Network Devices")

    device_data = []

    for device in devices:

        device_data.append(
            {
                "Device": get_value(
                    device,
                    "name",
                    get_value(device, "hostname"),
                ),
                "Type": get_value(device, "device_type"),
                "IP Address": get_value(device, "ip_address"),
                "Status": get_value(device, "status", "UP"),
            }
        )

    st.dataframe(
        pd.DataFrame(device_data),
        width="stretch",
        hide_index=True,
    )


# ============================================================
# VLANs & IP ADDRESSING
# ============================================================

elif page == "VLANs & IP Addressing":

    st.header("🔢 VLANs & IP Addressing")

    st.subheader("VLAN Configuration")

    vlan_data = []

    for vlan in vlans:

        vlan_data.append(
            {
                "VLAN ID": get_value(vlan, "vlan_id"),
                "Name": get_value(vlan, "name"),
                "Network": format_value(
                    get_value(vlan, "network")
                ),
                "Gateway": get_value(vlan, "gateway"),
            }
        )

    st.dataframe(
        pd.DataFrame(vlan_data),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Host Addressing")

    host_data = []

    for host in hosts:

        host_data.append(
            {
                "Hostname": get_value(host, "hostname"),
                "IP Address": get_value(host, "ip_address"),
                "VLAN": get_value(host, "vlan_id"),
                "Default Gateway": get_value(
                    host,
                    "default_gateway",
                    get_value(host, "gateway"),
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(host_data),
        width="stretch",
        hide_index=True,
    )


# ============================================================
# ROUTING TABLE
# ============================================================

elif page == "Routing Table":

    st.header("🛣️ Routing Table")

    routing_data = []

    for route in routing_table:

        routing_data.append(
            {
                "Destination": format_value(
                    get_value(route, "destination")
                ),
                "Next Hop": get_value(route, "next_hop"),
                "Interface": get_value(route, "interface"),
                "Type": get_value(route, "route_type"),
            }
        )

    st.dataframe(
        pd.DataFrame(routing_data),
        width="stretch",
        hide_index=True,
    )


# ============================================================
# CONNECTIVITY TESTS
# ============================================================

elif page == "Connectivity Tests":

    st.header("🔍 Connectivity Diagnostics")

    st.write(
        "Run simulated diagnostics without using the real network."
    )

    host_names = [
        get_value(host, "hostname")
        for host in hosts
    ]

    if len(host_names) >= 2:

        col1, col2 = st.columns(2)

        with col1:

            source = st.selectbox(
                "Source Host",
                host_names,
                key="diagnostic_source",
            )

        with col2:

            destination = st.selectbox(
                "Destination Host",
                host_names,
                index=1,
                key="diagnostic_destination",
            )

        diagnostic = st.selectbox(
            "Diagnostic",
            [
                "Ping",
                "Traceroute",
                "NSLookup",
                "IPConfig",
                "Route",
                "ARP",
            ],
        )

        if st.button(
            "Run Diagnostic",
            type="primary",
        ):

            from src import diagnostics

            source_obj = next(
                (
                    host
                    for host in hosts
                    if get_value(host, "hostname") == source
                ),
                None,
            )

            destination_obj = next(
                (
                    host
                    for host in hosts
                    if get_value(host, "hostname") == destination
                ),
                None,
            )

            source_ip = get_value(
                source_obj,
                "ip_address",
            )

            destination_ip = get_value(
                destination_obj,
                "ip_address",
            )

            try:

                if diagnostic == "Ping":

                    result = diagnostics.simulate_ping(
                        source_ip,
                        destination_ip,
                        network=network,
                    )

                elif diagnostic == "Traceroute":

                    result = diagnostics.simulate_traceroute(
                        source_ip,
                        destination_ip,
                        network=network,
                    )

                elif diagnostic == "NSLookup":

                    result = diagnostics.simulate_nslookup(
                        destination,
                    )

                elif diagnostic == "IPConfig":

                    result = diagnostics.simulate_ipconfig(
                        source_ip,
                    )

                elif diagnostic == "Route":

                    result = diagnostics.simulate_route(
                        source_ip,
                    )

                else:

                    result = diagnostics.simulate_arp(
                        source_ip,
                    )

                st.subheader("Diagnostic Result")

                st.code(
                    str(result),
                    language="text",
                )

            except Exception as exc:

                st.error(
                    f"Diagnostic error: {exc}"
                )


# ============================================================
# INCIDENTS
# ============================================================

elif page == "Incidents":

    st.header("🚨 Network Incidents")

    incidents = incident_manager.get_all_incidents()

    for incident in incidents:

        with st.expander(
            f"{incident.incident_id} — {incident.title}"
        ):

            st.write(
                f"**Severity:** {incident.severity}"
            )

            st.write(
                f"**Description:** {incident.description}"
            )

            st.write(
                f"**Affected device:** "
                f"{incident.affected_device}"
            )

            if incident.is_active:

                st.warning(
                    "🔴 Incident ACTIVE"
                )

            else:

                st.success(
                    "🟢 Incident inactive"
                )

            if st.button(
                "Activate / Deactivate",
                key=f"toggle_{incident.incident_id}",
            ):

                if incident.is_active:

                    incident_manager.deactivate_incident(
                        incident.incident_id
                    )

                else:

                    incident_manager.activate_incident(
                        incident.incident_id
                    )

                st.rerun()


# ============================================================
# TROUBLESHOOTING
# ============================================================

elif page == "Troubleshooting":

    st.header("🔧 Automated Troubleshooting")

    st.write(
        """
        The troubleshooting engine analyzes an active simulated
        incident, identifies diagnostic evidence, determines the
        root cause and provides a recommended corrective action.
        """
    )

    active_incidents = (
        incident_manager.get_active_incidents()
    )

    if not active_incidents:

        st.info(
            """
            No active incidents.

            Go to **Incidents**, activate a scenario,
            then return here to run the diagnosis.
            """
        )

    else:

        incident_options = {
            f"{incident.incident_id} — {incident.title}":
            incident.incident_id
            for incident in active_incidents
        }

        selected = st.selectbox(
            "Select an active incident",
            list(incident_options.keys()),
        )

        if st.button(
            "🔍 Run Troubleshooting",
            type="primary",
        ):

            incident_id = incident_options[selected]

            try:

                engine = TroubleshootingEngine(
                    incident_manager=incident_manager,
                    network=network,
                )

                result = engine.troubleshoot_incident(
                    incident_id
                )

                st.success(
                    "Troubleshooting completed successfully."
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Status",
                        result.status,
                    )

                with col2:

                    st.metric(
                        "Severity",
                        result.severity,
                    )

                with col3:

                    st.metric(
                        "Confidence",
                        result.confidence_level,
                    )

                st.divider()

                st.subheader("📋 Symptoms")

                for symptom in result.symptoms:

                    st.write(
                        f"• {symptom}"
                    )

                st.subheader("🔎 Diagnostic Evidence")

                for evidence in result.evidence:

                    st.write(
                        f"• {evidence}"
                    )

                st.subheader("🎯 Root Cause")

                st.error(
                    result.root_cause
                )

                st.subheader("🛠️ Recommended Action")

                st.info(
                    result.recommended_action
                )

            except Exception as exc:

                st.error(
                    f"Troubleshooting error: {exc}"
                )
