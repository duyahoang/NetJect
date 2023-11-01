# flake8: noqa E501
import logging
import re


def parse_nxos_show_version(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show version command."""

    logging.info('Parsing nxos "show version"...')

    # Define regular expressions for the attributes
    regex_map = {
        "bios_version": r"BIOS: version (.+)",
        "loader_version": r"loader: version (.+)",
        "kickstart_version": r"kickstart: version (.+)",
        "system_version": r"system: version (.+)",
        "bios_compile_time": r"BIOS compile time: (.+)",
        "kickstart_image_file": r"kickstart image file is: (.+)",
        "kickstart_compile_time": r"kickstart compile time: (.+)",
        "system_image_file": r"system image file is: (.+)",
        "system_compile_time": r"system compile time: (.+)",
        "chassis": r"cisco (.+Chassis)",
        "processor_info": r"(.+CPU with .+ kB of memory.)",
        "processor_board_id": r"Processor Board ID (.+)",
        "device_name": r"Device name: (.+)",
        "bootflash": r"bootflash: (.+ kB)",
        "kernel_uptime": r"Kernel uptime is (.+)",
        "last_reset": r"Last reset at .+ after (.+)",
        "last_reset_reason": r"Reason: (.+)",
        "system_version_long": r"System version: (.+)",
    }

    result = {}
    for key, regex in regex_map.items():
        match = re.search(regex, cli_output, re.MULTILINE)
        if match:
            result[key] = match.group(1)

    return result