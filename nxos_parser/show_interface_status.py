# flake8: noqa E501
import logging
import re


def parse_nxos_show_interface_status(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show interface status command."""
    
    logging.info('Parsing nxos "show interface status"...')

    interfaces = {}
    try:
        regex_map = {
            "interface_status_header": r"Port\s+Name\s+Status\s+Vlan\s+Duplex\s+Speed\s+Type",
            "separator_line": r"^-+"
        }

        lines = cli_output.split("\n")

        # Identify header and column start indices
        header_line = None
        for line in lines:
            if re.search(regex_map["interface_status_header"], line):
                header_line = line
                break

        if not header_line:
            logging.error("Header line not found!")
            return {"msg":"Header line not found!"}

        col_starts = {
            "Port": header_line.index("Port"),
            "Name": header_line.index("Name"),
            "Status": header_line.index("Status"),
            "Vlan": header_line.index("Vlan"),
            "Duplex": header_line.index("Duplex"),
            "Speed": header_line.index("Speed"),
            "Type": header_line.index("Type")
        }

        for line in lines:
            if re.search(regex_map["interface_status_header"], line):
                continue
            if re.search(regex_map["separator_line"], line):
                continue
            port = line[col_starts["Port"]:col_starts["Name"]].strip()
            name = line[col_starts["Name"]:col_starts["Status"]].strip()
            status = line[col_starts["Status"]:col_starts["Vlan"]].strip()
            vlan = line[col_starts["Vlan"]:col_starts["Duplex"]].strip()
            duplex = line[col_starts["Duplex"]:col_starts["Speed"]].strip()
            speed = line[col_starts["Speed"]:col_starts["Type"]].strip()
            int_type = line[col_starts["Type"]:].strip()

            if port:  # If port value exists, then add to the dictionary
                interfaces[port] = {
                    "name": name,
                    "status": status,
                    "vlan": vlan,
                    "duplex": duplex,
                    "speed": speed,
                    "type": int_type,
                }

        attributes = ["name","status","vlan","duplex","speed","type"]
        for attr in attributes:
            for interface, values in interfaces.items():
                if attr not in values:
                    interfaces[interface][attr] = ""
                
    except Exception as e:
        interfaces["error"] = f"{e}"

    return interfaces