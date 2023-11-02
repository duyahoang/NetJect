# flake8: noqa E501
import logging
import re


def parse_ios_show_interface_trunk(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show interface trunk command."""

    logging.info('Parsing ios "show interface trunk"...')
    result = {}
    try:
        # Regex patterns map
        regex_map = {
            "port_details_header": r"Port\s+Mode\s+Encapsulation\s+Status\s+Native vlan",
            "port_details": r"(?P<port>\S+)\s+(?P<mode>\S+)\s+(?P<encapsulation>\S+)\s+(?P<status>\S+)\s+(?P<native_vlan>\d+)",
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
                "status": match.group("status"),
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
        attributes = ["mode","encapsulation","status","native_vlan","vlans_allowed","vlans_allowed_mgmt","vlans_stp_forwarding"]
        for attr in attributes:
            for interface, values in result.items():
                if attr not in values:
                    result[interface][attr] = ""

    except Exception as e:
        result["error"] = f"{e}"

    return result
