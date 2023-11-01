# flake8: noqa E501
import asyncio
import re
import json
import getpass
import logging
import yaml
import aiofiles
from scrapli.driver.core import AsyncIOSXEDriver
from scrapli.driver.core import AsyncNXOSDriver
from itertools import zip_longest
from typing import Any, Callable


# Setting up logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s]: %(message)s"
)


def parse_nxos_show_version(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show version command."""

    logging.info('Parsing nxos "show version"...')

    # Define regular expressions for the attributes
    regex_map = {
        "bios_version": r"BIOS: version (.+)",
        "loader_version": r"loader: version (.+)",
        "kickstart_version": r"kickstart: version (.+)",
        "system_version": r"system: version (.+)",
        "bios_compile_time": r"BIOS compile time: (.+)",
        "kickstart_image_file": r"kickstart image file is: (.+)",
        "kickstart_compile_time": r"kickstart compile time: (.+)",
        "system_image_file": r"system image file is: (.+)",
        "system_compile_time": r"system compile time: (.+)",
        "chassis": r"cisco (.+Chassis)",
        "processor_info": r"(.+CPU with .+ kB of memory.)",
        "processor_board_id": r"Processor Board ID (.+)",
        "device_name": r"Device name: (.+)",
        "bootflash": r"bootflash: (.+ kB)",
        "kernel_uptime": r"Kernel uptime is (.+)",
        "last_reset": r"Last reset at .+ after (.+)",
        "last_reset_reason": r"Reason: (.+)",
        "system_version_long": r"System version: (.+)",
    }

    result = {}
    for key, regex in regex_map.items():
        match = re.search(regex, cli_output, re.MULTILINE)
        if match:
            result[key] = match.group(1)

    return result


def parse_nxos_show_interface(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface command."""

    logging.info('Parsing nxos "show interface"...')

    # Define regular expressions for the attributes
    # Define regular expressions for the attributes
    regex_map = {
        "interface": r"(.+?) is (up|down)",
        "eth_bundle": r"Belongs to (\w+)",
        "hardware_address": r"Hardware:.+?address: (.+?) \(bia",
        "description": r"Description: (.+)",
        "mtu": r"MTU (.+?) bytes",
        "bandwidth": r"BW (.+?) Kbit",
        "delay": r"DLY (.+?) usec",
        "reliability": r"reliability (.+?),",
        "txload": r"txload (.+?),",
        "rxload": r"rxload (.+?)",
        "encapsulation": r"Encapsulation (.+)",
        "port_mode": r"Port mode is (.+)",
        "duplex": r"(\w+-duplex)",
        "speed": r", (\d+ Gb/s),",
        "medium": r"media type is (.+)",
        "input_rate_30_sec": r"30 seconds input rate (.+?) bits",
        "output_rate_30_sec": r"30 seconds output rate (.+?) bits",
        "input_rate_5_min": r"input rate (.+?) bps",
        "output_rate_5_min": r"output rate (.+?) bps",
        "input_packets": r"(\d+) input packets",
        "output_packets": r"(\d+) output packets",
    }

    result = {"interfaces": {}}
    current_interface = ""

    for line in cli_output.split("\n"):
        if not line.strip():
            continue
        if "is up" in line or "is down" in line:
            match = re.search(regex_map["interface"], line)
            if match:
                current_interface = match.group(1)
                result["interfaces"][current_interface] = {"status": match.group(2)}
                continue
        for key, regex in regex_map.items():
            match = re.search(regex, line)
            if match and current_interface:
                result["interfaces"][current_interface][key] = match.group(1)

    return result


def parse_nxos_show_interface_trunk(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface trunk command."""

    logging.info('Parsing nxos "show interface trunk"...')

    # Regex patterns map
    regex_map = {
        "port_details_header": r"Port\s+Native\s+Status\s+Port",
        "port_details": r"(?P<port>\S+)\s+(?P<native_vlan>\d+)\s+(?P<status>\S+(?:-\S+)?)\s+(?P<port_channel>\S+)",
        "vlans_allowed_header": r"Port\s+Vlans Allowed on Trunk",
        "vlans_allowed": r"(?P<port>\S+)\s+(?P<vlans_allowed>[\d,-]+)",
        "stp_forwarding_header": r"Port\s+STP Forwarding",
        "stp_forwarding": r"(?P<port>\S+)\s+(?P<stp_forwarding>\S+)",
    }

    # Identify the start indices of each section based on headers
    port_details_index = re.search(regex_map["port_details_header"], cli_output).end()
    vlans_allowed_index = re.search(regex_map["vlans_allowed_header"], cli_output).end()
    stp_forwarding_index = re.search(regex_map["stp_forwarding_header"], cli_output).end()

    # Extract section strings
    port_details_string = cli_output[port_details_index:vlans_allowed_index]
    vlans_allowed_string = cli_output[vlans_allowed_index:stp_forwarding_index]
    stp_forwarding_string = cli_output[stp_forwarding_index:]

    # Parse port details section
    port_details = {}
    for match in re.finditer(regex_map["port_details"], port_details_string):
        port = match.group("port")
        port_details[port] = {
            "Native Vlan": match.group("native_vlan"),
            "Status": match.group("status"),
            "Port Channel": match.group("port_channel"),
        }

    # Parse VLANs allowed section
    vlans_allowed = {}
    for match in re.finditer(regex_map["vlans_allowed"], vlans_allowed_string):
        port = match.group("port")
        vlans_allowed[port] = match.group("vlans_allowed")

    # Parse STP Forwarding section
    stp_forwarding = {}
    for match in re.finditer(regex_map["stp_forwarding"], stp_forwarding_string):
        port = match.group("port")
        stp_forwarding[port] = match.group("stp_forwarding")

    # Combine the parsed data into a single dictionary
    result = {}
    for port in port_details:
        result[port] = port_details[port]
        result[port]["Vlans Allowed on Trunk"] = vlans_allowed.get(port, "")
        result[port]["STP Forwarding"] = stp_forwarding.get(port, "")

    return result


def parse_nxos_show_vlan(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show vlan command."""

    logging.info('Parsing nxos "show vlan"...')

    # Regex patterns map
    regex_map = {
        "vlan_details_header": r"VLAN\s+Name\s+Status\s+Ports",
        "vlan_details": r"(?P<vlan_id>\d+)\s+(?P<vlan_name>\S+)\s+(?P<status>\S+)(?P<ports>[\w\s,/-]*)",
        "vlan_type_header": r"VLAN\s+Type\s+Vlan-mode",
        "vlan_type_mode_index": r"(?P<vlan_id>\d+)\s+(?P<type>\S+)\s+(?P<mode>\S+)",
        "remote_span_header": r"Primary\s+Secondary\s+Type\s+Ports",
        "remote_span": r"(?P<primary>\d+)\s+(?P<secondary>\d+)\s+(?P<type>\S+)\s+(?P<ports>[\w\s,/-]*)",
    }

    # Identify the start indices of each section based on headers
    vlan_details_index = re.search(regex_map["vlan_details_header"], cli_output).end()
    vlan_type_mode_index = re.search(regex_map["vlan_type_mode_header"], cli_output).end()
    remote_span_index = re.search(regex_map["remote_span_header"], cli_output).end()

    # Extract section strings
    vlan_detail_string = cli_output[vlan_details_index:vlan_type_mode_index]
    vlan_type_mode_string = cli_output[vlan_type_mode_index:remote_span_index]
    remote_span_string = cli_output[remote_span_index:]

    vlan_data = {}

    # Variable to hold current VLAN ID
    current_vlan = None

    # Parse VLAN details with ports mapping
    for line in vlan_detail_string.splitlines():
        match = re.search(regex_map["vlan_details"], line)
        if match:
            current_vlan = match.group("vlan_id")
            ports_list = match.group("ports").strip().split(", ")
            # Ensure that empty strings are not included in the Ports list
            ports_list = [port for port in ports_list if port]
            vlan_data[current_vlan] = {
                "VLAN Name": match.group("vlan_name"),
                "Status": match.group("status"),
                "Ports": ports_list,
            }
        elif current_vlan and line.strip():
            # Continuation lines for the ports of a VLAN
            ports = line.strip().split(", ")
            vlan_data[current_vlan]["Ports"].extend(ports)

    # Parse VLAN type and mode
    for line in vlan_type_mode_string.splitlines():
        match = re.search(regex_map["vlan_type_mode"], line)
        if match:
            vlan_id = match.group("vlan_id")
            if vlan_id in vlan_data:  # Ensure the VLAN ID exists in the data
                vlan_data[vlan_id].update(
                    {"Type": match.group("type"), "Mode": match.group("mode")}
                )

    # Parse Remote SPAN VLANs
    for line in remote_span_string.splitlines():
        match = re.search(regex_map["remote_span"], line)
        if match:
            primary = match.group("primary")
            # If primary VLAN ID exists in the data, update its attributes
            if primary in vlan_data:
                vlan_data[primary].update(
                    {
                        "Secondary": match.group("secondary"),
                        "RS_Type": match.group("type"),
                        "RS_Ports": match.group("ports").strip().split(", "),
                    }
                )

    return vlan_data


def parse_nxos_show_interface_status(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface status command."""
    
    logging.info('Parsing nxos "show interface status"...')

    interfaces = {}
    try:
        regex_map = {
            "interface_status_header": r"Port\s+Name\s+Status\s+Vlan\s+Duplex\s+Speed\s+Type",
            "separator_line": r"^-+"
        }

        
        lines = cli_output.split("\n")

        # Identify header and column start indices
        header_line = None
        for line in lines:
            if re.search(regex_map["interface_status_header"], line):
                header_line = line
                break

        if not header_line:
            logging.error("Header line not found!")
            return {"msg":"Header line not found!"}

        col_starts = {
            "Port": header_line.index("Port"),
            "Name": header_line.index("Name"),
            "Status": header_line.index("Status"),
            "Vlan": header_line.index("Vlan"),
            "Duplex": header_line.index("Duplex"),
            "Speed": header_line.index("Speed"),
            "Type": header_line.index("Type")
        }

        for line in lines:
            if re.search(regex_map["separator_line"], line):
                continue
            port = line[col_starts["Port"]:col_starts["Name"]].strip()
            name = line[col_starts["Name"]:col_starts["Status"]].strip()
            status = line[col_starts["Status"]:col_starts["Vlan"]].strip()
            vlan = line[col_starts["Vlan"]:col_starts["Duplex"]].strip()
            duplex = line[col_starts["Duplex"]:col_starts["Speed"]].strip()
            speed = line[col_starts["Speed"]:col_starts["Type"]].strip()
            int_type = line[col_starts["Type"]:].strip()

            if port:  # If port value exists, then add to the dictionary
                interfaces[port] = {
                    "name": name,
                    "status": status,
                    "vlan": vlan,
                    "duplex": duplex,
                    "speed": speed,
                    "type": int_type,
                }
                
    except Exception as e:
        interfaces["msg"] = f"{e}"

    return interfaces


def parse_nxos_show_ip_route_vrf_all(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip route vrf all command."""

    return {"msg": "Not supported yet"}
    logging.info('Parsing "show ip route vrf all"...')

    regex_map = {
        "route": re.compile(
            r"^([\d.]+/\d+),\s+(\d+)\s+ucast next-hops, (\d+)\s+mcast next-hops"
        ),
        "next_hop": re.compile(
            r"^\s+\*\s*via\s+(\S+),\s+\[([\d/]+)\],\s+(\d+:\d+:\d+),\s+(\w+),\s+(\w+)"
        ),
    }

    routes = {}
    lines = cli_output.split("\n")

    current_route = None
    for line in lines:
        route_match = regex_map["route"].search(line)
        if route_match:
            current_route = route_match.group(1)
            routes[current_route] = {
                "ucast_next_hops": int(route_match.group(2)),
                "mcast_next_hops": int(route_match.group(3)),
                "next_hops": [],
            }
        elif current_route:
            next_hop_match = regex_map["next_hop"].search(line)
            if next_hop_match:
                next_hop = {
                    "via": next_hop_match.group(1),
                    "preference_metric": next_hop_match.group(2),
                    "age": next_hop_match.group(3),
                    "source": next_hop_match.group(4),
                    "type": next_hop_match.group(5),
                }
                routes[current_route]["next_hops"].append(next_hop)

    return {"routes": routes}


def parse_nxos_show_system_resources(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show system resources command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_spanning_tree(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show spanning tree command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_vpc(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show vpc command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_vpc_role(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show vpc role command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_cons_para_global(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show cons para global command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_port_channel_summary(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show port channel summary command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_cdp_neighbor(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show cdp neighbor command."""

    logging.info('Parsing nxos "show cdp neighbors"...')

    try:
        # Extract capability codes and their full names using regex
        capability_mapping = {}
        capability_pattern = re.compile(r"([A-Za-z]) - ([ \w-]+)")
        matches = capability_pattern.findall(cli_output)
        for code, name in matches:
            capability_mapping[code] = name.strip()

        regex_map = {
            "only_nei_info": r"\s+(?P<local_int>[/\w ]+?)\s+(?P<holdtime>\d+)\s+(?P<capability>[A-Z ]+)\s+(?P<platform>\S+)\s+(?P<port_id>[/\w ]+)",
            "only_device_id": r"^(?P<device_id>\S+)$",
            "full_info": r"^(?P<device_id>\S+)\s+(?P<local_int>[/\w ]+?)\s+(?P<holdtime>\d+)\s+(?P<capability>[A-Z ]+)\s+(?P<platform>\S+)\s+(?P<port_id>[/\w ]+)"
        }

        neighbors = {}
        lines = cli_output.split("\n")
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            lines[i] = lines[i].rstrip()
            match = re.search(regex_map["full_info"], lines[i])
            if match:
                capability_list = [capability_mapping[code] for code in match.group("capability").strip().split() if code in capability_mapping] 
                capability = ", ".join(capability_list)
                neighbors[match.group("device_id")] = {
                    "local_interface": match.group("local_int").strip(),
                    "holdtime": match.group("holdtime"),
                    "capability": capability,
                    "platform": match.group("platform"),
                    "port_id": match.group("port_id")
                }
            else:
                match_device_id = re.search(regex_map["only_device_id"], lines[i])
                if match_device_id and i + 1 < len(lines):
                    i = i + 1
                    lines[i] = lines[i].rstrip()
                    match_info = re.search(regex_map["only_nei_info"], lines[i])
                    if match_info:
                        capability_list = [capability_mapping[code] for code in match_info.group("capability").strip().split() if code in capability_mapping] 
                        capability = ", ".join(capability_list)
                        neighbors[match_device_id.group("device_id")] = {
                            "local_interface": match_info.group("local_int").strip(),
                            "holdtime": match_info.group("holdtime"),
                            "capability": capability,
                            "platform": match_info.group("platform"),
                            "port_id": match_info.group("port_id")
                        }
            i = i + 1

    except Exception as e:
        return {"error": f"{e}"}

    return neighbors


def parse_nxos_show_forwarding_adjacency(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show forwarding adjacency command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_ip_arp(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip arp command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_mac_address_table(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show mac address table command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_ip_bgp_summary(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip bgp summary command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_ip_ospf_neighbor(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip ospf neighbor command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_ip_pim_neighbor(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip pim neighbor command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_hsrp(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show hsrp command."""

    return {"msg": "Not supported yet"}


def parse_nxos_show_policy_map_int_ctrl_plane(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show policy map int ctrl plane command."""

    return {"msg": "Not supported yet"}


# New IOS parsers (only definition and arguments)
def parse_ios_show_version(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show version command."""

    logging.info('Parsing ios "show version"...')
    try:
        # Define regular expressions for the attributes
        regex_map = {
            "version": r"Cisco IOS Software, (.+?), RELEASE SOFTWARE",
            "rom": r"ROM: (.+?), RELEASE SOFTWARE",
            "system_image_file": r"System image file is: (.+)",
            "platform": r"(Cisco.+Intel.+)"
        }

        result = {}
        for key, regex in regex_map.items():
            match = re.search(regex, cli_output, re.MULTILINE)
            if match:
                result[key] = match.group(1)

    except Exception as e:
        return {"error": f"{e}"}
    
    return result


def parse_ios_show_interface(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show interface command."""

    logging.info('Parsing ios "show interface"...')
    try:
        # Define regular expressions for the attributes
        regex_map = {
            "interface": r"(.+?) is (up|down), line protocol is (.+?) (.+?)",
            "hardware_address": r"Hardware is .+?address is (.+?) \(bia",
            "internet_address": r"Internet address is (.+)",
            "description": r"Description: (.+)",
            "mtu": r"MTU (.+?) bytes",
            "bandwidth": r"BW (.+?) Kbit",
            "delay": r"DLY (.+?) usec",
            "reliability": r"reliability (.+?),",
            "txload": r"txload (.+?),",
            "rxload": r"rxload (.+?)",
            "encapsulation": r"Encapsulation (.+)",
            "eth_mode": r"Port mode is (.+)",
            "duplex": r"(\w+-duplex)",
            "speed": r", (\d+ Gb/s),",
            "media": r"media type is (.+)",
        }

        result = {"interfaces": {}}
        current_interface = ""

        for line in cli_output.split("\n"):
            if not line.strip():
                continue
            if "is up" in line or "is down" in line:
                match = re.search(regex_map["interface"], line)
                if match:
                    current_interface = match.group(1)
                    result["interfaces"][current_interface] = {"status": match.group(2)}
                    result["interfaces"][current_interface]["protocol_status"] = match.group(3)
                    result["interfaces"][current_interface]["physical_status"] = match.group(4)
                    continue
            for key, regex in regex_map.items():
                match = re.search(regex, line)
                if match and current_interface:
                    result["interfaces"][current_interface][key] = match.group(1)
    
    except Exception as e:
        result = {"error": f"{e}"}
    
    return result


def parse_ios_show_interface_trunk(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show interface trunk command."""

    logging.info('Parsing ios "show interface trunk"...')
    result = {}
    try:
        # Regex patterns map
        regex_map = {
            "port_details_header": r"Port\s+Mode\s+Encapsulation\s+Status\s+Native vlan",
            "port_details": r"(?P<port>\S+)\s+(?P<mode>\S)\s+(?P<encapsulation>\S)\s+(?P<status>\S+)\s+(?P<native_vlan>\d+)",
            "vlans_allowed_header": r"Port\s+Vlans allowed on trunk",
            "vlans_allowed": r"(?P<port>\S+)\s+(?P<vlans_allowed>[\d,-]+)",
            "vlans_allowed_mgmt_header": r"Port\s+Vlans allowed and active in management domain",
            "vlans_allowed_mgmt": r"(?P<port>\S+)\s+(?P<vlans_allowed_mgmt>[\d,-]+)",
            "vlans_stp_forwarding_header": r"Port\s+Vlans in spanning tree forwarding state and not pruned",
            "vlan_stp_forwarding": r"(?P<port>\S+)\s+(?P<vlans_stp>[\d,-]+)",
        }

        # Identify the start indices of each section based on headers
        port_details_index = re.search(regex_map["port_details_header"], cli_output).end()
        vlans_allowed_index = re.search(regex_map["vlans_allowed_header"], cli_output).end()
        vlans_allowed_mgmt_index = re.search(regex_map["vlans_allowed_mgmt_header"], cli_output).end()
        vlans_stp_forwarding_index = re.search(regex_map["vlans_stp_forwarding_header"], cli_output).end()

        # Extract section strings
        port_details_string = cli_output[port_details_index:vlans_allowed_index]
        vlans_allowed_string = cli_output[vlans_allowed_index:vlans_allowed_mgmt_index]
        vlans_allowed_mgmt_string = cli_output[vlans_allowed_mgmt_index:vlans_stp_forwarding_index]
        vlans_stp_forwarding_string = cli_output[vlans_stp_forwarding_index:]

        # Parse port details section
        for match in re.finditer(regex_map["port_details"], port_details_string):
            port = match.group("port")
            result[port] = {
                "mode": match.group("mode"),
                "encapsulation": match.group("encapsulation"),
                "Status": match.group("status"),
                "native_vlan": match.group("native_vlan"),
            }

        # Parse VLANs allowed section
        for match in re.finditer(regex_map["vlans_allowed"], vlans_allowed_string):
            port = match.group("port")
            if port in result:
                result[port]["vlans_allowed"] = match.group("vlans_allowed")
            else:
                result[port] = {"vlans_allowed": match.group("vlans_allowed")}

        # Parse VLANs allowed and active in management domain
        for match in re.finditer(regex_map["vlans_allowed_mgmt"], vlans_allowed_mgmt_string):
            port = match.group("port")
            if port in result:
                result[port]["vlans_allowed_mgmt"] = match.group("vlans_allowed_mgmt")
            else:
                result[port] = {"vlans_allowed_mgmt": match.group("vlans_allowed_mgmt")}

        # Parse STP Forwarding section
        for match in re.finditer(regex_map["vlan_stp_forwarding"], vlans_stp_forwarding_string):
            port = match.group("port")
            if port in result:
                result[port]["vlans_stp_forwarding"] = match.group("vlans_stp")
            else:
                result[port] = {"vlans_stp_forwarding": match.group("vlans_stp")}

        # If no attribute, assign empty string
        for port in result:
            if "mode" not in port:
                result[port]["mode"] = ""
            if "encapsulation" not in port:
                result[port]["encapsulation"] = ""
            if "Status" not in port:
                result[port]["Status"] = ""
            if "native_vlan" not in port:
                result[port]["native_vlan"] = ""
            if "vlans_allowed" not in port:
                result[port]["vlans_allowed"] = ""
            if "vlans_allowed_mgmt" not in port:
                result[port]["vlans_allowed_mgmt"] = ""
            if "vlans_stp_forwarding" not in port:
                result[port]["vlans_stp_forwarding"] = ""

    except Exception as e:
        result["error"] = f"{e}"

    return result


def parse_ios_show_vlan(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show vlan command."""

    logging.info('Parsing ios "show vlan"...')
    vlan_data = {}
    try:
        # Regex patterns map
        regex_map = {
            "vlan_details_header": r"VLAN\s+Name\s+Status\s+Ports",
            "vlan_details": r"(?P<vlan_id>\d+)\s+(?P<vlan_name>\S+)\s+(?P<status>\S+)(?P<ports>[\w\s,/-]*)",
            "vlan_more_header": r"VLAN\s+Type\s+SAID\s+MTU\s+Parent\s+RingNo\s+BridgeNo\s+Stp\s+BrdgMode\s+Trans1\s+Trans2",
            "vlan_more": r"(?P<vlan_id>\d+)\s+(?P<type>\S+)\s+(?P<said>\d+)\s+(?P<mtu>\d+)\s+(?P<parent>\S+)\s+(?P<ringno>\S+)\s+(?P<bridgeno>\S+)\s+(?P<stp>\S+)\s+(?P<brdgmode>\S+)\s+(?P<trans1>\d+)\s+(?P<trans2>\S+)",
        }

        # Identify the start indices of each section based on headers
        vlan_details_index = re.search(regex_map["vlan_details_header"], cli_output).end()
        vlan_more_index = re.search(regex_map["vlan_more_header"], cli_output).end()

        # Extract section strings
        vlan_details_string = cli_output[vlan_details_index:vlan_more_index]
        vlan_more_string = cli_output[vlan_more_index:]

        # Variable to hold current VLAN ID
        current_vlan = None

        # Parse VLAN details with ports mapping
        for line in vlan_details_string.splitlines():
            match = re.search(regex_map["vlan_details"], line)
            if match:
                current_vlan = match.group("vlan_id")
                ports_list = match.group("ports").strip().split(", ")
                # Ensure that empty strings are not included in the Ports list
                ports_list = [port for port in ports_list if port]
                vlan_data[current_vlan] = {
                    "vlan_name": match.group("vlan_name"),
                    "status": match.group("status"),
                    "ports": ports_list,
                }
            elif current_vlan and line.strip():
                # Continuation lines for the ports of a VLAN
                ports = line.strip().split(", ")
                ports = [port for port in ports if port]
                vlan_data[current_vlan]["Ports"].extend(ports)

        # Parse more info of VLAN
        for line in vlan_more_string.splitlines():
            match = re.search(regex_map["vlan_more"], line)
            if match:
                vlan_id = match.group("vlan_id")
                if vlan_id not in vlan_data:  # Ensure the VLAN ID exists in the data
                    vlan_data[vlan_id] = {}
                vlan_data[vlan_id].update(
                    {
                        "type": match.group("type"),
                        "said": match.group("said"),
                        "mtu": match.group("mtu"),
                        "parent": match.group("parent"),
                        "ringno": match.group("ringno"),
                        "bridgeno": match.group("bridgeno"),
                        "stp": match.group("stp"),
                        "brdgmode": match.group("brdgmode"),
                        "trans1": match.group("trans1"),
                        "trans2": match.group("trans2"),
                    }
                )

    except Exception as e:
        vlan_data["error"] = f"{e}"
    return vlan_data


def parse_ios_show_interface_status(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show interface status command."""

    logging.info('Parsing ios "show interface status"...')

    interfaces = {}
    try:
        regex_map = {
            "interface_status_header": r"Port\s+Name\s+Status\s+Vlan\s+Duplex\s+Speed\s+Type",
            "separator_line": r"^-+"
        }

        
        lines = cli_output.split("\n")

        # Identify header and column start indices
        header_line = None
        for line in lines:
            if re.search(regex_map["interface_status_header"], line):
                header_line = line
                break

        if not header_line:
            logging.error("Header line not found!")
            return {"msg":"Header line not found!"}

        col_starts = {
            "Port": header_line.index("Port"),
            "Name": header_line.index("Name"),
            "Status": header_line.index("Status"),
            "Vlan": header_line.index("Vlan"),
            "Duplex": header_line.index("Duplex"),
            "Speed": header_line.index("Speed"),
            "Type": header_line.index("Type")
        }

        for line in lines:
            if re.search(regex_map["separator_line"], line):
                continue
            port = line[col_starts["Port"]:col_starts["Name"]].strip()
            name = line[col_starts["Name"]:col_starts["Status"]].strip()
            status = line[col_starts["Status"]:col_starts["Vlan"]].strip()
            vlan = line[col_starts["Vlan"]:col_starts["Duplex"]].strip()
            duplex = line[col_starts["Duplex"]:col_starts["Speed"]].strip()
            speed = line[col_starts["Speed"]:col_starts["Type"]].strip()
            int_type = line[col_starts["Type"]:].strip()

            if port:  # If port value exists, then add to the dictionary
                interfaces[port] = {
                    "name": name,
                    "status": status,
                    "vlan": vlan,
                    "duplex": duplex,
                    "speed": speed,
                    "type": int_type,
                }
                
    except Exception as e:
        interfaces["errpr"] = f"{e}"

    return interfaces


def parse_ios_show_cdp_neighbors(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show cdp neighbors command."""
    
    logging.info('Parsing ios "show cdp neighbors"...')

    try:
        # Extract capability codes and their full names using regex
        capability_mapping = {}
        capability_pattern = re.compile(r"([A-Za-z]) - ([ \w-]+)")
        matches = capability_pattern.findall(cli_output)
        for code, name in matches:
            capability_mapping[code] = name.strip()

        regex_map = {
            "only_nei_info": r"\s+(?P<local_int>[/\w ]+?)\s+(?P<holdtime>\d+)\s+(?P<capability>[A-Z ]+)\s+(?P<platform>\S+)\s+(?P<port_id>[/\w ]+)",
            "only_device_id": r"^(?P<device_id>\S+)$",
            "full_info": r"^(?P<device_id>\S+)\s+(?P<local_int>[/\w ]+?)\s+(?P<holdtime>\d+)\s+(?P<capability>[A-Z ]+)\s+(?P<platform>\S+)\s+(?P<port_id>[/\w ]+)"
        }

        neighbors = {}
        lines = cli_output.split("\n")
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            lines[i] = lines[i].rstrip()
            match = re.search(regex_map["full_info"], lines[i])
            if match:
                capability_list = [capability_mapping[code] for code in match.group("capability").strip().split() if code in capability_mapping] 
                capability = ", ".join(capability_list)
                neighbors[match.group("device_id")] = {
                    "local_interface": match.group("local_int").strip(),
                    "holdtime": match.group("holdtime"),
                    "capability": capability,
                    "platform": match.group("platform"),
                    "port_id": match.group("port_id")
                }
            else:
                match_device_id = re.search(regex_map["only_device_id"], lines[i])
                if match_device_id and i + 1 < len(lines):
                    i = i + 1
                    lines[i] = lines[i].rstrip()
                    match_info = re.search(regex_map["only_nei_info"], lines[i])
                    if match_info:
                        capability_list = [capability_mapping[code] for code in match_info.group("capability").strip().split() if code in capability_mapping] 
                        capability = ", ".join(capability_list)
                        neighbors[match_device_id.group("device_id")] = {
                            "local_interface": match_info.group("local_int").strip(),
                            "holdtime": match_info.group("holdtime"),
                            "capability": capability,
                            "platform": match_info.group("platform"),
                            "port_id": match_info.group("port_id")
                        }
            i = i + 1

    except Exception as e:
        return {"error": f"{e}"}

    return neighbors


def parse_ios_show_ip_arp(cli_output: str) -> list:
    """Parses the IOS CLI output of the show ip arp command."""
    
    logging.info('Parsing ios "show ip arp"...')

    try:
        ip_arp_list = []
        # Define regular expressions for the attributes
        regex_map = {
            "ip_arp_details": r"(?P<protocol>\S+)\s+(?P<address>\d+\.\d+\.\d+\.\d+)\s+(?P<age>\S+)\s+(?P<hardware_address>\S+)\s+(?P<type>\S+)\s+(?P<interface>\S+)",
        }

        lines = cli_output.split("\n")

        for line in lines:
            match = re.search(regex_map["ip_arp_details"], line)
            if match:
                ip_arp_list.append({
                    "protocol": match.group("protocol"),
                    "address": match.group("address"),
                    "age": match.group("age"),
                    "hardware_address": match.group("hardware_address"),
                    "type": match.group("type"),
                    "interface": match.group("interface"),
                    })
                
    except Exception as e:
        return [{"error": f"{e}"}]
    
    return ip_arp_list


def parse_ios_show_mac_address_table(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show mac address-table command."""

    logging.info('Parsing ios "show mac address-table"...')

    try:
        mac_table = {}
        # Define regular expressions for the attributes
        regex_map = {
            "mac_details": r"(?P<vlan>\d+)\s+(?P<mac>\S+)\s+(?P<type>\S+)\s+(?P<learn>\S+)\s+(?P<age>\S+)\s+(?P<ports>[\w\s,/-]*)",
        }

        lines = cli_output.split("\n")

        for line in lines:
            match = re.search(regex_map["mac_details"], line)
            if match:
                mac = match.group("mac")
                mac_table[mac] = {
                    "vlan": match.group("vlan"),
                    "type": match.group("type"),
                    "learn": match.group("learn"),
                    "age": match.group("age"),
                    "ports": match.group("ports").strip(),
                    }
                
    except Exception as e:
        return {"error": f"{e}"}
    
    return mac_table


def parse_ios_show_ip_route(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show ip route command."""

    logging.info('Parsing ios "show ip route"...')

    try:
        codes_mapping = {}
        codes_pattern = re.compile(r"([\w*+%]+) - ([-\w\ ]+)")
        matches = codes_pattern.findall(cli_output)
        for code, name in matches:
            codes_mapping[code] = name.strip()

        route_pattern = re.compile(
                r"^(?P<codes>[\S\s]+?)\s+(?P<prefix>\d+\.\d+\.\d+\.\d+/\d+)"
                r"(?:\s+\[(?P<preference>\d+)/(?P<metric>\d+)\])?"
                r"\s+(?:via\s+(?P<next_hop>[\d\.]+)|(?P<directly_connected>is directly connected)),?"
                r"(?:\s+.*,)?\s+(?P<interface>\S+)"
            )

        routes = {}
        for line in cli_output.split("\n"):
            match = route_pattern.search(line)
            if match:
                prefix = match.group("prefix")
                codes_list = []
                codes_str = match.group("codes").strip()
                for code in codes_str.split():
                    code = code.strip()
                    if code:
                        if "*" in code:
                            codes_list.append(codes_mapping.get("*", "*"))
                            code = code.replace("*", "")
                        codes_list.append(codes_mapping.get(code, code))
                next_hop = match.group("next_hop") or match.group("directly_connected")

                routes[prefix] = {
                    "codes": codes_list,
                    "preference": match.group("preference") or "",
                    "metric": match.group("metric") or "",
                    "next_hop": next_hop,
                    "interface": match.group("interface")
                }
    
    except Exception as e:
        return {"error": f"{e}"}
    
    return routes


def parse_ios_show_run_interface(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show run interface command."""

    logging.info('Parsing ios "show run interface"...')
    interfaces = {}
    try:
    # Regular expressions for each attribute
        regex_map = {
            "interface": re.compile(r"^interface (\S+)"),
            "description": re.compile(r"^ description (.+)"),
            "switchport_mode": re.compile(r"^ switchport mode (\S+)"),
            "switchport_trunk_allowed_vlan": re.compile(
                r"^ switch port trunk allowed vlan (.+)"
            ),
            "switchport_trunk_allowed_vlan_add": re.compile(
                r"^ switchport trunk allowed vlan add (.+)"
            ),
            "no_switchport": re.compile(r"^ no switchport"),
            "no_ip_address": re.compile(r"^ no IP address"),
            "switch_virtual_link": re.compile(r"^ switch virtual link (\d+)"),
            "login_event_link_status": re.compile(r"^ login event link-status"),
            "channel_group": re.compile(r"^ channel-group (\d+) mode (\S+)"),
        }

        current_interface = ""

        # Split the output into lines and loop through each line
        for line in cli_output.split("\n"):
            interface_match = regex_map["interface"].match(line)
            if interface_match:
                current_interface = interface_match.group(1)
                interfaces[current_interface] = {}
                continue

            # If inside an interface configuration section, search for attributes
            if current_interface:
                for attr, regex in regex_map.items():
                    if attr == "interface":
                        continue
                    match = regex.match(line)
                    if match:
                        if attr in [
                            "switchport_trunk_allowed_vlan",
                            "switchport_trunk_allowed_vlan_add",
                        ]:
                            # Add the allowed vlans to the list
                            vlans = match.group(1)
                            if "allowed_vlans" in interfaces[current_interface]:
                                interfaces[current_interface]["allowed_vlans"] += (
                                    "," + vlans
                                )
                            else:
                                interfaces[current_interface]["allowed_vlans"] = vlans
                        else:
                            interfaces[current_interface][attr] = match.group(1)
    except Exception as e:
        interfaces["msg"] = e
    return interfaces


def extract_txt_cmd_output(text: str, commands: list) -> dict:
    """Extract the output of each show commands from the text file."""

    output = {}
    positions = []

    # find the positions of each command in the text
    for cmd in commands:
        pos = text.find(cmd)
        if pos != -1:
            positions.append((pos, cmd))

    # sort the positions to maintain the order in text
    positions.sort()

    # extract the output of each command
    for i in range(len(positions)):
        start = positions[i][0] + len(positions[i][1])  # start of the output
        end = (
            positions[i + 1][0] if i + 1 < len(positions) else len(text)
        )  # end of the output
        cmd_output = text[start:end].strip()  # extract the output
        output[positions[i][1]] = cmd_output

    return output


async def parse_text_file(device: dict, command_parsers: dict) -> dict:
    """Parses the text file that contain show commands and their output."""

    filename = device["file"]
    logging.info(f'Extracting show commands from {filename} txt file...')
    async with aiofiles.open(filename, "r") as file:
        content = await file.read()

    cmd_output = extract_txt_cmd_output(content, command_parsers.keys())
    
    outputs = {}
    parse_output_tasks = []
    for cmd, output in cmd_output.items():
        if cmd in device["commands"]: 
            parse_output_tasks.append(parse_output(cmd, output, device["cli_output_format"], command_parsers.get(cmd)))

    parsed_outputs = await asyncio.gather(*parse_output_tasks)
    for cmd, parsed_output in parsed_outputs:
        outputs[cmd] = parsed_output

    return {filename: outputs}


# Function to recursively remove TABLE_ and ROW_ prefixes
async def remove_prefixes(obj: dict) -> dict:
    """Remove TABLE_ and ROW_ prefix from show commands output in JSON format"""

    if isinstance(obj, dict):    
        new_obj = {}
        for k, v in obj.items():
            new_key = k
            if k.startswith("TABLE_"):
                new_key = k.replace("TABLE_", "", 1)
            elif k.startswith("ROW_"):
                new_key = k.replace("ROW_", "", 1)
            
            new_obj[new_key] = await remove_prefixes(v)
        return new_obj
    elif isinstance(obj, list):
        return [await remove_prefixes(item) for item in obj]
    else:
        return obj

    
async def parse_table(table: dict) -> dict:
    """Recursively parses the tables in show commands output in JSON format."""

    result = {}
    for table_key, table_value in table.items():
        if not table_key.startswith("TABLE_"):
            result[table_key] = table_value
            continue
        result_key = table_key.split("_",1)[1]
        # result_key = table_key
        if isinstance(table_value, dict):
            for row_key, row_value in table_value.items():
                if isinstance(row_value, list):
                    for item in row_value:
                        temps = []
                        keys_to_delete = []
                        for item_key, item_value in item.items():
                            if item_key.startswith("TABLE_"):
                                keys_to_delete.append(item_key)
                                data = await parse_table({item_key: item_value})
                                temps.append(data)
                        for key in keys_to_delete:
                            del item[key]
                        for temp in temps:
                            item.update(temp)
                elif isinstance(row_value, dict):
                    temps = []
                    keys_to_delete = []
                    for key, value in row_value.items():
                        if key.startswith("TABLE_"): 
                            keys_to_delete.append(key)
                            data = await parse_table({key: value})
                            temps.append(data)
                    for key in keys_to_delete:
                        del row_value[key]
                    for temp in temps:
                        row_value.update(temp)
            result[result_key] = row_value
        elif isinstance(table_value, list):
            result[result_key] = []
            for row in table_value:
                for row_key, row_value in row.items():
                    if isinstance(row_value, dict):
                        temps = []
                        keys_to_delete = []
                        for key, value in row_value.items():
                            if key.startswith("TABLE_"): 
                                keys_to_delete.append(key)
                                data = await parse_table({key: value})
                                temps.append(data)
                        for key in keys_to_delete:
                            del row_value[key]
                        for temp in temps:
                            row_value.update(temp)
                    elif isinstance(row_value, list):
                        for item in row_value:
                            temps = []
                            keys_to_delete = []
                            for item_key, item_value in item.items():
                                if item_key.startswith("TABLE_"):
                                    keys_to_delete.append(item_key)
                                    data = await parse_table({item_key: item_value})
                                    temps.append(data)
                            for key in keys_to_delete:
                                del item[key]
                            for temp in temps:
                                item.update(temp)
                    result[result_key].append(row_value)
    return result


async def zip_tables(data: dict) -> dict:
    """Zip tables at the same level in hierarchy."""

    # table_keys = [key for key in data if key.startswith("TABLE_")]
    table_lists = [data[key] for key in data.keys()]

    zipped_dicts = []
    for dicts in zip_longest(*table_lists, fillvalue={}):
        merged_dict = {}
        for key, d in zip(data.keys(), dicts):
            # Concatenate the data key with each item key
            concatenated_dict = {f"{key}_{k}": v for k, v in d.items()}
            merged_dict.update(concatenated_dict)
        zipped_dicts.append(merged_dict)

    return zipped_dicts


async def parse_output(cmd: str, output: str or dict, format: str, parser: Callable[[dict], dict]) -> (str, dict):
    """Parses the output of specifc show command."""

    logging.info(f'Parsing the output of {cmd}...')

    try:

        if format == "json":
            if cmd in ["show interface trunk", "show vlan"]:
                return cmd, await zip_tables(await parse_table(output))
            else:
                return cmd, await parse_table(output)
        elif format == "cli-text":
            return cmd, parser(output)
        
    except Exception as e:
        return cmd, {"msg": f"Failed to parse the output from {cmd}","error": f"{e}"}
    

async def parse_device(device: dict, command_parsers: dict) -> dict:
    """Establish SSH connection to device, send commands, and parse their output."""

    host = device["address"]
    if "password" not in device:
        device["password"] = getpass.getpass(prompt=f"Device {host}\nEnter the password: ")

    cmd_out = {}
    try:
        if device["os_type"] == "ios":
            conn = AsyncIOSXEDriver(
                host=device["address"],
                auth_username=device["username"],
                auth_password=device["password"],
                auth_strict_key=False,
                transport="asyncssh",
            )
            await conn.open()
        elif device["os_type"] == "nxos":
            conn = AsyncNXOSDriver(
                host=device["address"],
                auth_username=device["username"],
                auth_password=device["password"],
                auth_strict_key=False,
                transport="asyncssh",
            )
            await conn.open()
        else:
            raise ValueError(f"Unsupported OS type: {device['os_type']}")

        hostname_response = await conn.send_command("show hostname")
        host = hostname_response.result
        result = {host: {}}
        cli_output_format = device.get("cli_output_format", "json")
        if device['os_type'] == 'ios' and cli_output_format == 'json':
            raise ValueError(f"Cisco IOS does not support JSON output format")
        
        parse_output_tasks = []
        for cmd in device["commands"]:
            response = await conn.send_command(cmd if format == "cli-text" else f"{cmd} | json")
            try:
                json_resp = json.loads(response.result)
                parse_output_tasks.append(parse_output(cmd, json_resp, cli_output_format, command_parsers.get(cmd)))
            except json.JSONDecodeError:
                logging.error(f'Command {cmd} CLI output is not in JSON format.')
                result[host].update({cmd: {"output": response.result, "msg": "The CLI output is not in JSON format."}})
            
        parsed_outputs = await asyncio.gather(*parse_output_tasks)
        for cmd, parsed_output in parsed_outputs:
            cmd_out[cmd] = parsed_output

        # Save outputs to a file
        for cmd in device["commands"]:
            response = await conn.send_command(cmd)
            logging.info(f'Saving the CLI output of {cmd}...')
            with open(f"{host}.txt", "a") as file:
                file.write(f"{cmd}\n")
                file.write(f"{response.result}\n")
    
        await conn.close()

    except Exception as exc:
        logging.error(f"Error encountered during establishing SSH and parsing for {device['address']}: {exc}")
        return {host: {"error": f"Failed to parse device: {exc}"}}
    
    result[host].update(cmd_out)
    logging.info(f'Finish parsing {host}...')
    return result

async def write_json(data: dict):
    """Asynchronously write data to a JSON file."""

    for host, _ in data.items():
        filename = f"{host}.json"

    async with aiofiles.open(f"{filename}", "w") as file:
        await file.write(json.dumps(data, indent=4))


async def load_configuration(file_path: str) -> dict:
    """Load device configuration from a YAML file."""

    nxos_cmds_default = [
            "show version",
            "show interface",
            "show interface trunk",
            "show vlan",
            "show interface status",
            "show ip route vrf all",
            "show system resources",
            "show spanning-tree",
            "show vpc",
            "show vpc role",
            "show vpc consistency-parameters global",
            "show port-channel summary",
            "show cdp neighbor",
            "show forwarding adjacency",
            "show ip arp",
            "show mac address-table",
            "show ip bgp summary",
            "show ip ospf neighbor",
            "show ip pim neighbor",
            "show hsrp",
            "show policy-map interface control-plane"
        ]
    ios_cmds_default = [
            "show version",
            "show interface",
            "show interface trunk",
            "show vlan",
            "show interface status",
            "show cdp neighbors",
            "show ip arp",
            "show mac address-table"
            "show ip route"
        ]
    
    async with aiofiles.open(file_path, "r") as file:
        content = await file.read()
    content_dict = yaml.safe_load(content)
    if "devices" not in content_dict:
        raise ValueError(f"No 'devices' key is found in {file_path}")
    for device in content_dict["devices"]:
        if "address" not in device and "file" not in device:
            raise ValueError(f"No 'address' or 'file' key is found in {device}")
        if "username" not in device and "username" not in content_dict:
            raise ValueError(f"No 'username' key is found in {device}")
        if "username" not in device:
            device["username"] = content_dict["username"]
        if "os_type" not in device:
            device["os_type"] = content_dict.get("os_type", "nxos")
        if "cli_output_format" not in device:
            device["cli_output_format"] = content_dict.get("cli_output_format", "json")
            if device['os_type'] == 'ios' and device["cli_output_format"] == 'json':
                raise ValueError(f"Cisco IOS does not support JSON output format")
        if "commands" not in device:
            if "commands" not in content_dict:
                if device["os_type"] == "nxos":
                    device["commands"] = nxos_cmds_default
                elif device["os_type"] == "ios":
                    device["commands"] = ios_cmds_default
            else:
                device["commands"] = content_dict["commands"]
    return content_dict


async def process_device(device: dict, command_parsers: dict) -> Any:
    """Process a single device based on the provided configuration."""

    os_type = device["os_type"]

    supported_commands = command_parsers.get(os_type, {})
    for cmd in device["commands"]:
        if cmd not in supported_commands:
            raise ValueError(f"Command {cmd} is not supported in {os_type}")
    if "address" in device:
        return await parse_device(device, supported_commands)
    elif "file" in device:
        return await parse_text_file(device, supported_commands)

async def process_and_write(device: dict, command_parsers: dict):
    try:
        output = await process_device(device, command_parsers)
    except Exception as e:
        name = device["address"] if "address" in device else device["file"]
        output = {{name}:{"msg": f"Failed to process device {name}", "error": f"{e}"}}

    if not output.keys():
        logging.error(f'Found no key from parsing result of {device["host"] if "host" in device else device["file"]} ...')
    elif list(output.keys())[0]:
        logging.info(f'Writing {list(output.keys())[0]} to JSON file...')
        await write_json(output)
    return output

async def main():

    # command_parsers based on the OS type
    command_parsers = {
        "nxos": {
            "show version": parse_nxos_show_version,
            "show interface": parse_nxos_show_interface,
            "show interface trunk": parse_nxos_show_interface_trunk,
            "show vlan": parse_nxos_show_vlan,
            "show interface status": parse_nxos_show_interface_status,
            "show ip route vrf all": parse_nxos_show_ip_route_vrf_all,
            "show system resources": parse_nxos_show_system_resources,
            "show spanning-tree": parse_nxos_show_spanning_tree,
            "show vpc": parse_nxos_show_vpc,
            "show vpc role": parse_nxos_show_vpc_role,
            "show vpc consistency-parameters global": parse_nxos_show_cons_para_global,
            "show port-channel summary": parse_nxos_show_port_channel_summary,
            "show cdp neighbor": parse_nxos_show_cdp_neighbor,
            "show forwarding adjacency": parse_nxos_show_forwarding_adjacency,
            "show ip arp": parse_nxos_show_ip_arp,
            "show mac address-table": parse_nxos_show_mac_address_table,
            "show ip bgp summary": parse_nxos_show_ip_bgp_summary,
            "show ip ospf neighbor": parse_nxos_show_ip_ospf_neighbor,
            "show ip pim neighbor": parse_nxos_show_ip_pim_neighbor,
            "show hsrp": parse_nxos_show_hsrp,
            "show policy-map interface control-plane": parse_nxos_show_policy_map_int_ctrl_plane
        },
        "ios": {
            "show version": parse_ios_show_version,
            "show interface": parse_ios_show_interface,
            "show interface trunk": parse_ios_show_interface_trunk,
            "show vlan": parse_ios_show_vlan,
            "show interface status": parse_ios_show_interface_status,
            "show cdp neighbors": parse_ios_show_cdp_neighbors,
            "show ip arp": parse_ios_show_ip_arp,
            "show mac address-table": parse_ios_show_mac_address_table,
            "show ip route": parse_ios_show_ip_route
        },
    }

    config = await load_configuration("/Users/duyhoan/Documents/GitHub-Cisco/Small Scripts/net-cmd-parser/devices-config.yaml")
    tasks = []
    if "devices" in config:
        for device in config["devices"]:
            tasks.append(process_and_write(device, command_parsers))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    outputs = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Error encountered during task: {result}")
        else:
            outputs.append(result)
    # await write_list_json(outputs)
    return outputs


# Call the async main function
if __name__ == "__main__":
    outputs = asyncio.run(main())
    