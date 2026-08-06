import json


FILE_NAME = "properties.json"


def save_properties(properties):
    with open(FILE_NAME, "w") as file:
        json.dump(
            properties,
            file,
            indent=4
        )

def load_properties():
    try:
        with open(FILE_NAME, "r") as file:
            data = json.load(file)
            return data


    except (FileNotFoundError, json.JSONDecodeError):
        return []