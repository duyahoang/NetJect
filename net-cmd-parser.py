import asyncssh
import asyncio
import re
import json
import csv
import argparse
import logging


def parse_nxos_show_version(output):
    logging.debug('Parsing "show version"...')
    
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
    logging.debug('Parsing "show interface"...')

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
    logging.debug('Parsing "show interface trunk"...')

    # Regex patterns map
    regex_map = {
        'port_details_header': r'Port\s+Native\s+Status\s+Port',
        'port_details': r'(?P<port>\S+)\s+(?P<native_vlan>\d+)\s+(?P<status>\S+(?:-\S+)?)\s+(?P<port_channel>\S+)',
        'vlans_allowed_header': r'Port\s+Vlans Allowed on Trunk',
        'vlans_allowed': r'(?P<port>\S+)\s+(?P<vlans_allowed>[\d,-]+)',
        'stp_forwarding_header': r'Port\s+STP Forwarding',
        'stp_forwarding': r'(?P<port>\S+)\s+(?P<stp_forwarding>\S+)'
    }
    
    # Identify the start indices of each section based on headers
    port_details_index = re.search(regex_map['port_details_header'], output).end()
    vlans_allowed_index = re.search(regex_map['vlans_allowed_header'], output).end()
    stp_forwarding_index = re.search(regex_map['stp_forwarding_header'], output).end()

    # Extract section strings
    port_details_string = output[port_details_index:vlans_allowed_index]
    vlans_allowed_string = output[vlans_allowed_index:stp_forwarding_index]
    stp_forwarding_string = output[stp_forwarding_index:]
    
    # Parse port details section
    port_details = {}
    for match in re.finditer(regex_map['port_details'], port_details_string):
        port = match.group('port')
        port_details[port] = {
            'Native Vlan': match.group('native_vlan'),
            'Status': match.group('status'),
            'Port Channel': match.group('port_channel')
        }

    # Parse VLANs allowed section
    vlans_allowed = {}
    for match in re.finditer(regex_map['vlans_allowed'], vlans_allowed_string):
        port = match.group('port')
        vlans_allowed[port] = match.group('vlans_allowed')

    # Parse STP Forwarding section
    stp_forwarding = {}
    for match in re.finditer(regex_map['stp_forwarding'], stp_forwarding_string):
        port = match.group('port')
        stp_forwarding[port] = match.group('stp_forwarding')

    # Combine the parsed data into a single dictionary
    result = {}
    for port in port_details:
        result[port] = port_details[port]
        result[port]['Vlans Allowed on Trunk'] = vlans_allowed.get(port, '')
        result[port]['STP Forwarding'] = stp_forwarding.get(port, '')

    return result


def parse_nxos_show_vlan(output):
    logging.debug('Parsing "show vlan"...')

    # Regex patterns map
    regex_map = {
        'vlan_details': r'(?P<vlan_id>\d+)\s+(?P<vlan_name>\S+)\s+(?P<status>\S+)(?P<ports>[\w\s,/-]*)',
        'vlan_type_mode': r'(?P<vlan_id>\d+)\s+(?P<type>\S+)\s+(?P<mode>\S+)',
        'remote_span': r'(?P<primary>\d+)\s+(?P<secondary>\d+)\s+(?P<type>\S+)\s+(?P<ports>[\w\s,/-]*)'
    }

    # Identify the start indices of each section based on headers
    vlan_detail_index = output.find('VLAN Name')
    vlan_type_mode_index = output.find('VLAN Type  Vlan-mode')
    remote_span_index = output.find('Remote SPAN VLANs')
    
    # Extract section strings
    vlan_detail_string = output[vlan_detail_index:vlan_type_mode_index]
    vlan_type_mode_string = output[vlan_type_mode_index:remote_span_index]
    remote_span_string = output[remote_span_index:]
    
    vlan_data = {}
    
    # Variable to hold current VLAN ID
    current_vlan = None
    
    # Parse VLAN details with ports mapping
    for line in vlan_detail_string.splitlines():
        match = re.search(regex_map['vlan_details'], line)
        if match:
            current_vlan = match.group('vlan_id')
            ports_list = match.group('ports').strip().split(', ')
            # Ensure that empty strings are not included in the Ports list
            ports_list = [port for port in ports_list if port]
            vlan_data[current_vlan] = {
                'VLAN Name': match.group('vlan_name'),
                'Status': match.group('status'),
                'Ports': ports_list
            }
        elif current_vlan and line.strip():
            # Continuation lines for the ports of a VLAN
            ports = line.strip().split(', ')
            vlan_data[current_vlan]['Ports'].extend(ports)
    
    # Parse VLAN type and mode
    for line in vlan_type_mode_string.splitlines():
        match = re.search(regex_map['vlan_type_mode'], line)
        if match:
            vlan_id = match.group('vlan_id')
            if vlan_id in vlan_data:  # Ensure the VLAN ID exists in the data
                vlan_data[vlan_id].update({
                    'Type': match.group('type'),
                    'Mode': match.group('mode')
                })
    
    # Parse Remote SPAN VLANs
    for line in remote_span_string.splitlines():
        match = re.search(regex_map['remote_span'], line)
        if match:
            primary = match.group('primary')
            # If primary VLAN ID exists in the data, update its attributes
            if primary in vlan_data:
                vlan_data[primary].update({
                    'Secondary': match.group('secondary'),
                    'RS_Type': match.group('type'),
                    'RS_Ports': match.group('ports').strip().split(', ')
                })
    
    return vlan_data


def parse_nxos_show_interface_status(output):
    logging.debug('Parsing "show interface status"...')
    
    regex_map = {
        'interface_status': r'^(?P<port>Eth\d+/\d+)\s+(?P<name>.+?)\s+(?P<status>down|err-disabled|err-vlans|inactive|up|module \d{1,2})\s+(?P<vlan>\S+)\s+(?P<duplex>\S+)\s+(?P<speed>\S+)\s+(?P<type>\S+)$'
    }

    interfaces = {}
    lines = output.split('\n')

    for line in lines:
        match = re.search(regex_map['interface_status'], line)
        if match:
            port = match.group('port')
            interfaces[port] = {
                'Name': match.group('name'),
                'Status': match.group('status'),
                'Vlan': match.group('vlan'),
                'Duplex': match.group('duplex'),
                'Speed': match.group('speed'),
                'Type': match.group('type')
            }

    return interfaces


def parse_nxos_show_ip_route_all(output):
    logging.debug('Parsing "show ip route all"...')

    regex_map = {
        'route': re.compile(r'^([\d.]+/\d+),\s+(\d+)\s+ucast next-hops, (\d+)\s+mcast next-hops'),
        'next_hop': re.compile(r'^\s+\*\s*via\s+(\S+),\s+\[([\d/]+)\],\s+(\d+:\d+:\d+),\s+(\w+),\s+(\w+)')
    }

    routes = {}
    lines = output.split('\n')

    current_route = None
    for line in lines:
        route_match = regex_map['route'].search(line)
        if route_match:
            current_route = route_match.group(1)
            routes[current_route] = {
                'ucast_next_hops': int(route_match.group(2)),
                'mcast_next_hops': int(route_match.group(3)),
                'next_hops': []
            }
        elif current_route:
            next_hop_match = regex_map['next_hop'].search(line)
            if next_hop_match:
                next_hop = {
                    'via': next_hop_match.group(1),
                    'preference_metric': next_hop_match.group(2),
                    'age': next_hop_match.group(3),
                    'source': next_hop_match.group(4),
                    'type': next_hop_match.group(5)
                }
                routes[current_route]['next_hops'].append(next_hop)

    return {"routes": routes}


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


def extract_txt_cmd_output(text, commands):
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
        end = positions[i+1][0] if i+1 < len(positions) else len(text)  # end of the output
        cmd_output = text[start:end].strip()  # extract the output
        output[positions[i][1]] = cmd_output
    
    return output


def parse_text_file(filename, command_parsers):
    
    with open(filename, 'r') as file:
        content = file.read()
        cmd_output = extract_txt_cmd_output(content, command_parsers.keys())
        outputs = {}
        for cmd, output in cmd_output.items():
            parser = command_parsers.get(cmd)
            if parser:
                outputs[cmd] = parser(output)
    
    return {filename: outputs}


def write_txt(filename, data):
    with open(filename, 'w') as f:
        f.write(data)


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
    parser.add_argument("os_type", choices=["ios", "nxos"], help="Operating system type of the network device.")
    parser.add_argument("--file", help="Text file containing the output of the show commands.")
    args = parser.parse_args()
    
    # Choose the appropriate parsers based on the OS type
    if args.os_type == "nxos":
        command_parsers = {
            'show version': parse_nxos_show_version,
            'show interface': parse_nxos_show_interface,
            'show interface trunk': parse_nxos_show_interface_trunk,
            'show vlan': parse_nxos_show_vlan,
            'show interface status': parse_nxos_show_interface_status,
            'show ip route all': parse_nxos_show_ip_route_all
        }
    elif args.os_type == "ios":
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
        outputs = parse_text_file(args.file, command_parsers)
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
