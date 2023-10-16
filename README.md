# Network Command Parser

## Overview

The Network Command Parser is a Python-based tool designed to interact with Cisco NXOS and IOS devices, retrieve command outputs, and parse the results to extract specific details. The tool can also parse command outputs stored in text files. The structured data extracted from the command outputs is saved in JSON format, making it easier to analyze or integrate with other tools.

## Features

1. **Live Device Interaction**: Connects to Cisco NXOS devices to execute and retrieve command outputs.
2. **File Parsing**: Can parse stored command outputs from text files.
3. **Command Parsing**: Uses `re` regular expressions to extract specific details from command outputs.
4. **Structured Output**: Saves parsed data in `JSON` format.
5. **Parallel Task Execution**: Employs `asyncio` to process multiple devices or files concurrently, enhancing efficiency.
6. **Extensible**: Placeholder functions exist for future development and integration with Cisco IOS devices.
7. Currently supported commands on NXOS only
   ```
   'nxos':{
        'show version'
        'show interface'
        'show interface trunk'
        'show vlan'
        'show interface status'
    }
   ```

## Requirements

- Python 3.7 or later
  ```bash
  pip install 'python>=3.7'
  ```
- Libraries: `scrapli`, `yaml`, `asyncio`, `logging`, `json`, `re`

## Usage

1. **Clone the Repository**:
   ```
   git clone https://github.com/duyahoang/net-cmd-parser
   ```
2. Install Required Libraries:
   Make sure you have Python and pip installed. Then run:
   ```
   pip install -r requirements.txt
   ```
3. Configure your devices or text files in `devices-config.yaml`.
   - For live devices, provide the `address`, `username`, `password`, `os_type`, and list of `commands`.
   - For text files, provide the `file`, `os_type`, and list of `commands`.
  
2. Execute the script:
   
   ```
   python net-cmd-parser.py
   ```

3. Check the generated JSON files for the parsed output.

## Example

### devices-config.yaml

```yaml
devices:
  - address: 10.201.36.107
    username: admin
    password: C!sc0123
    os_type: nxos
    commands:
      - show version
      - show interface
  - file: device-test.txt
    os_type: nxos
    commands:
      - show version
      - show interface status
```

### Execution:

After running the script, you will find JSON files containing structured data extracted from the specified commands for each device or text file.

---
## Author
Duy Hoang
duyhoan@cisco.com

---

**Note**: Ensure you have the required Python libraries installed and that you're operating in a secure environment when dealing with live devices and sensitive configurations.

--- 
