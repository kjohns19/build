import jsonschema  # type: ignore
import json
import pathlib
from typing import Any, Callable, Dict, Iterable, List, TypeVar

T = TypeVar('T')


def identity(value: T) -> T:
    return value


def load_json(filename: pathlib.Path, schema: Dict[str, Any]) -> Dict[str, Any]:
    with filename.open('r') as f:
        data = json.load(f)
    jsonschema.validate(data, schema)
    return data


def unique_list(lst: Iterable[T], key: Callable[[T], Any] = identity) -> List[T]:
    seen_set = set()

    def seen(elem: T) -> bool:
        value = key(elem)
        if value in seen_set:
            return True
        seen_set.add(value)
        return False

    return [elem for elem in lst if not seen(elem)]
