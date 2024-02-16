# flake8: noqa E501
import asyncio
import json
import getpass
import logging
import yaml
import aiofiles
import argparse
import pandas as pd
from pathlib import Path
from scrapli.driver.core import AsyncIOSXEDriver
from scrapli.driver.core import AsyncNXOSDriver
from typing import Any, Callable
from ios_parser import *
from nxos_parser import *


# Disable propagation to prevent logs from being handled by ancestor loggers
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
logger.propagate = False


async def finalize_device_output(device: dict, device_output: dict) -> dict:
    if device["cli_output_format"] == "json" and device["os_type"] == "nxos":
        if "show interface trunk" in device_output and "error" not in device_output["show interface trunk"]:
            device_output["show interface trunk"] = await zip_tables(device_output["show interface trunk"])
        if "show vlan" in device_output and "error" not in device_output["show vlan"]:
            device_output["show vlan"] = await zip_tables(device_output["show vlan"])

    return device_output


async def parse_cmd_output(cmd: str, output: str or dict, format: str, parser: Callable[[dict], dict]) -> (str, dict):
    """Parses the output of specifc show command."""

    logger.info(f'Parsing the output of {cmd}...')

    try:
        if format == "json":
                return cmd, await parse_table(output)
        elif format == "text":
            return cmd, parser(output)
        
    except Exception as e:
        return cmd, {"msg": f"Failed to parse the output from {cmd}","error": f"{e}"}
    

def extract_txt_cmd_output(text: str, commands: list) -> dict:
    """Extract the output of each show commands from the text file."""

    output = {}
    positions = []

    # find the positions of each command in the text
    for cmd in commands:
        pos = text.find(cmd)
        if pos != -1:
            positions.append((pos, cmd))

    # sort the positions to maintain the order in text
    positions.sort()

    # extract the output of each command
    for i in range(len(positions)):
        start = positions[i][0] + len(positions[i][1])  # start of the output
        end = (
            positions[i + 1][0] if i + 1 < len(positions) else len(text)
        )  # end of the output
        cmd_output = text[start:end].strip()  # extract the output
        output[positions[i][1]] = cmd_output

    return output


async def parse_text_file(device: dict, command_parsers: dict) -> dict:
    """Parses the text file that contain show commands and their output."""

    path = Path(device["file"])
    filename = path.stem
    logger.info(f'Extracting show commands from {filename} txt file...')
    async with aiofiles.open(filename, "r") as file:
        content = await file.read()

    cmd_output = extract_txt_cmd_output(content, command_parsers.keys())
    
    outputs = {}
    parse_output_tasks = []
    for cmd, output in cmd_output.items():
        if cmd in device["commands"]:
            parse_output_tasks.append(parse_cmd_output(cmd, output, device["cli_output_format"], command_parsers.get(cmd)))

    parsed_outputs = await asyncio.gather(*parse_output_tasks)
    for cmd, parsed_output in parsed_outputs:
        outputs[cmd] = parsed_output

    device["json_data"] = {filename: outputs}

    return {filename: outputs}


async def parse_device(device: dict, command_parsers: dict) -> dict:
    """Establish SSH connection to device, send commands, and parse their output."""

    host = device["address"]
    if "password" not in device:
        device["password"] = getpass.getpass(prompt=f"Device {host}\nEnter the password: ")

    cmd_out = {}
    try:
        if device["os_type"] == "ios":
            conn = AsyncIOSXEDriver(
                host=device["address"],
                auth_username=device["username"],
                auth_password=device["password"],
                auth_strict_key=False,
                transport="asyncssh",
            )
            logger.info(f"Connecting to {host} and retrieving show commands output...")
            await conn.open()
        elif device["os_type"] == "nxos":
            conn = AsyncNXOSDriver(
                host=device["address"],
                auth_username=device["username"],
                auth_password=device["password"],
                auth_strict_key=False,
                transport="asyncssh",
            )
            logger.info(f"Connecting to {host} and retrieving show commands output...")
            await conn.open()
        else:
            raise ValueError(f"Unsupported OS type: {device['os_type']}")

        hostname_response = await conn.send_command("show hostname")
        device["hostname"] = hostname_response.result
        host = f"{hostname_response.result}_{host}"
        result = {host: {}}
        cli_output_format = device.get("cli_output_format", "json")
        if device['os_type'] == 'ios' and cli_output_format == 'json':
            raise ValueError(f"Cisco IOS does not support JSON output format")
        
        parse_output_tasks = []
        for cmd in device["commands"]:
            if cli_output_format == "json":
                response = await conn.send_command(f"{cmd} | json")
                try:
                    json_resp = json.loads(response.result)
                    parse_output_tasks.append(parse_cmd_output(cmd, json_resp, cli_output_format, command_parsers.get(cmd)))
                except json.JSONDecodeError:
                    logger.error(f'Command {cmd} CLI output is not in JSON format.')
                    result[host].update({cmd: {"output": response.result, "error": "The CLI output is not in JSON format."}})
            elif cli_output_format == "text":
                response = await conn.send_command(cmd)
                parse_output_tasks.append(parse_cmd_output(cmd, response.result, cli_output_format, command_parsers.get(cmd)))
            else:
                logger.error(f'{host}: NetJect only support cli_output_format in json or text. Have {cli_output_format}.')
                result[host].update({ "error": f'{host}: NetJect only support cli_output_format in json or text. Have {cli_output_format}.'})
            
        parsed_outputs = await asyncio.gather(*parse_output_tasks)
        for cmd, parsed_output in parsed_outputs:
            cmd_out[cmd] = parsed_output
        
        cmd_out = await finalize_device_output(device, cmd_out)

        # Save outputs to a file
        for cmd in device["commands"]:
            response = await conn.send_command(cmd)
            full_filename = device['output_path'] / f"{host}.txt"
            logger.info(f'Saving the CLI output of {cmd} to {full_filename}...')
            with open(f"{full_filename}", "a") as file:
                file.write(f"{cmd}\n")
                file.write(f"{response.result}\n")
    
        await conn.close()

    except Exception as exc:
        logger.error(f"Error encountered during establishing SSH and parsing for {device['address']}: {exc}")
        return {host: {"error": f"Failed to parse device: {exc}"}}
    
    result[host].update(cmd_out)
    device["json_data"] = result
    logger.info(f'Finish parsing {host}...')
    return result


async def process_device(device: dict, command_parsers: dict) -> Any:
    """Process a single device based on the provided configuration."""

    os_type = device["os_type"]

    supported_commands = command_parsers.get(os_type, {})
    for cmd in device["commands"]:
        if cmd not in supported_commands:
            raise ValueError(f"Command {cmd} is not supported in {os_type}")
    if "address" in device:
        return await parse_device(device, supported_commands)
    elif "file" in device:
        return await parse_text_file(device, supported_commands)


async def write_json(output_path: Path, data: dict):
    """Asynchronously write data to a JSON file."""

    for host, _ in data.items():
        filename = f"{host}.json"
    full_filename = output_path / filename
    logger.info(f'Writing {list(data.keys())[0]} to JSON file {full_filename}...')
    async with aiofiles.open(str(full_filename), "w") as file:
        await file.write(json.dumps(data, indent=4))


# Function to handle the conversion of lists to strings
def convert_lists_to_strings(item: list):
    if isinstance(item, list):
        return ', '.join(map(str, item))
    return item


# Function to convert nested dictionaries to rows in a DataFrame
def dict_to_rows(cmd_dict: dict):
    rows = []
    # Iterate over the first level keys and values
    for key, value in cmd_dict.items():
        if isinstance(value, dict):
            # Iterate over the second level keys and values
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    # Use the first level key and second level key as part of the row
                    row = {'key': key, 'key2': subkey}
                    # Add the nested key-values as new columns in this row
                    for nested_key, nested_value in subvalue.items():
                        row[nested_key] = convert_lists_to_strings(nested_value)
                    rows.append(row)
                else:
                    # If the subvalue is not a dictionary, handle it as a special case
                    rows.append({'key': key, 'key2': subkey, 'value': convert_lists_to_strings(subvalue)})
        else:
            # If the value is not a dictionary, handle it as a special case
            rows.append({'key': key, 'value': convert_lists_to_strings(value)})
    return pd.DataFrame(rows)


# Function to convert JSON data for a show command into a DataFrame
def json_to_dataframe(data: dict | list):
    if isinstance(data, dict):
        # Process the dictionary to create rows
        return dict_to_rows(data)
    elif isinstance(data, list):
        # Process each item in the list to ensure that lists are joined into strings
        processed_data = [{k: convert_lists_to_strings(v) for k, v in item.items()} for item in data]
        return pd.DataFrame(processed_data)
    else:
        raise ValueError("Data is neither a dictionary nor a list")


def write_to_excel(output_path: Path, data: dict):

    device_name = list(data.keys())[0]
    full_filename = output_path / f"{device_name}.xlsx"

    # Create a new Excel writer object for this device
    logger.info(f'Writing {list(data.keys())[0]} to Excel {full_filename}...')
    with pd.ExcelWriter(f'{full_filename}', engine='openpyxl') as writer:
        for commands in data.values():
            # Iterate over each show command for the device
            for command_name, command_data in commands.items():
                # Convert the command data to a DataFrame
                df = json_to_dataframe(command_data)
                # Write the DataFrame to a new sheet in the Excel file
                df.to_excel(writer, sheet_name=command_name, index=False)


async def process_and_write(device: dict, command_parsers: dict):
    try:
        output = await process_device(device, command_parsers)
    except Exception as e:
        name = device["address"] if "address" in device else device["file"]
        output = {name:{"msg": f"Failed to process device {name}", "error": f"{e}"}}

    if not output.keys():
        logger.error(f'Found no key from parsing result of {device["host"] if "host" in device else device["file"]}')
    elif list(output.keys())[0]:
        await write_json(device["output_path"], output)
        if device.get("excel"):
            write_to_excel(device["output_path"], output)
    return output


async def load_configuration(args_dict: dict) -> dict:
    """Load device configuration from a YAML file."""

    nxos_cmds_default = [
            "show version",
            "show interface",
            "show interface trunk",
            "show vlan",
            "show interface status",
            "show ip route vrf all",
            "show system resources",
            "show spanning-tree",
            "show vpc",
            "show vpc role",
            "show vpc consistency-parameters global",
            "show port-channel summary",
            "show cdp neighbor",
            "show forwarding adjacency",
            "show ip arp",
            "show mac address-table",
            "show ip bgp summary",
            "show ip ospf neighbor",
            "show ip pim neighbor",
            "show hsrp",
            "show policy-map interface control-plane",
        ]
    ios_cmds_default = [
            "show version",
            "show interface",
            "show interface trunk",
            "show vlan",
            "show interface status",
            "show cdp neighbor",
            "show ip arp",
            "show mac address-table",
            "show ip route",
            "show run interface",
        ]

    for device in args_dict["devices"]:
        if "address" not in device and "file" not in device:
            raise ValueError(f"No 'address' or 'file' key is found in {device}")
        if "username" not in device and "username" not in args_dict and "address" in device:
            raise ValueError(f"No 'username' key is found in {device}")
        if "username" not in device and "address" in device:
            device["username"] = args_dict["username"]
        if "password" not in device and "password" in args_dict:
            device["password"] = args_dict["password"]
        if "os_type" not in device:
            device["os_type"] = args_dict.get("os_type", "nxos")
        if "cli_output_format" not in device:
            device["cli_output_format"] = args_dict.get("cli_output_format", "json")
            if device['os_type'] == 'ios' and device["cli_output_format"] == 'json':
                raise ValueError(f"Cisco IOS does not support JSON output format")
        if "output_path" not in device:
            device["output_path"] = Path(args_dict.get("output_path", Path.cwd()))
        if "excel" not in device:
            device["excel"] = args_dict.get("excel", False)
        if "commands" not in device:
            if "commands" not in args_dict:
                if device["os_type"] == "nxos":
                    device["commands"] = nxos_cmds_default
                elif device["os_type"] == "ios":
                    device["commands"] = ios_cmds_default
            else:
                device["commands"] = args_dict["commands"]
    return args_dict


def parse_args():

    # Create the argument parser
    parser = argparse.ArgumentParser(description='NetJect - Network JSON Object')

    # Define arguments that correspond to the YAML configuration
    parser.add_argument('--config', type=str, help='Path to the NetJect-config.yaml configuration file.')
    parser.add_argument('--username', type=str, help='Username for device login.')
    parser.add_argument('--password', type=str, help='Password for device login. If not provide, NetJect will ask later.')
    parser.add_argument('--os_type', type=str, choices=['nxos', 'ios'], help='OS type of the device. (nxos | ios)')
    parser.add_argument('--cmd_output_format', type=str, choices=['json', 'text'], help='Command output format. (json | text).')
    parser.add_argument('--output_path', type=str, help='Path to save the output.')
    parser.add_argument('--commands', nargs='*', help='List of commands to execute.')
    parser.add_argument('--addresses', nargs='*', help='List of device addresses.')
    parser.add_argument('--files', nargs='*', help='List of files with device\'s show commands CLI output.')
    parser.add_argument('--excel', action='store_true', help='Write data to Excel.')

    args = parser.parse_args()

    return args


def parse_args_NetJect(args) -> dict:
    
    args_dict = {}
    
    if args.config:
        config_path = Path(args.config)
        if config_path.is_dir():
            config_file = config_path / "NetJect-config.yaml"
            if config_file.is_file():
                with open(config_file, 'r') as stream:
                    args_dict = yaml.safe_load(stream)
            else:
                logger.error(f"NetJect-config.yaml file is not found in {config_path}.")
                raise ValueError(f"NetJect-config.yaml file is not found in {config_path}.")
        else:
            logger.error(f"Path {args.config} not found.")
            raise ValueError(f"NetJect-config.yaml file is not found in {config_path}.")
    elif args.addresses or args.files:
        # Convert arguments to a dictionary, removing any None values
        args_dict = {k: v for k, v in vars(args).items() if v is not None}
        args_dict["devices"] = []
        for addr in args_dict.get("addresses", []):
            args_dict["devices"].append({"address": addr})
        for file in args_dict.get("files", []):
            args_dict["devices"].append({"file": file})
    else:
        config_file = Path.cwd() / "NetJect-config.yaml"
        if config_file.is_file():
            with open(config_file, 'r') as stream:
                args_dict = yaml.safe_load(stream)
        else:
            logger.error(f"Path to the NetJect-config.yaml configuration file is not provided and NetJect-config.yaml file is not found in current working directory.")
            raise ValueError(f"Path to the NetJect-config.yaml configuration file is not provided and NetJect-config.yaml file is not found in current working directory.")

    if "devices" not in args_dict or len(args_dict["devices"]) == 0:
        raise ValueError(f"No devices are provided.")
    
    return args_dict


async def NetJect(args_dict: dict) -> dict:

    # command_parsers based on the OS type
    command_parsers = {
        "nxos": {
            "show version": parse_nxos_show_version,
            "show interface": parse_nxos_show_interface,
            "show interface trunk": parse_nxos_show_interface_trunk,
            "show vlan": parse_nxos_show_vlan,
            "show interface status": parse_nxos_show_interface_status,
            "show ip route vrf all": parse_nxos_show_ip_route_vrf_all,
            "show system resources": parse_nxos_show_system_resources,
            "show spanning-tree": parse_nxos_show_spanning_tree,
            "show vpc": parse_nxos_show_vpc,
            "show vpc role": parse_nxos_show_vpc_role,
            "show vpc consistency-parameters global": parse_nxos_show_vpc_cons_para_global,
            "show port-channel summary": parse_nxos_show_port_channel_summary,
            "show cdp neighbor": parse_nxos_show_cdp_neighbor,
            "show forwarding adjacency": parse_nxos_show_forwarding_adjacency,
            "show ip arp": parse_nxos_show_ip_arp,
            "show mac address-table": parse_nxos_show_mac_address_table,
            "show ip bgp summary": parse_nxos_show_ip_bgp_summary,
            "show ip ospf neighbor": parse_nxos_show_ip_ospf_neighbor,
            "show ip pim neighbor": parse_nxos_show_ip_pim_neighbor,
            "show hsrp": parse_nxos_show_hsrp,
            "show policy-map interface control-plane": parse_nxos_show_policy_map_int_ctrl_plane,
        },
        "ios": {
            "show version": parse_ios_show_version,
            "show interface": parse_ios_show_interface,
            "show interface trunk": parse_ios_show_interface_trunk,
            "show vlan": parse_ios_show_vlan,
            "show interface status": parse_ios_show_interface_status,
            "show cdp neighbor": parse_ios_show_cdp_neighbor,
            "show ip arp": parse_ios_show_ip_arp,
            "show mac address-table": parse_ios_show_mac_address_table,
            "show ip route": parse_ios_show_ip_route,
            "show run interface": parse_ios_show_run_interface,
        },
    }

    config = await load_configuration(args_dict)

    tasks = []
    if "devices" in config:
        for device in config["devices"]:
            tasks.append(process_and_write(device, command_parsers))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    outputs = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Error encountered during task: {result}")
        else:
            outputs.append(result)
    return outputs


if __name__ != "__main__":
    # Add a handler to logger to handle only ERROR level messages
    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)  # Set logger to only pass ERROR messages and above


# Call the async NetJect function
if __name__ == "__main__":
    # Setting up logging
    # logging.basicConfig(
    #     level=logging.INFO, format="[%(asctime)s] [%(levelname)s]: %(message)s"
    # )
    # Add a handler to logger to handle only ERROR level messages
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Set logger to only pass INFO messages and above
    args = parse_args()
    args_dict = parse_args_NetJect(args)
    outputs = asyncio.run(NetJect(args_dict))
