import dataclasses
import enum
import pathlib
from typing import List, Optional

from . import util


TYPE_STRING = {'type': 'string'}
TYPE_STRING_ARRAY = {'type': 'array', 'items': TYPE_STRING}

INFO_SCHEMA = {
    'type': 'object',
    'properties': {
        'projectname': TYPE_STRING,
        'builddir': TYPE_STRING,
        'flags': TYPE_STRING,
        'libraries': TYPE_STRING_ARRAY,
        'include_dirs': TYPE_STRING_ARRAY,
        'locallibs': TYPE_STRING,
        'copy': TYPE_STRING_ARRAY,
        'targets': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': TYPE_STRING,
                    'type': {
                        'type': 'string',
                        'pattern': '^(executable|sharedlib|staticlib)$'
                    },
                    'srcs': TYPE_STRING_ARRAY,
                    'flags': TYPE_STRING,
                    'libraries': TYPE_STRING_ARRAY,
                    'include_dirs': TYPE_STRING_ARRAY,
                    'install_to': TYPE_STRING_ARRAY,
                    'install_includes': TYPE_STRING_ARRAY
                },
                'additionalProperties': False,
                'required': ['name', 'srcs']
            }
        }
    },
    'additionalProperties': False,
    'required': ['projectname', 'builddir', 'targets']
}


class TargetType(enum.Enum):
    EXECUTABLE = 'executable'
    SHAREDLIB = 'sharedlib'
    STATICLIB = 'staticlib'


@dataclasses.dataclass
class Target:
    name: str
    type: TargetType
    srcs: List[pathlib.Path]
    flags: str
    libraries: List[str]
    include_dirs: List[pathlib.Path]
    install_to: List[pathlib.Path]
    install_includes: List[pathlib.Path]


@dataclasses.dataclass
class Info:
    projectname: str
    builddir: pathlib.Path
    flags: str
    libraries: List[str]
    include_dirs: List[pathlib.Path]
    locallibs: Optional[pathlib.Path]
    copy: List[str]
    targets: List[Target]


def load(path: pathlib.Path) -> Info:
    def paths_array(value: Optional[List[str]]) -> List[pathlib.Path]:
        if value is None:
            return []
        return [pathlib.Path(path) for path in value]

    def target_type(type_or_none: Optional[str]) -> TargetType:
        if type_or_none is None:
            return TargetType.EXECUTABLE
        return TargetType[type_or_none.upper()]

    data = util.load_json(path, INFO_SCHEMA)
    return Info(
        projectname=data['projectname'],
        builddir=pathlib.Path(data['builddir']),
        flags=data.get('flags', ''),
        libraries=data.get('libraries', []),
        include_dirs=paths_array(data.get('include_dirs')),
        locallibs=pathlib.Path(data['locallibs']) if 'locallibs' in data else None,
        copy=data.get('copy', []),
        targets=[
            Target(
                name=target['name'],
                type=target_type(target.get('type')),
                srcs=[pathlib.Path(path) for path in target['srcs']],
                flags=target.get('flags', ''),
                libraries=target.get('libraries', []),
                include_dirs=paths_array(target.get('include_dirs')),
                install_to=paths_array(target.get('install_to')),
                install_includes=paths_array(target.get('install_includes'))
            )
            for target in data['targets']
        ]
    )
