# flake8: noqa E501
import logging
import re


def parse_ios_show_run_interface(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show run interface command."""

    logging.info('Parsing ios "show run interface"...')
    interfaces = {}
    try:
    # Regular expressions for each attribute
        regex_map = {
            "interface": re.compile(r"^interface (\S+)"),
            "description": re.compile(r"\s+description (.+)"),
            "switchport_mode": re.compile(r"\s+switchport mode (\S+)"),
            "native_vlan": re.compile(r"native vlan (.+)"),
            "access_vlan": re.compile(r"\s+switchport access vlan (\d+)"),
            "ip_address": re.compile(r"^ ip address (.+)"),
            "channel_group": re.compile(r"^ channel-group (\d+) mode (\S+)"),
        }

        current_interface = ""

        # Split the output into lines and loop through each line
        for line in cli_output.split("\n"):
            interface_match = regex_map["interface"].match(line)
            if interface_match:
                current_interface = interface_match.group(1)
                interfaces[current_interface] = {}
                continue

            # If inside an interface configuration section, search for attributes
            if current_interface:
                for attr, regex in regex_map.items():
                    if attr == "interface":
                        continue
                    match = regex.match(line)
                    if match:
                        if attr == "channel_group":
                            interfaces[current_interface][attr] = match.group(1)
                            interfaces[current_interface]["channel_group_mode"] = match.group(2)
                        else:
                            interfaces[current_interface][attr] = match.group(1)

        attributes = ["description","switchport_mode","native_vlan","access_vlan","ip_address","channel_group","channel_group_mode"]
        for attr in attributes:
            for inter, values in interfaces.items():
                if attr not in values:
                    interfaces[inter][attr] = ""

    except Exception as e:
        interfaces["msg"] = e
    return interfaces