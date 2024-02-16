# flake8: noqa E501
import logging
import re


def parse_nxos_show_interface_trunk(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface trunk command."""

    logging.info('Parsing nxos "show interface trunk"...')

    result = {}

    try:

        # Regex patterns map
        regex_map = {
            "port_details_header": r"Port\s+Native\s+Status\s+Port",
            "port_details": r"(?P<port>[\w/]+)\s+(?P<native_vlan>\d+)\s+(?P<status>\S+(?:-\S+)?)\s+(?P<port_channel>\S+)",
            "vlans_allowed_header": r"Port\s+Vlans Allowed on Trunk",
            "vlans_allowed": r"(?P<port>[\w/]+)\s+(?P<vlans_allowed>[,\w-]+)",
            "vlan_err_disabled_header": r"Port\s+Vlans Err-disabled on Trunk",
            "vlan_err_disabled": r"(?P<port>[\w/]+)\s+(?P<vlan_err_disabled>[,\w-]+)",
            "stp_forwarding_header": r"Port\s+STP Forwarding",
            "stp_forwarding": r"(?P<port>[\w/]+)\s+(?P<stp_forwarding>[,\w-]+)",
            "stp_not_pruned_header": r"Port\s+Vlans in spanning tree forwarding state and not pruned",
            "stp_not_pruned": r"(?P<port>[\w/]+)\s+(?P<stp_not_pruned>[,\w-]+)",
            "fabric_path_header": r"Port\s+Vlans Forwarding on FabricPath",
            "fabric_path": r"(?P<port>[\w/]+)\s+(?P<fabric_path>[,\w-]+)",
        }

        # Identify the start indices of each section based on headers
        port_details_index = re.search(regex_map["port_details_header"], cli_output).end()
        vlans_allowed_start_index = re.search(regex_map["vlans_allowed_header"], cli_output).start()
        vlans_allowed_index = re.search(regex_map["vlans_allowed_header"], cli_output).end()
        vlan_err_disabled_start_index = re.search(regex_map["vlan_err_disabled_header"], cli_output).start()
        vlan_err_disabled_index = re.search(regex_map["vlan_err_disabled_header"], cli_output).end()
        stp_forwarding_start_index = re.search(regex_map["stp_forwarding_header"], cli_output).start()
        stp_forwarding_index = re.search(regex_map["stp_forwarding_header"], cli_output).end()
        stp_not_pruned_start_index = re.search(regex_map["stp_not_pruned_header"], cli_output).start()
        stp_not_pruned_index = re.search(regex_map["stp_not_pruned_header"], cli_output).end()
        fabric_path_start_index = re.search(regex_map["fabric_path_header"], cli_output).start()
        fabric_path_index = re.search(regex_map["fabric_path_header"], cli_output).end()

        # Extract section strings
        port_details_string = cli_output[port_details_index:vlans_allowed_start_index]
        vlans_allowed_string = cli_output[vlans_allowed_index:vlan_err_disabled_start_index]
        vlan_err_disabled_string = cli_output[vlan_err_disabled_index:stp_forwarding_start_index]
        stp_forwarding_string = cli_output[stp_forwarding_index:stp_not_pruned_start_index]
        stp_not_pruned_string = cli_output[stp_not_pruned_index:fabric_path_start_index]
        fabric_path_string = cli_output[fabric_path_index:]
        

        # Parse port details section
        for match in re.finditer(regex_map["port_details"], port_details_string):
            port = match.group("port")
            result[port] = {
                "native_vlan": match.group("native_vlan"),
                "status": match.group("status"),
                "port_channel": match.group("port_channel"),
            }

        # Parse VLANs allowed section
        for match in re.finditer(regex_map["vlans_allowed"], vlans_allowed_string):
            port = match.group("port")
            if port in result:
                result[port]["vlans_allowed"] = match.group("vlans_allowed")
            else:
                result[port] = {"vlans_allowed": match.group("vlans_allowed")}

        # Parse vlan_err_disabled section
        for match in re.finditer(regex_map["vlan_err_disabled"], vlan_err_disabled_string):
            port = match.group("port")
            if port in result:
                result[port]["vlan_err_disabled"] = match.group("vlan_err_disabled")
            else:
                result[port] = {"vlan_err_disabled": match.group("vlan_err_disabled")}

        # Parse STP Forwarding section
        for match in re.finditer(regex_map["stp_forwarding"], stp_forwarding_string):
            port = match.group("port")
            if port in result:
                result[port]["stp_forwarding"] = match.group("stp_forwarding")
            else:
                result[port] = {"stp_forwarding": match.group("stp_forwarding")}

        # Parse stp_not_pruned_string section
        for match in re.finditer(regex_map["stp_not_pruned"], stp_not_pruned_string):
            port = match.group("port")
            if port in result:
                result[port]["stp_not_pruned"] = match.group("stp_not_pruned")
            else:
                result[port] = {"stp_not_pruned": match.group("stp_not_pruned")}

        # Parse fabric_path_string section
        for match in re.finditer(regex_map["fabric_path"], fabric_path_string):
            port = match.group("port")
            if port in result:
                result[port]["fabric_path"] = match.group("fabric_path")
            else:
                result[port] = {"fabric_path": match.group("fabric_path")}
        

        # If no attribute, assign empty string
        attributes = ["status","native_vlan","port_channel","vlans_allowed","vlan_err_disabled","stp_forwarding","stp_not_pruned","fabric_path"]
        for attr in attributes:
            for interface, values in result.items():
                if attr not in values:
                    result[interface][attr] = ""

    except Exception as e:
        result["error"] = f"{e}"

    return result