# flake8: noqa E501
import json
import asyncio
import aioping
from deepdiff import DeepDiff
from NetJect import NetJect, parse_args_NetJect, load_configuration
import logging
from pathlib import Path
import argparse


logger = logging.getLogger(__name__)
logger.propagate = False  


# Asynchronously ping a device
async def ping_device(device: dict) -> bool:
    try:
        delay = await aioping.ping(device['address']) * 1000  # aioping.ping returns delay in seconds
        logger.info(f"{device['address']} is UP, delay {delay:.2f} ms")
        return True
    except TimeoutError:
        logger.warning(f"{device['address']} is DOWN")
        return False
    except Exception as e:
        logger.error(f"An error occurred while pinging {device['address']}: {str(e)}")
        return False


# Compare JSON configurations
def compare_json(old_config: dict, new_config: dict):
    try:
        return DeepDiff(old_config, new_config, ignore_order=True).pretty()
    except Exception as e:
        logger.error(f"An error occurred while comparing JSON data: {str(e)}")
        return None


# Load original state from JSON files
def load_original_state(file_list):
    data_list = []
    for file_path in file_list:
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                data_list.append(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in file {file_path}: {str(e)}")
        except FileNotFoundError as e:
            logger.error(f"File not found {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred while loading {file_path}: {str(e)}")
    return data_list


# Process each device
async def process_device(device: dict):
    just_up = False
    while True:
        try:
            if await ping_device(device):
                if just_up:
                    await asyncio.sleep(3)
                current_state = await NetJect({"devices": [device]})
                current_state = current_state[0]
                hostname = list(current_state.keys())[0]
                diff = compare_json(device["original_state"], current_state)
                if diff:
                    logger.info(f"{hostname} state has been changed:\n{diff}")
                else:
                    logger.info(f"{hostname} state has no changed.")
                just_up = False
            else:
                just_up = True
        except Exception as e:
            logger.error(f"An error occurred during processing device {device['address']}: {str(e)}")
        finally:
            await asyncio.sleep(3)  # Sleep before next round


# Monitoring loop for all devices
async def monitor_devices(devices):
    try:
        tasks = [process_device(device) for device in devices]
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"{e}")


# Find all JSON files in the directory
def find_json_files(directory):
    path = Path(directory)
    return list(path.rglob('*.json'))


# Argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='Monitoring Network Devices by using NetJect')
    parser.add_argument('--config', type=str, help='Path to the NetJect-config.yaml configuration file.')
    parser.add_argument('--original_state_path', type=str, help='Path to the original state JSON files.')
    args = parser.parse_args()
    return args


# Main coroutine
async def main():
    try:
        args = parse_arguments()
        args_dict = parse_args_NetJect(args)

        config = await load_configuration(args_dict)

        json_files = find_json_files(args.original_state_path)
        original_state_list = load_original_state(json_files)

        current_state_directory = Path.cwd() / "current_state_netject"
        current_state_directory.mkdir(parents=True, exist_ok=True)

        for item in original_state_list:
            device_name = list(item.keys())[0]
            for device in config["devices"]:
                if device["address"] in device_name:
                    device["original_state"] = item
                    device["output_path"] = current_state_directory
                    break
        
        for device in config["devices"]:
            if "original_state" not in device:
                logger.error(f'{device["address"]} does not have original state.')
                return

        await monitor_devices(config["devices"])

    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {str(e)}")


# Run the main function
if __name__ == "__main__":
    # Configure logging
    # logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Set logger to only pass INFO messages and above
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Caught keyboard interrupt. Exit NetJect_monitor...")
        exit(0)
