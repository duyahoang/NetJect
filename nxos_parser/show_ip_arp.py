# flake8: noqa E501
import re
import logging


def parse_nxos_show_ip_arp(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip arp command."""

    logging.info('Parsing nxos "show ip arp"...')
    try:
        ip_arp_list = []
        # Define regular expressions for the attributes
        regex_map = {
            "ip_arp_details": r"(?P<address>\d+\.\d+\.\d+\.\d+)\s+(?P<age>\S+)\s+(?P<mac_address>\S+)\s+(?P<interface>\S+)",
        }

        lines = cli_output.split("\n")

        for line in lines:
            match = re.search(regex_map["ip_arp_details"], line)
            if match:
                ip_arp_list.append({
                    "address": match.group("address"),
                    # "age": match.group("age"),
                    "mac_address": match.group("mac_address"),
                    "interface": match.group("interface"),
                    })
        
        attributes = ["address","age","mac_address","interface"]
        for attr in attributes:
            for item in ip_arp_list:
                if attr not in item:
                    item[attr] = ""
        
    except Exception as e:
        return [{"error": f"{e}"}]
    
    return ip_arp_list
