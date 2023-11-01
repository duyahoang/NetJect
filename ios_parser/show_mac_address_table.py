# flake8: noqa E501
import logging
import re


def parse_ios_show_mac_address_table(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show mac address-table command."""

    logging.info('Parsing ios "show mac address-table"...')

    try:
        mac_table = {}
        # Define regular expressions for the attributes
        regex_map = {
            "mac_details": r"(?P<vlan>\d+)\s+(?P<mac>\S+)\s+(?P<type>\S+)\s+(?P<learn>\S+)\s+(?P<age>\S+)\s+(?P<ports>[\w\s,/-]*)",
        }

        lines = cli_output.split("\n")

        for line in lines:
            match = re.search(regex_map["mac_details"], line)
            if match:
                mac = match.group("mac")
                mac_table[mac] = {
                    "vlan": match.group("vlan"),
                    "type": match.group("type"),
                    "learn": match.group("learn"),
                    "age": match.group("age"),
                    "ports": match.group("ports").strip(),
                    }
                
        attributes = ["vlan","type","learn","age","ports"]
        for attr in attributes:
            for mac, values in mac_table.items():
                if attr not in values:
                    mac_table[mac][attr] = ""
                
    except Exception as e:
        return {"error": f"{e}"}
    
    return mac_table