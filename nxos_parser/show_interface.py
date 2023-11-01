# flake8: noqa E501
import logging
import re


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