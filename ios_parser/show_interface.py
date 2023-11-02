# flake8: noqa E501
import logging
import re


def parse_ios_show_interface(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show interface command."""

    logging.info('Parsing ios "show interface"...')
    try:
        # Define regular expressions for the attributes
        regex_map = {
            "interface": r"(.+?) is (up|down), line protocol is (.+?) \((.+?)\)",
            "hardware_address": r"Hardware is .+?address is (.+?) \(bia",
            "internet_address": r"Internet address is (.+)",
            "description": r"Description: (.+)",
            "mtu": r"MTU (.+?) bytes",
            "encapsulation": r"Encapsulation (.+?),",
            "duplex": r"(\w+-duplex)",
            "speed": r", (\d+[GM]b/s),",
            "media": r"media type is (.+)",
            "members": r"Members in this channel: (.+)"
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
                    result[current_interface]["protocol_status"] = match.group(3)
                    result[current_interface]["physical_status"] = match.group(4)
                    continue
            for key, regex in regex_map.items():
                match = re.search(regex, line)
                if match and current_interface:
                    if key == "members":
                        result[current_interface][key] = match.group(1).split()
                    else:
                        result[current_interface][key] = match.group(1)

        for key in regex_map.keys():
            if key == "interface":
                continue
            for interface, values in result.items():
                if key not in values:
                    result[interface][key] = ""
        
        for interface, attribute in result.items():
            result[interface]["port_channel"] = ""
            if attribute["members"]:
                for mem in attribute["members"]:
                    mem_match = re.search(r"[\d/]+", mem).group(0)
                    for inter in result:
                        if mem_match in inter:
                            result[inter]["port_channel"] = interface

    except Exception as e:
        result = {"error": f"{e}"}

    return result
