# NetJect 
in short for Network JSON Object

## Overview

NetJect is a Python-based tool designed to interact with Cisco NXOS and IOS devices, retrieve show command outputs, and transform the results to JSON data. The tool can also parse command outputs stored in text files. The structured data extracted from the command outputs is saved in JSON format, making it easier to analyze or integrate with other tools.

## Features

**Live Devices Interaction Simultaneously**: Connects to Cisco NXOS and IOS devices to execute and retrieve command outputs. It leverages [scrapli](https://carlmontanari.github.io/scrapli/) that natively supports asynchronous to establish SSH connections to multiple devices simultaneously.

**File Parsing**: Can parse stored command outputs from text files.

**Command Parsing**: Uses `re` regular expressions to extract specific details from command outputs.

**Structured Output**: Saves parsed data in `JSON` format.

**Parallel Task Execution**: Employs `asyncio` to process multiple devices or files concurrently, enhancing efficiency.

**Extensible**: Organize into packages such as `nxos_parser` and `ios_parser`. Ease of development for new commands in the future.

**NX-OS**: Currently, NetJect appends `| json` at the end of Nexus show commands to retrieve the JSON format. NetJect cleans up the data by removing the TABLE and ROW intermediates. It also zips tables at the same level hierarchy so the object reflects all its attributes. The zip action is applied on `show interface trunk` and `show vlan` commands. It is recommended to use the `json` for nxos for now until the regex parsing logic for text output is developed.
TODO: develop parsing logic for CLI text format.
   ```
   nxos:
      show version
      show interface
      show interface trunk
      show vlan
      show interface status
      show ip route vrf all
      show system resources
      show spanning-tree
      show vpc
      show vpc role
      show vpc consistency-parameters global
      show port-channel summary
      show cdp neighbor
      show forwarding adjacency
      show ip arp
      show mac address-table
      show ip bgp summary
      show ip ospf neighbor
      show ip pim neighbor
      show hsrp
      show policy-map interface control-plane
    }
   ```

**IOS**: Because IOS only displays CLI text format by default, currently, NetJect supports regex parsing CLI text output of the following show commands.
   ```
   ios:
      show version
      show interface
      show interface trunk
      show vlan
      show interface status
      show cdp neighbor
      show ip arp
      show mac address-table
      show ip route
      show run interface
    }
   ```
   If you want NetJect to parse from the text file, ensure the show commands are in full, like above.


For now, the output result is the device name with each show command as the key to hold the data of its show commands. It is planned to combine information of relative show commands into one, such as show interface, show interface status, and show interface run.

   
## Requirements

- Python 3.7 or later
  ```bash
  pip install 'python>=3.7'
  ```
- Libraries: `scrapli`, `pyyaml`, `aiofiles`

## Usage

1. **Clone the Repository**:
   ```
   git clone https://github.com/duyahoang/NetJect
   ```
2. Install Required Libraries:
   Make sure you have Python and pip installed. Then run:
   ```
   pip install -r requirements.txt
   ```
3. Configure your devices or text files in `devices-config.yaml`.
   - For live devices, provide the `address`, `username`, `password`, `os_type`, `cli_output_format`, and list of `commands`.
   - For text files, provide the `file` with the path of the text file.
   - The common variables, such as `username`, `password`, `os_type`, `cli_output_format`, and `commands`, can be provided at the root of the YAML config file to be shared across devices, or can be placed under the device to use for that specific device.
   - The default value is `os_type: nxos`, `cli_output_format: json`, and `commands` is the list of all supported commands for the OS type.
  
2. Execute the script:
   
   ```
   python NetJect.py
   ```

3. Check the generated JSON files for the parsed output.

## Example

### devices-config.yaml

```yaml
username: admin
password: C!sc0123
os_type: nxos
devices:
  - address: 10.201.36.107
  - file: device-test.txt
    os_type: ios
    cli_output_format: cli-text
    commands:
      - show version
      - show interface status
```

### Execution:

After running the script, you will find JSON files containing structured data extracted from the specified commands for each device or text file.

## Future

- Develop regex parsing logic for text output for nxos device.
- Combine information from relative show commands into one, such as show interface, show interface status, and show run interface.

---
## Author
Duy Hoang
duyhoan@cisco.com

---

**Note**: Ensure you have the required Python libraries installed and that you're operating in a secure environment when dealing with live devices and sensitive configurations.

--- 
