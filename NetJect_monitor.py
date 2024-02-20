# flake8: noqa E501
import json
import asyncio
import aioping
from deepdiff import DeepDiff
from NetJect import NetJect, parse_args_NetJect, load_configuration
import logging
from pathlib import Path
import argparse
import time
from flask import Flask, render_template
from flask_socketio import SocketIO
import json
import time



logger = logging.getLogger(__name__)
logger.propagate = False  

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

# Asynchronously ping a device
async def ping_device(device: dict) -> bool:
    try:
        delay = await aioping.ping(device['address']) * 1000  # aioping.ping returns delay in seconds
        logger.info(f"{device['address']} is UP, delay {delay:.2f} ms")
        return True
    except TimeoutError:
        logger.info(f"{device['address']} is DOWN")
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
                    just_up = False

                current_state = await NetJect({"devices": [device]})
                current_state = current_state[0]
                hostname = list(current_state.keys())[0]
                diff = compare_json(device["original_state"], current_state)
                if diff:
                    logger.info(f"{hostname} state has been changed:\n{diff}")
                    res = {"device_ip": device.get("address", "No address found in device config"), "device": hostname, "status": "Up"}
                    res.update({"diffs": ["State has been changed.", diff]})
                    res.update({"time_checked": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())})
                else:
                    logger.info(f"{hostname} state has no changed.")
                    res = {"device_ip": device.get("address", "No address found in device config"), "device": hostname, "status": "Up"}
                    res.update({"diffs": "State has no changed."})
                    res.update({"time_checked": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())})
            else:
                try:
                    res = {"device": hostname}
                except NameError:
                    res = {"device": device.get("address", "No address found in device config")}
                res.update({"device_ip": device.get("address", "No address found in device config")})
                res.update({"status": "Down"})
                res.update({"diffs": "Not process yet."})
                res.update({"time_checked": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())})
        except Exception as e:
            logger.error(f"An error occurred during processing device {device['address']}: {str(e)}")
        finally:
            socketio.emit('device_update', json.dumps(res))
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
async def main_async():
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


def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_async())

@socketio.on('connect')
def test_connect():
    print('Client connected')
    # Optionally trigger some actions on connect...

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')
    # Optionally trigger some actions on disconnect...

if __name__ == '__main__':
    # Start the asynchronous event loop in a separate thread or process...
    try:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)  # Set logger to only pass INFO messages and above
        from threading import Thread
        thread = Thread(target=start_async_loop)
        thread.start()
        # Start Flask-SocketIO app
        socketio.run(app, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Caught keyboard interrupt. Exit NetJect_monitor...")
        exit(0)