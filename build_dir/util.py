import jsonschema  # type: ignore
import json
import pathlib
from typing import Any, Dict, Iterable, List, TypeVar

T = TypeVar('T')


def load_json(filename: pathlib.Path, schema: Dict[str, Any]) -> Dict[str, Any]:
    with filename.open('r') as f:
        data = json.load(f)
    jsonschema.validate(data, schema)
    return data


def unique_list(lst: Iterable[T]) -> List[T]:
    seen = set()
    return [
        elem for elem in lst
        if not (elem in seen or seen.add(elem))  # type: ignore
    ]
