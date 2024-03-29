# flake8: noqa E501
import logging
import re


def parse_nxos_show_vlan(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show vlan command."""

    logging.info('Parsing nxos "show vlan"...')
    try:
        # Regex patterns map
        regex_map = {
            "vlan_details_header": r"VLAN\s+Name\s+Status\s+Ports",
            "vlan_details": r"(?P<vlan_id>\d+)\s+(?P<vlan_name>\S+)\s+(?P<status>\S+)(?P<ports>[\w\s,/-]*)",
            "vlan_type_header": r"VLAN\s+Type\s+Vlan-mode",
            "vlan_type_mode": r"(?P<vlan_id>\d+)\s+(?P<type>\S+)\s+(?P<mode>\S+)",
            "remote_span_header": r"Primary\s+Secondary\s+Type\s+Ports",
            "remote_span": r"(?P<primary>\d+)\s+(?P<secondary>\d+)\s+(?P<type>\S+)\s+(?P<ports>[\w\s,/-]*)",
        }

        # Identify the start indices of each section based on headers
        vlan_details_index = re.search(regex_map["vlan_details_header"], cli_output).end()
        vlan_type_mode_index = re.search(regex_map["vlan_type_header"], cli_output).end()
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
                    "vlan_name": match.group("vlan_name"),
                    "status": match.group("status"),
                    "ports": ports_list,
                }
            elif current_vlan and line.strip():
                # Continuation lines for the ports of a VLAN
                ports = line.strip().split(", ")
                vlan_data[current_vlan]["ports"].extend(ports)

        # Parse VLAN type and mode
        for line in vlan_type_mode_string.splitlines():
            match = re.search(regex_map["vlan_type_mode"], line)
            if match:
                vlan_id = match.group("vlan_id")
                if vlan_id not in vlan_data:  # Ensure the VLAN ID exists in the data
                    vlan_data[vlan_id] = {}
                vlan_data[vlan_id].update(
                    {"type": match.group("type"), "mode": match.group("mode")}
                )

        # Parse Remote SPAN VLANs
        for line in remote_span_string.splitlines():
            match = re.search(regex_map["remote_span"], line)
            if match:
                primary = match.group("primary")
                # If primary VLAN ID exists in the data, update its attributes
                if primary not in vlan_data:
                    vlan_data[primary] = {}
                vlan_data[primary].update(
                    {
                        "secondary": match.group("secondary"),
                        "rs_type": match.group("type"),
                        "rs_ports": match.group("ports").strip().split(", "),
                    }
                )
        
        attributes = ["vlan_name","status","ports","type","mode","primary","secondary","rs_type","rs_ports"]
        for attr in attributes:
            for vlan, values in vlan_data.items():
                if attr not in values:
                    vlan_data[vlan][attr] = ""

    except Exception as e:
        return {"error": f"{e}"}

    return vlan_data