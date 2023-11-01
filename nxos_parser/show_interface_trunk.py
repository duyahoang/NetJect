# flake8: noqa E501
import logging
import re


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