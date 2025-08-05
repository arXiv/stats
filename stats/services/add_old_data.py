"""
add_old_data.py

Temporary function to inject our old, less detailed data into the final result derived from query_global_sum, so long as our data remains split.


Functions:
    inject_old_data: Appends data from the appropriate JSON file ('monthly' or 'yearly') into final_result.

Modules:
    json: JSON encoder and decoder.
    os: Miscellaneous operating system interfaces.
"""

import json
import os


def inject_old_data(final_result, time_group):
    """Appends data from the appropriate JSON file ('monthly' or 'yearly') into final_result."""

    if time_group not in {"monthly", "yearly"}:
        print(f"Invalid time_group: {time_group}. Expected 'monthly' or 'yearly'.")
        return final_result  # Return unchanged if an invalid argument is passed

    # Construct absolute path to the JSON file in 'static/old_data'
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of this script
    json_file_path = os.path.join(
        base_dir, "static", "old_data", f"{time_group}_data.json"
    )
    print(json_file_path)
    # print(f"Looking for {json_file_path}...")

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            print(
                f"Successfully loaded {json_file_path}. Injecting {len(json_data)} entries."
            )

        final_result[:0] = json_data  # preppend all data

    except FileNotFoundError:
        print(f"JSON file {json_file_path} not found. Skipping injection.")
    except json.JSONDecodeError:
        print(f"JSON file {json_file_path} is not a valid JSON. Skipping injection.")
    except Exception as e:
        print(f"Unexpected error reading {json_file_path}: {e}")

    return final_result  # Return modified result (or unchanged if error occurred)
