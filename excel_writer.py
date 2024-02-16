# flake8: noqa E501
import pandas as pd
import json
import argparse
from pathlib import Path


# Function to find all json file in the directory and its subdirectory
def find_json_files(directory):
    path = Path(directory)
    return list(path.rglob('*.json'))


# Function to handle the conversion of lists to strings
def convert_lists_to_strings(item):
    if isinstance(item, list):
        return ', '.join(map(str, item))
    return item


# Function to convert nested dictionaries to rows in a DataFrame
def dict_to_rows(cmd_dict):
    rows = []
    for key, value in cmd_dict.items():
        # Create a row for each key
        if isinstance(value, dict):
            # Add the nested key-values as new columns in this row
            for subkey, subvalue in value.items():
                row = {'key': key}
                if isinstance(subvalue, dict):
                    row.update({'key2': subkey})
                    row.update({subkey2: convert_lists_to_strings(subvalue2) for subkey2, subvalue2 in subvalue.items()})
                else:
                    row.update({subkey: convert_lists_to_strings(subvalue) for subkey, subvalue in value.items()})
                rows.append(row)
        else:
            # If the value is not a dictionary, just add the value directly
            rows.append({'key': key, 'value': convert_lists_to_strings(value)})
    return pd.DataFrame(rows)


# Function to convert JSON data for a show command into a DataFrame
def json_to_dataframe(data):
    if isinstance(data, dict):
        # Process the dictionary to create rows
        return dict_to_rows(data)
    elif isinstance(data, list):
        # Process each item in the list to ensure that lists are joined into strings
        processed_data = [{k: convert_lists_to_strings(v) for k, v in item.items()} for item in data]
        return pd.DataFrame(processed_data)
    else:
        raise ValueError("Data is neither a dictionary nor a list")


def write_to_excel(data):

    device_name = list(data.keys())[0]

    # Create a new Excel writer object for this device
    with pd.ExcelWriter(f'{device_name}.xlsx', engine='openpyxl') as writer:
        for commands in data.values():
            # Iterate over each show command for the device
            for command_name, command_data in commands.items():
                # Convert the command data to a DataFrame
                df = json_to_dataframe(command_data)
                sheet_name = command_name[:31]
                # Write the DataFrame to a new sheet in the Excel file
                df.to_excel(writer, sheet_name=sheet_name, index=False)

def main():

    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Write JSON data to Excel')
    parser.add_argument('--file', type=str, help='The JSON data file')
    parser.add_argument('--directory', type=str, help='The directory that has one or multiple JSON files.')

    # Parse arguments
    args = parser.parse_args()

    data_list = []

    # Read the JSON file
    if args.file:
        with open(args.file, 'r') as content:
            data = json.load(content)
            data_list.append(data)
    
    if args.directory:
        json_files = find_json_files(args.directory)
        for file in json_files:
            with open(f'{file}', 'r') as content:
                data = json.load(content)
                data_list.append(data)
    
    for data in data_list:
        write_to_excel(data)


if __name__ == "__main__":
    main()
