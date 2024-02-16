# flake8: noqa E501
import logging
import re


def parse_nxos_show_ip_route_vrf_all(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip route vrf all command."""

    logging.info('Parsing "show ip route vrf all"...')
    try:
        # Regex pattern to match VRF names
        vrf_pattern = r"IP Route Table for VRF \"(.*?)\""
        # Regex pattern to match route details
        route_pattern = (
            r"(\S+),\s+ubest/mbest:\s+(\d+)/(\d+)(,\s+attached)?\n"
            r"(?:\s+\*via\s+(\S+),\s+(\S+),\s+\[(\d+)/(\d+)\],\s+(\S+),\s+(\S+))"
        )
        # Find all VRF sections
        vrf_sections = re.split(vrf_pattern, cli_output)[1:]
        
        # Iterate over VRF sections and parse routes
        route_map = {}
        for i in range(0, len(vrf_sections), 2):
            vrf_name = vrf_sections[i]
            routes = vrf_sections[i + 1]
            route_entries = re.findall(route_pattern, routes)
            
            # Map the regex groups to meaningful route properties, making the network the key
            route_map[vrf_name] = {
                match[0]: {
                    "ubest": match[1],
                    "mbest": match[2],
                    "attached": match[3] != '',
                    "next_hop": match[4],
                    "interface": match[5],
                    "preference": match[6],
                    "metric": match[7],
                    "age": match[8],
                    "route_type": match[9]
                } for match in route_entries
            }

    except Exception as e:
        logging.error(f"An error occurred while parsing: {e}")
        return {"error": f"{e}"}
        
    return route_map
