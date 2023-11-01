# flake8: noqa E501
import logging
import re


def parse_nxos_show_cdp_neighbor(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show cdp neighbor command."""

    logging.info('Parsing nxos "show cdp neighbor"...')

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