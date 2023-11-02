# flake8: noqa E501
import logging
import re


def parse_ios_show_ip_route(cli_output: str) -> dict:
    """Parses the IOS CLI output of the show ip route command."""

    logging.info('Parsing ios "show ip route"...')

    try:
        codes_mapping = {}
        codes_pattern = re.compile(r"([\w*+%]+) - ([-\w\ ]+)")
        matches = codes_pattern.findall(cli_output)
        for code, name in matches:
            codes_mapping[code] = name.strip()

        route_pattern = re.compile(
                r"^(?P<codes>.+?)\s+(?P<prefix>\d+\.\d+\.\d+\.\d+/\d+)"
                r"(?:\s+\[(?P<preference>\d+)/(?P<metric>\d+)\])?\s+"
                r"(via\s+(?P<next_hop>\d+\.\d+\.\d+\.\d+)?|(?P<directly_connected>is directly connected)?,)"
                r"(\s+)?(?P<interface>\S+)?"
            )

        routes = {}
        for line in cli_output.split("\n"):
            match = route_pattern.search(line)
            if match:
                prefix = match.group("prefix")
                codes_list = []
                codes_str = match.group("codes").strip()
                for code in codes_str.split():
                    code = code.strip()
                    if code:
                        if "*" in code:
                            codes_list.append(codes_mapping.get("*", "*"))
                            code = code.replace("*", "")
                        codes_list.append(codes_mapping.get(code, code))
                next_hop = match.group("next_hop") or match.group("directly_connected")

                routes[prefix] = {
                    "codes": codes_list,
                    "preference": match.group("preference") or "",
                    "metric": match.group("metric") or "",
                    "next_hop": next_hop,
                    "interface": match.group("interface")
                }

        attributes = ["codes","preference","metric","next_hop","interface"]
        for attr in attributes:
            for route, values in routes.items():
                if attr not in values:
                    routes[route][attr] = ""

    except Exception as e:
        return {"error": f"{e}"}
    
    return routes
