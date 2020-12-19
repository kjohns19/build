import dataclasses
import enum
import pathlib
from typing import Dict, List, Optional

from . import library
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
    libraries: List[library.Library]
    include_dirs: List[pathlib.Path]
    install_to: List[pathlib.Path]
    install_includes: List[pathlib.Path]


@dataclasses.dataclass
class Info:
    projectname: str
    builddir: pathlib.Path
    copy: List[str]
    targets: List[Target]


def load(path: pathlib.Path, libraries: Dict[str, library.Library]) -> Info:
    def paths_array(value: Optional[List[str]]) -> List[pathlib.Path]:
        if value is None:
            return []
        return [pathlib.Path(path) for path in value]

    def target_type(type_or_none: Optional[str]) -> TargetType:
        if type_or_none is None:
            return TargetType.EXECUTABLE
        return TargetType[type_or_none.upper()]

    all_libraries = libraries.copy()

    def get_libraries(info_libs: Optional[List[str]],
                      target_libs: Optional[List[str]]) -> List[library.Library]:
        lib_names = util.unique_list((info_libs or []) + (target_libs or []))
        return [all_libraries[name] for name in lib_names]

    data = util.load_json(path, INFO_SCHEMA)

    # Add local libraries to the list of libraries
    for target in data['targets']:
        type = target_type(target.get('type'))
        if type in (TargetType.SHAREDLIB, TargetType.STATICLIB):
            all_libraries[target['name']] = library.Library(
                name=target['name'],
                link_libs=[target['name']],
                find_package=[],
                pkg_check=[],
                include_dirs=[],
                link_dirs=[])

    base_includes = paths_array(data.get('include_dirs'))
    base_flags = data.get('flags', '') + ' '

    return Info(
        projectname=data['projectname'],
        builddir=pathlib.Path(data['builddir']),
        copy=data.get('copy', []),
        targets=[
            Target(
                name=target['name'],
                type=target_type(target.get('type')),
                srcs=[pathlib.Path(path) for path in target['srcs']],
                flags=(base_flags + target.get('flags', '')).strip(),
                libraries=get_libraries(data.get('libraries'), target.get('libraries')),
                include_dirs=base_includes + paths_array(target.get('include_dirs')),
                install_to=paths_array(target.get('install_to')),
                install_includes=paths_array(target.get('install_includes'))
            )
            for target in data['targets']
        ]
    )
