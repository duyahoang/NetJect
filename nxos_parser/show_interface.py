# flake8: noqa E501
import logging
import re


def parse_nxos_show_interface(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface command."""

    logging.info('Parsing nxos "show interface"...')

    try:
        # Define regular expressions for the attributes
        regex_map = {
            "interface": r"(.+?) is (up|down)",
            "port_channel": r"Belongs to (\w+)",
            "hardware_address": r"Hardware:.+?address: (.+?) \(bia",
            "description": r"Description: (.+)",
            "mtu": r"MTU (.+?) bytes",
            "encapsulation": r"Encapsulation (.+)",
            "port_mode": r"Port mode is (.+)",
            "duplex": r"(\w+-duplex)",
            "speed": r", (\d+ [GM]b/s)",
            "media": r"media type is (.+)",
            "members": r"Members in this channel: (.+)",
        }

        result = {}
        current_interface = ""

        for line in cli_output.split("\n"):
            if not line.strip():
                continue
            if "is up" in line or "is down" in line:
                match = re.search(regex_map["interface"], line)
                if match:
                    current_interface = match.group(1)
                    result[current_interface] = {"status": match.group(2)}
                    continue
            for key, regex in regex_map.items():
                match = re.search(regex, line)
                if match and current_interface:
                    result[current_interface][key] = match.group(1)

        for key in regex_map.keys():
            if key == "interface":
                continue
            for interface, values in result.items():
                if key not in values:
                    result[interface][key] = ""
    
    except Exception as e:
        result = {"error": f"{e}"}

    return result