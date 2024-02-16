# flake8: noqa E501
import logging
import re


def parse_nxos_show_version(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show version command."""

    logging.info('Parsing nxos "show version"...')

    try:
        # Define regular expressions for the attributes
        regex_map = {
            "bios_version": r"BIOS:\s+version\s(.+)",
            "loader_version": r"loader:\s+version\s+(.+)",
            "kickstart_version": r"kickstart:\s+version\s+(.+)",
            "system_version": r"system:\s+version\s+(.+)",
            "kickstart_image_file": r"kickstart image file is:\s+(.+)",
            "system_image_file": r"system image file is:\s+(.+)",
            "platform": r"(cisco Nexus .+Chassis.+)",
            "device_name": r"Device name:\s+(.+)",
        }

        result = {}
        for key, regex in regex_map.items():
            match = re.search(regex, cli_output, re.MULTILINE)
            if match:
                result[key] = match.group(1)
        
        for key in regex_map.keys():
            if key not in result:
                result[key] = ""
    
    except Exception as e:
        return {"error": f"{e}"}

    return result