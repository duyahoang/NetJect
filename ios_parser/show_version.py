import logging
import re


def parse_ios_show_version(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show version command."""

    logging.info('Parsing ios "show version"...')
    try:
        # Define regular expressions for the attributes
        regex_map = {
            "version": r"Cisco IOS Software, (.+?), RELEASE SOFTWARE",
            "rom": r"ROM: (.+?), RELEASE SOFTWARE",
            "system_image_file": r"System image file is: (.+)",
            "platform": r"(Cisco.+Intel.+)"
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
