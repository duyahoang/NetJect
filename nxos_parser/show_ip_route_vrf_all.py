# flake8: noqa E501
import logging
import re


def parse_nxos_show_ip_route_vrf_all(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show ip route vrf all command."""

    return {"msg": "Not supported yet"}
    logging.info('Parsing "show ip route vrf all"...')

    regex_map = {
        "route": re.compile(
            r"^([\d.]+/\d+),\s+(\d+)\s+ucast next-hops, (\d+)\s+mcast next-hops"
        ),
        "next_hop": re.compile(
            r"^\s+\*\s*via\s+(\S+),\s+\[([\d/]+)\],\s+(\d+:\d+:\d+),\s+(\w+),\s+(\w+)"
        ),
    }

    routes = {}
    lines = cli_output.split("\n")

    current_route = None
    for line in lines:
        route_match = regex_map["route"].search(line)
        if route_match:
            current_route = route_match.group(1)
            routes[current_route] = {
                "ucast_next_hops": int(route_match.group(2)),
                "mcast_next_hops": int(route_match.group(3)),
                "next_hops": [],
            }
        elif current_route:
            next_hop_match = regex_map["next_hop"].search(line)
            if next_hop_match:
                next_hop = {
                    "via": next_hop_match.group(1),
                    "preference_metric": next_hop_match.group(2),
                    "age": next_hop_match.group(3),
                    "source": next_hop_match.group(4),
                    "type": next_hop_match.group(5),
                }
                routes[current_route]["next_hops"].append(next_hop)

    return {"routes": routes}