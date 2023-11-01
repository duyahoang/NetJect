# flake8: noqa E501
import logging
import re


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
        
        attributes = ["vlan_name","status","ports","type","said","mtu","parent","ringno","bridgeno","stp","brdgmode","trans1","trans2"]
        for attr in attributes:
            for vlan, values in vlan_data.items():
                if attr not in values:
                    vlan_data[vlan][attr] = ""
        

    except Exception as e:
        vlan_data["error"] = f"{e}"
    return vlan_data