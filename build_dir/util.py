import jsonschema  # type: ignore
import json
import pathlib
from typing import Any, Dict, List


def load_json(filename: pathlib.Path, schema: Dict[Any, Any]) -> Dict[Any, Any]:
    with filename.open('r') as f:
        data = json.load(f)
    jsonschema.validate(data, schema)
    return data


def unique_list(lst: List[Any]) -> List[Any]:
    seen = set()
    return [
        elem for elem in lst
        if not (elem in seen or seen.add(elem))  # type: ignore
    ]
