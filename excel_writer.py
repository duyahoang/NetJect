import pandas as pd
import json
import argparse


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
            row = {'key': key}
            # Add the nested key-values as new columns in this row
            for subkey, subvalue in value.items():
                row[subkey] = convert_lists_to_strings(subvalue)
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


def main():

    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Convert JSON data to Excel')
    parser.add_argument('json_file', help='The path to the JSON data file')

    # Parse arguments
    args = parser.parse_args()

    # Read the JSON file
    with open(args.json_file, 'r') as file:
        data = json.load(file)

    device_name = list(data.keys())[0]

    # Create a new Excel writer object for this device
    with pd.ExcelWriter(f'{device_name}.xlsx', engine='openpyxl') as writer:
        for commands in data.values():
            # Iterate over each show command for the device
            for command_name, command_data in commands.items():
                # Convert the command data to a DataFrame
                df = json_to_dataframe(command_data)
                # Write the DataFrame to a new sheet in the Excel file
                df.to_excel(writer, sheet_name=command_name, index=False)


main()
