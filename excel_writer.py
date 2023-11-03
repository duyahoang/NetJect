import pandas as pd
import json
import argparse


# Function to convert JSON data for a show command into a DataFrame
def json_to_dataframe(data):
    # Helper function to handle the conversion of lists to strings
    def convert_lists_to_strings(item):
        if isinstance(item, list):
            return ', '.join(map(str, item))  # Ensures all items are converted to strings
        return item
    
    if isinstance(data, dict):
        # Process the dictionary to convert lists to strings and flatten nested structures
        processed_data = {k: convert_lists_to_strings(v) for k, v in data.items()}
        return pd.json_normalize(processed_data).T
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

    # Iterate over each device in the JSON data
    for device_name, commands in data.items():
        # Create a new Excel writer object for this device
        with pd.ExcelWriter(f'{device_name}.xlsx', engine='openpyxl') as writer:
            # Iterate over each show command for the device
            for command_name, command_data in commands.items():
                # Convert the command data to a DataFrame
                df = json_to_dataframe(command_data)
                # Write the DataFrame to a new sheet in the Excel file
                df.to_excel(writer, sheet_name=command_name, index=False)

            # Save the workbook
            writer.save()


main()
