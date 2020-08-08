import dataclasses
import pathlib
from typing import Dict, List, Optional

from . import util


TYPE_STRING = {'type': 'string'}
TYPE_STRING_ARRAY = {'type': 'array', 'items': TYPE_STRING}

LIBRARY_SCHEMA = {
    'type': 'object',
    'additionalProperties': {
        'type': 'object',
        'properties': {
            'find_package': TYPE_STRING_ARRAY,
            'pkg_check': TYPE_STRING_ARRAY,
            'include_dirs': TYPE_STRING_ARRAY,
            'link_dirs': TYPE_STRING_ARRAY,
            'link_libs': TYPE_STRING_ARRAY
        },
        'additionalProperties': False,
        'required': ['link_libs']
    }
}


@dataclasses.dataclass
class Library:
    name: str
    find_package: List[str]
    pkg_check: List[str]
    include_dirs: List[pathlib.Path]
    link_dirs: List[pathlib.Path]
    link_libs: List[str]


def load_all(directory: pathlib.Path) -> Dict[str, Library]:
    libraries = {}

    for libfilename in directory.iterdir():
        for lib in load(libfilename):
            libraries[lib.name] = lib

    return libraries


def load(path: pathlib.Path) -> List[Library]:
    def paths_array(value: Optional[List[str]]) -> List[pathlib.Path]:
        if value is None:
            return []
        return [pathlib.Path(path) for path in value]

    data = util.load_json(path, LIBRARY_SCHEMA)
    return [
        Library(
            name=name,
            find_package=fields.get('find_package', []),
            pkg_check=fields.get('pkg_check', []),
            include_dirs=paths_array(fields.get('include_dirs')),
            link_dirs=paths_array(fields.get('link_dirs')),
            link_libs=fields.get('link_libs', [])
        )
        for name, fields in data.items()
    ]
