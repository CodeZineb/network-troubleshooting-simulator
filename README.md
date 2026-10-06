# Network Troubleshooting Simulator

A lightweight educational network troubleshooting simulator built with Python and Streamlit.

The project simulates an enterprise network environment where users can explore network configuration, perform connectivity diagnostics, activate network incidents, and identify their root causes through a troubleshooting engine.

> **Important:** This is a fully simulated offline environment. It does not connect to real networks or modify the host computer's network configuration.

## Project Overview

The simulated architecture follows this structure:

```text
Internet
   |
 Router
   |
Core Switch
   |
   +--- VLAN 10 — IT
   +--- VLAN 20 — HR
   +--- VLAN 30 — Servers
   +--- VLAN 40 — Guest
```

### VLAN Configuration

| VLAN | Name | Network | Default Gateway |
|---:|---|---|---|
| 10 | IT | 192.168.10.0/24 | 192.168.10.1 |
| 20 | HR | 192.168.20.0/24 | 192.168.20.1 |
| 30 | Servers | 192.168.30.0/24 | 192.168.30.1 |
| 40 | Guest | 192.168.40.0/24 | 192.168.40.1 |

## Objectives

The project was designed to practice:

- IP addressing and subnetting
- VLAN concepts
- Inter-VLAN routing
- DHCP and DNS concepts
- Network diagnostics
- Incident identification
- Root-cause analysis
- Network troubleshooting methodology

## Features

### Network Model

The simulator includes:

- Router
- Core switch
- VLANs
- Hosts
- IP addresses
- Default gateways
- Network configuration validation

### Subnetting

The subnetting module provides:

- Network address
- Broadcast address
- Subnet mask
- Prefix length
- Usable host range
- IP/network validation

The calculations use Python's built-in `ipaddress` module.

### Routing

The routing simulator provides:

- Routing table
- Connected routes
- Route lookup
- Inter-VLAN routing simulation
- Route availability checks
- Simulated traceroute

### Simulated Network Services

#### DHCP

The project simulates:

- DHCP address pools
- IP allocation
- Lease management
- IP release
- DHCP service failure

#### DNS

The project simulates:

- Hostname-to-IP resolution
- IP-to-hostname resolution
- DNS records
- DNS service failure
- Incorrect DNS records

### Network Diagnostics

The following diagnostic tools are simulated:

- `ping`
- `traceroute`
- `nslookup`
- `ipconfig`
- `route`
- `arp`

These operations are implemented in Python and do not execute real network commands.

## Incident Scenarios

The simulator contains nine predefined network incidents:

| ID | Incident |
|---|---|
| INC-001 | Wrong Default Gateway |
| INC-002 | Wrong Subnet Mask |
| INC-003 | Wrong VLAN |
| INC-004 | Missing Route to Servers |
| INC-005 | DHCP Service Failure |
| INC-006 | DNS Service Failure |
| INC-007 | Duplicate IP Address |
| INC-008 | Incorrect DNS Record |
| INC-009 | Guest VLAN Link Down |

Each incident can be activated and analyzed through the troubleshooting system.

## Troubleshooting Engine

The troubleshooting engine analyzes active incidents and produces a structured diagnostic result including:

- Incident ID
- Severity
- Affected device
- Symptoms
- Diagnostic checks
- Evidence
- Root cause
- Recommended corrective action
- Confidence level
- Resolution status

The engine is rule-based and does **not** use artificial intelligence or machine learning.

## Dashboard

The project provides an interactive Streamlit dashboard with several sections:

- **Overview**
- **Network Devices**
- **VLANs & IP Addressing**
- **Routing Table**
- **Connectivity Tests**
- **Incidents**
- **Troubleshooting**

The dashboard allows users to explore the simulated network and investigate different network problems interactively.

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- `ipaddress`
- `unittest`

## Project Structure

```text
network-troubleshooting-simulator/
│
├── data/
│   └── README.md
│
├── src/
│   ├── __init__.py
│   ├── diagnostics.py
│   ├── incidents.py
│   ├── network_model.py
│   ├── routing.py
│   ├── services.py
│   ├── subnetting.py
│   └── troubleshooting.py
│
├── tests/
│   ├── __init__.py
│   ├── test_diagnostics.py
│   ├── test_incidents.py
│   ├── test_network_model.py
│   ├── test_routing.py
│   ├── test_services.py
│   └── test_subnetting.py
│
├── app.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Testing

The project includes unit tests covering the main components:

- Network model
- Subnetting
- Routing
- DHCP/DNS services
- Diagnostics
- Incident management

Run all tests with:

```powershell
python -m unittest discover -v
```

The complete test suite currently passes successfully.

## Installation

Clone the repository:

```powershell
git clone https://github.com/CodeZineb/network-troubleshooting-simulator.git
cd network-troubleshooting-simulator
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the Application

Start the Streamlit dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open the local Streamlit address displayed in the terminal.

## Usage

A typical troubleshooting workflow is:

1. Explore the simulated network.
2. Review VLANs and IP addressing.
3. Examine the routing table.
4. Run simulated connectivity diagnostics.
5. Activate a network incident.
6. Analyze the incident symptoms.
7. Run the troubleshooting engine.
8. Review the evidence and identified root cause.
9. Examine the recommended corrective action.

## Limitations

This project is an educational simulation.

It does **not**:

- communicate with real network devices
- generate real network traffic
- run a real DHCP server
- run a real DNS server
- modify Windows network configuration
- require Packet Tracer
- require GNS3
- require virtual machines
- connect to an external network

All network behavior is simulated in Python.

