import json

def count_json_elements(json_filename: str) -> int:
    """
    Loads a JSON file and returns the count of elements in it.
    The JSON file is expected to contain a list of elements.
    
    :param json_filename: The filename of the JSON file to load.
    :return: The number of elements in the JSON file.
    :raises ValueError: If the loaded data is not a list.
    """
    data = load_links_from_json(json_filename)
    
    if isinstance(data, list):
        return len(data)
    else:
        raise ValueError("The JSON file does not contain a list of elements.")
    
def load_links_from_json(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

# Example usage:
if __name__ == "__main__":
    filename = "totalbike\\totalbike_final_output.json" 
    count = count_json_elements(filename)
    print(f"Number of elements in {filename}: {count}")
