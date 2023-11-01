# flake8: noqa E501
import logging
import re


def parse_ios_show_ip_arp(cli_output: str) -> list:
    """Parses the IOS CLI output of the show ip arp command."""
    
    logging.info('Parsing ios "show ip arp"...')

    try:
        ip_arp_list = []
        # Define regular expressions for the attributes
        regex_map = {
            "ip_arp_details": r"(?P<protocol>\S+)\s+(?P<address>\d+\.\d+\.\d+\.\d+)\s+(?P<age>\S+)\s+(?P<hardware_address>\S+)\s+(?P<type>\S+)\s+(?P<interface>\S+)",
        }

        lines = cli_output.split("\n")

        for line in lines:
            match = re.search(regex_map["ip_arp_details"], line)
            if match:
                ip_arp_list.append({
                    "protocol": match.group("protocol"),
                    "address": match.group("address"),
                    "age": match.group("age"),
                    "hardware_address": match.group("hardware_address"),
                    "type": match.group("type"),
                    "interface": match.group("interface"),
                    })
        
        attributes = ["protocol","address","age","hardware_address","type","interface"]
        for attr in attributes:
            for item in ip_arp_list:
                if attr not in item:
                    item[attr] = ""
        
    except Exception as e:
        return [{"error": f"{e}"}]
    
    return ip_arp_list