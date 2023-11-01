# flake8: noqa E501
import logging
import re


def parse_nxos_show_hsrp(cli_output: str) -> dict:
    """Parses the NXOS CLI output of the show hsrp command."""

    return {"msg": "Not supported yet"}