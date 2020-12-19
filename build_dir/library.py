import dataclasses
import logging
import pathlib
import subprocess
import sys
from typing import Dict, List, Optional, Union

from . import util


TYPE_STRING = {'type': 'string'}
TYPE_STRING_ARRAY = {'type': 'array', 'items': TYPE_STRING}
TYPE_STRING_OR_ARRAY = {'anyOf': [TYPE_STRING, TYPE_STRING_ARRAY]}

LIBRARY_SCHEMA = {
    'type': 'object',
    'additionalProperties': {
        'type': 'object',
        'properties': {
            'find_package': TYPE_STRING_OR_ARRAY,
            'pkg_check': TYPE_STRING_OR_ARRAY,
            'include_dirs': TYPE_STRING_OR_ARRAY,
            'link_dirs': TYPE_STRING_OR_ARRAY,
            'link_libs': TYPE_STRING_OR_ARRAY
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
    def paths_array(name, data: Optional[Union[str, List[str]]]) -> List[pathlib.Path]:
        return [pathlib.Path(path) for path in get_values(name, data)]

    data = util.load_json(path, LIBRARY_SCHEMA)
    return [
        Library(
            name=name,
            find_package=get_values(name, fields.get('find_package')),
            pkg_check=get_values(name, fields.get('pkg_check')),
            include_dirs=paths_array(name, fields.get('include_dirs')),
            link_dirs=paths_array(name, fields.get('link_dirs')),
            link_libs=get_values(name, fields.get('link_libs'))
        )
        for name, fields in data.items()
    ]


def get_values(name: str, data: Optional[Union[str, List[str]]]) -> List[str]:
    if data is None:
        return []
    elif isinstance(data, list):
        return data
    else:
        proc = subprocess.run(data, shell=True, capture_output=True, text=True)
        if proc.returncode:
            logging.error(f'Command for library {name} failed '
                          f'with rcode {proc.returncode}: {data}')
            sys.exit(1)
        return [line for line in proc.stdout.split('\n') if line]
