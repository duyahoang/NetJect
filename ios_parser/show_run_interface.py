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
            "description": re.compile(r"^ description (.+)"),
            "switchport_mode": re.compile(r"^ switchport mode (\S+)"),
            "switchport_trunk_allowed_vlan": re.compile(
                r"^ switch port trunk allowed vlan (.+)"
            ),
            "switchport_trunk_allowed_vlan_add": re.compile(
                r"^ switchport trunk allowed vlan add (.+)"
            ),
            "no_switchport": re.compile(r"^ no switchport"),
            "no_ip_address": re.compile(r"^ no IP address"),
            "switch_virtual_link": re.compile(r"^ switch virtual link (\d+)"),
            "login_event_link_status": re.compile(r"^ login event link-status"),
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
                        if attr in [
                            "switchport_trunk_allowed_vlan",
                            "switchport_trunk_allowed_vlan_add",
                        ]:
                            # Add the allowed vlans to the list
                            vlans = match.group(1)
                            if "allowed_vlans" in interfaces[current_interface]:
                                interfaces[current_interface]["allowed_vlans"] += (
                                    "," + vlans
                                )
                            else:
                                interfaces[current_interface]["allowed_vlans"] = vlans
                        else:
                            interfaces[current_interface][attr] = match.group(1)
    
    except Exception as e:
        interfaces["msg"] = e
    return interfaces