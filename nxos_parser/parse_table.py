# flake8: noqa E501
from itertools import zip_longest


# Function to recursively remove TABLE_ and ROW_ prefixes
async def remove_prefixes(obj: dict) -> dict:
    """Remove TABLE_ and ROW_ prefix from show commands output in JSON format"""

    if isinstance(obj, dict):    
        new_obj = {}
        for k, v in obj.items():
            new_key = k
            if k.startswith("TABLE_"):
                new_key = k.replace("TABLE_", "", 1)
            elif k.startswith("ROW_"):
                new_key = k.replace("ROW_", "", 1)
            
            new_obj[new_key] = await remove_prefixes(v)
        return new_obj
    elif isinstance(obj, list):
        return [await remove_prefixes(item) for item in obj]
    else:
        return obj

    
async def parse_table(table: dict) -> dict:
    """Recursively parses the tables in show commands output in JSON format."""

    result = {}
    for table_key, table_value in table.items():
        if not table_key.startswith("TABLE_"):
            result[table_key] = table_value
            continue
        result_key = table_key.split("_",1)[1]
        # result_key = table_key
        if isinstance(table_value, dict):
            for row_key, row_value in table_value.items():
                if isinstance(row_value, list):
                    for item in row_value:
                        temps = []
                        keys_to_delete = []
                        for item_key, item_value in item.items():
                            if item_key.startswith("TABLE_"):
                                keys_to_delete.append(item_key)
                                data = await parse_table({item_key: item_value})
                                temps.append(data)
                        for key in keys_to_delete:
                            del item[key]
                        for temp in temps:
                            item.update(temp)
                elif isinstance(row_value, dict):
                    temps = []
                    keys_to_delete = []
                    for key, value in row_value.items():
                        if key.startswith("TABLE_"): 
                            keys_to_delete.append(key)
                            data = await parse_table({key: value})
                            temps.append(data)
                    for key in keys_to_delete:
                        del row_value[key]
                    for temp in temps:
                        row_value.update(temp)
            result[result_key] = row_value
        elif isinstance(table_value, list):
            result[result_key] = []
            for row in table_value:
                for row_key, row_value in row.items():
                    if isinstance(row_value, dict):
                        temps = []
                        keys_to_delete = []
                        for key, value in row_value.items():
                            if key.startswith("TABLE_"): 
                                keys_to_delete.append(key)
                                data = await parse_table({key: value})
                                temps.append(data)
                        for key in keys_to_delete:
                            del row_value[key]
                        for temp in temps:
                            row_value.update(temp)
                    elif isinstance(row_value, list):
                        for item in row_value:
                            temps = []
                            keys_to_delete = []
                            for item_key, item_value in item.items():
                                if item_key.startswith("TABLE_"):
                                    keys_to_delete.append(item_key)
                                    data = await parse_table({item_key: item_value})
                                    temps.append(data)
                            for key in keys_to_delete:
                                del item[key]
                            for temp in temps:
                                item.update(temp)
                    result[result_key].append(row_value)
    return result


async def zip_tables(data: dict) -> dict:
    """Zip tables at the same level in hierarchy."""

    # table_keys = [key for key in data if key.startswith("TABLE_")]
    table_lists = [data[key] for key in data.keys()]

    zipped_dicts = []
    for dicts in zip_longest(*table_lists, fillvalue={}):
        merged_dict = {}
        for key, d in zip(data.keys(), dicts):
            # Concatenate the data key with each item key
            concatenated_dict = {f"{key}_{k}": v for k, v in d.items()}
            merged_dict.update(concatenated_dict)
        zipped_dicts.append(merged_dict)

    return zipped_dicts