import asyncssh
import asyncio
import re
import json
import csv
import argparse


def parse_nxos_show_version(output):
    # Define regular expressions for the attributes
    regex_map = {
        'bios_version': r'BIOS: version (.+)',
        'loader_version': r'loader: version (.+)',
        'kickstart_version': r'kickstart: version (.+)',
        'system_version': r'system: version (.+)',
        'bios_compile_time': r'BIOS compile time: (.+)',
        'kickstart_image_file': r'kickstart image file is: (.+)',
        'kickstart_compile_time': r'kickstart compile time: (.+)',
        'system_image_file': r'system image file is: (.+)',
        'system_compile_time': r'system compile time: (.+)',
        'chassis': r'cisco (.+Chassis)',
        'processor_info': r'(.+CPU with .+ kB of memory.)',
        'processor_board_id': r'Processor Board ID (.+)',
        'device_name': r'Device name: (.+)',
        'bootflash': r'bootflash: (.+ kB)',
        'kernel_uptime': r'Kernel uptime is (.+)',
        'last_reset': r'Last reset at .+ after (.+)',
        'last_reset_reason': r'Reason: (.+)',
        'system_version_long': r'System version: (.+)',
    }

    result = {}
    for key, regex in regex_map.items():
        match = re.search(regex, output, re.MULTILINE)
        if match:
            result[key] = match.group(1)

    return result


def parse_nxos_show_interface(output):
    # Define regular expressions for the attributes
    regex_map = {
        'interface': r'(.+?) is (up|down)',
        'admin_state': r'admin state is (up|down)',
        'hardware_address': r'Hardware:.+?address: (.+?) \(bia',
        'mtu': r'MTU (.+?) bytes',
        'bandwidth': r'BW (.+?) Kbit',
        'delay': r'DLY (.+?) usec',
        'reliability': r'reliability (.+?),',
        'txload': r'txload (.+?),',
        'rxload': r'rxload (.+?)',
        'encapsulation': r'Encapsulation (.+?),',
        'medium': r'medium is (.+)',
        'port_mode': r'Port mode is (.+)',
        'duplex': r'(\w+-duplex)',
        'speed': r'(\d+.+?b/s)',
        'input_rate_30_sec': r'30 seconds input rate (.+?) bits',
        'output_rate_30_sec': r'30 seconds output rate (.+?) bits',
        'input_rate_5_min': r'input rate (.+?) bps',
        'output_rate_5_min': r'output rate (.+?) bps',
        'input_packets': r'(\d+) input packets',
        'output_packets': r'(\d+) output packets',
    }

    result = {'interfaces': {}}
    current_interface = ''

    for line in output.split('\n'):
        if not line.strip():
            continue
        if 'is up' in line or 'is down' in line:
            match = re.search(regex_map['interface'], line)
            if match:
                current_interface = match.group(1)
                result['interfaces'][current_interface] = {
                    'status': match.group(2)
                }
                continue
        for key, regex in regex_map.items():
            match = re.search(regex, line)
            if match and current_interface:
                result['interfaces'][current_interface][key] = match.group(1)

    return result


def parse_nxos_show_interface_trunk(output):
    interfaces = re.findall(r'(Eth\d+/\d+|Po\d+)', output)
    native_vlans = re.findall(r'(\d+)\s+(trunking|trnk-bndl|not-trunking)', output)
    port_channels = re.findall(r'(trunking|trnk-bndl|not-trunking)\s+(--|Po\d+)', output)
    vlans_allowed = re.findall(r'(Eth\d+/\d+|Po\d+)\s+(\d+-\d+,\d+-\d+)', output)
    stp_forwarding = re.findall(r'(Eth\d+/\d+|Po\d+)\s+(none)', output)

    result = {'interfaces': {}}
    for i, interface in enumerate(interfaces):
        result['interfaces'][interface] = {
            'native_vlan': native_vlans[i][0],
            'status': native_vlans[i][1],
            'port_channel': port_channels[i][1] if port_channels[i][1] != '--' else None,
            'vlans_allowed': vlans_allowed[i][1],
            'stp_forwarding': stp_forwarding[i][1]
        }

    return result


def parse_nxos_show_vlan(output):
    # Define regular expressions for each attribute
    regex_map = {
        'vlan_id': re.compile(r'^(\d+)\s+'),
        'name': re.compile(r'(\S+)\s+(active|suspended)'),
        'status': re.compile(r'(\S+)\s+(active|suspended)'),
        'ports': re.compile(r'active\s+(Eth[^\n]+)'),
        'type': re.compile(r'(\d+)\s+(\w+)\s+'),
        'mode': re.compile(r'(\d+)\s+\w+\s+(\w+)')
    }

    # Split the output by lines and initialize the vlan dictionary
    lines = output.split('\n')
    vlans = {}

    # Loop through each line to find the attributes
    for line in lines:
        vlan_id_match = regex_map['vlan_id'].search(line)
        if vlan_id_match:
            vlan_id = int(vlan_id_match.group(1))
            vlans[vlan_id] = {}

        for attr, regex in regex_map.items():
            match = regex.search(line)
            if match and vlan_id:
                if attr == 'ports':
                    vlans[vlan_id][attr] = [port.strip() for port in match.group(1).split(',')]
                elif attr != 'vlan_id':
                    vlans[vlan_id][attr] = match.group(1)

    return vlans


def parse_nxos_show_interface_status(output):
    regex_map = {
        'port': re.compile(r'^(Eth\d+/\d+)\s+'),
        'name': re.compile(r'^\S+\s+([^\s]+)\s+'),
        'status': re.compile(r'^\S+\s+\S+\s+(\S+)\s+'),
        'vlan': re.compile(r'^\S+\s+\S+\s+\S+\s+(\S+)\s+'),
        'duplex': re.compile(r'^\S+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+'),
        'speed': re.compile(r'^\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+'),
        'type': re.compile(r'^\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)')
    }

    interfaces = {}
    lines = output.split('\n')

    for line in lines:
        port_match = regex_map['port'].search(line)
        if port_match:
            port = port_match.group(1)
            interfaces[port] = {}

            for attr, regex in regex_map.items():
                match = regex.search(line)
                if match and attr != 'port':
                    interfaces[port][attr] = match.group(1)

    return interfaces


# New IOS parsers (only definition and arguments)
def parse_ios_show_version(output):
    pass  # Implement the actual parsing logic for IOS


def parse_ios_show_interface(output):
    pass  # Implement the actual parsing logic for IOS


def parse_ios_show_interface_trunk(output):
    pass  # Implement the actual parsing logic for IOS


def parse_ios_show_vlan(output):
    pass  # Implement the actual parsing logic for IOS


def parse_ios_show_interface_status(output):
    pass  # Implement the actual parsing logic for IOS


def parse_ios_show_run(output):
    # Regular expressions for each attribute
    regex_map = {
        'interface': re.compile(r'^interface (\S+)'),
        'description': re.compile(r'^ description (.+)'),
        'switchport_mode': re.compile(r'^ switchport mode (\S+)'),
        'switchport_trunk_allowed_vlan': re.compile(r'^ switch port trunk allowed vlan (.+)'),
        'switchport_trunk_allowed_vlan_add': re.compile(r'^ switchport trunk allowed vlan add (.+)'),
        'no_switchport': re.compile(r'^ no switchport'),
        'no_ip_address': re.compile(r'^ no IP address'),
        'switch_virtual_link': re.compile(r'^ switch virtual link (\d+)'),
        'login_event_link_status': re.compile(r'^ login event link-status'),
        'channel_group': re.compile(r'^ channel-group (\d+) mode (\S+)')
    }

    # Initialize a dictionary to hold the parsed data
    interfaces = {}
    current_interface = ''

    # Split the output into lines and loop through each line
    for line in output.split('\n'):
        interface_match = regex_map['interface'].match(line)
        if interface_match:
            current_interface = interface_match.group(1)
            interfaces[current_interface] = {}
            continue

        # If inside an interface configuration section, search for attributes
        if current_interface:
            for attr, regex in regex_map.items():
                if attr == 'interface':
                    continue
                match = regex.match(line)
                if match:
                    if attr in ['switchport_trunk_allowed_vlan', 'switchport_trunk_allowed_vlan_add']:
                        # Add the allowed vlans to the list
                        vlans = match.group(1)
                        if 'allowed_vlans' in interfaces[current_interface]:
                            interfaces[current_interface]['allowed_vlans'] += ',' + vlans
                        else:
                            interfaces[current_interface]['allowed_vlans'] = vlans
                    else:
                        interfaces[current_interface][attr] = match.group(1)

    return {"show run": interfaces}


def parse_text_file(filename, command_parsers, address):
    with open(filename, 'r') as file:
        content = file.read()
        commands = re.findall(r'show \w+', content)
        outputs = {}
        for index, command in enumerate(commands):
            start = content.index(command) + len(command)
            end = content.index(commands[index + 1]) if index + 1 < len(commands) else None
            output = content[start:end]
            parser = command_parsers.get(command)
            if parser:
                outputs[command] = parser(output)
        return {address: outputs}


def write_json(data):
    for address, output in data.items():
        filename = f"{address.replace('.', '_')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=4)


async def connect_to_device(device, command_parsers):
    try:
        async with asyncssh.connect(
            device['address'],
            username=device['username'],
            password=device['password']
        ) as conn:
            outputs = {}
            for cmd, parser in command_parsers.items():
                result = await conn.run(cmd, check=True)
                outputs[cmd] = parser(result.stdout)
            write_json({device['address']: outputs})
    except (OSError, asyncssh.Error) as exc:
        print(f"SSH connection failed for {device['address']}: {exc}")


async def main():
    
    # Argument parser
    parser = argparse.ArgumentParser(description="Network Device Parser")
    parser.add_argument("os_type", choices=["IOS", "NX-OS"], help="Operating system type of the network device.")
    parser.add_argument("--file", help="Text file containing the output of the show commands.")
    args = parser.parse_args()
    
    # Choose the appropriate parsers based on the OS type
    if args.os_type == "NX-OS":
        command_parsers = {
            'show version': parse_nxos_show_version,
            'show interface': parse_nxos_show_interface,
            'show interface trunk': parse_nxos_show_interface_trunk,
            'show vlan': parse_nxos_show_vlan,
            'show interface status': parse_nxos_show_interface_status
        }
    elif args.os_type == "IOS":
        command_parsers = {
            'show version': parse_ios_show_version,
            'show interface': parse_ios_show_interface,
            'show interface trunk': parse_ios_show_interface_trunk,
            'show vlan': parse_ios_show_vlan,
            'show interface status': parse_ios_show_interface_status,
            'show run': parse_ios_show_run
        }
    
    # If a text file is provided, parse the commands from the text file
    if args.file:
        outputs = parse_text_file(args.file, command_parsers, args.file)
        write_json(outputs)
    else:
        devices = []
        with open('devices.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                devices.append(row)
        tasks = [connect_to_device(device, command_parsers) for device in devices]
        await asyncio.gather(*tasks)


# Call the async main function
if __name__ == "__main__":
    asyncio.run(main())
