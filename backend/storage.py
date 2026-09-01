import json


def save_data(filename, data):

    with open(filename, "w") as file:
        json.dump(
            data,
            file,
            indent=4
        )


def load_data(filename,):

    try:
        with open(filename, "r") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_next_id(items):

    if not items:
        return 1

    return max(
        item["id"]
        for item in items
    ) + 1
