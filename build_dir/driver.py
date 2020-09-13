import argparse
import contextlib
import dataclasses
import errno
import logging
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List

from . import buildinfo
from . import library
from . import util


BUILDDATADIR = pathlib.Path(__file__).parent.parent.resolve() / 'build_data'

CMAKEFILES = ['CMakeCache.txt', 'CMakeFiles', 'cmake_install.cmake', 'Makefile']


@dataclasses.dataclass
class BuildData:
    info: buildinfo.Info
    run_cmake: bool
    run_make: bool
    need_cmake: bool
    need_init: bool


def main(argv: List[str]):
    args = parse_args(argv)

    init_logging()

    if args.listtemplates:
        print('Available templates: {", ".join(all_templates())}')
        return
    if args.projectname:
        copy_template(args.buildfile, args.projectname, args.template)

    libraries = library.load_all(BUILDDATADIR / 'libs')
    data = read_info(args.buildfile, libraries, args.run_cmake, args.run_make)

    is_git = is_git_repo()
    if not is_git and args.make_git:
        init_git()
        is_git = True

    data.info.builddir.mkdir(parents=True, exist_ok=True)
    check_source_files(data)

    if data.need_init:
        generate_cmake(data.info, pathlib.Path('CMakeLists.txt'))
        if is_git:
            generate_gitignore(data.info)
        data.need_cmake = True

    if data.need_cmake and data.run_cmake:
        run_cmake(data.info.builddir)

    if data.run_make:
        run_make(data.info.builddir, args.sudo, args.make_args)


def parse_args(argv: List[str]) -> argparse.Namespace:
    desc = 'Easy to use wrapper script around cmake and make'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '-f', '--buildfile', action='store', type=pathlib.Path,
        default=pathlib.Path('build.info'),
        help='Use FILE as the build file')
    parser.add_argument(
        '-i', '--init', action='store', dest='projectname',
        help='Initialize a new project build. This generates a new build.info file.')
    parser.add_argument(
        '-t', '--template', action='store', default='default',
        help='With -i/--init, use a template for initialization')
    parser.add_argument(
        '-T', '--listtemplates', action='store_true',
        help='List all available templates')
    parser.add_argument(
        '-c', '--nocmake', dest='run_cmake', action='store_false',
        help='Don\'t run cmake')
    parser.add_argument(
        '-m', '--nomake', dest='run_make', action='store_false',
        help='Don\'t run make')
    parser.add_argument(
        '-g', '--nogit', dest='make_git', action='store_false',
        help='Don\'t create a git repository (with -i/--init)')
    parser.add_argument(
        '-s', '--sudo', action='store_true',
        help='Run make with sudo')
    parser.add_argument(
        'make_args', action='store', nargs='*',
        help='Pass argument to make')

    return parser.parse_args(argv)


def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s')


def is_git_repo() -> bool:
    command = ['git', 'rev-parse', '--git-dir']
    rc = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return rc == 0


def copy_file(file: pathlib.Path, dest: pathlib.Path):
    try:
        shutil.copytree(str(file), str(dest))
    except OSError as e:
        if e.errno == errno.ENOTDIR:
            shutil.copy(str(file), str(dest))
        else:
            raise


def all_templates() -> List[str]:
    all_template_dir = BUILDDATADIR / 'templates'
    return sorted(d.name for d in all_template_dir.iterdir() if d.is_dir())


def copy_template(buildfile: pathlib.Path, projectname: str, template: str):
    templatedir = BUILDDATADIR / 'templates' / template
    if not templatedir.is_dir():
        all_templates_str = ', '.join(all_templates())
        logging.error(f'Invalid template "{template}". '
                      f'Valid templates: {all_templates_str}')
        sys.exit(1)
    buildinfo = templatedir / 'build.info'
    if not buildinfo.is_file():
        logging.error('Invalid template "{template}". Missing build.info')
        sys.exit(1)

    buildinfocontents = buildinfo.read_text()
    buildfile.write_text(buildinfocontents.replace('${project}', projectname) + '\n')

    for filename in [f for f in templatedir.iterdir() if f.name != 'build.info']:
        copy_file(filename, pathlib.Path.cwd() / filename.name)


@contextlib.contextmanager
def move_cmake_files(srcdir: pathlib.Path, destdir: pathlib.Path):
    def do_move(srcdir, destdir):
        for file in CMAKEFILES:
            src = srcdir / file
            dest = destdir / file
            try:
                shutil.move(str(src), str(dest))
            except FileNotFoundError:
                pass

    do_move(srcdir, destdir)
    try:
        yield
    finally:
        do_move(destdir, srcdir)


def run_command(command: List[str]) -> int:
    logging.info(f'Running {shlex.join(command)}')
    return subprocess.call(command)


def init_git():
    command = ['git', 'init']
    run_command(command)


def generate_gitignore(info: buildinfo.Info):
    logging.info('Generating .gitignore')

    startline = '#-- Generated by build --#'
    endline = '#-- End generated by build --#'

    gitignore = [
        startline,
        '# Build dir',
        '/build.dir',
        '',
        '# Vim swap files',
        '*.swp',
        '*.swo',
        '',
        '# Object files',
        '*.o',
        '',
        '# Libraries',
        '*.a',
        '*.so',
    ]

    if any(target.install_to for target in info.targets):
        gitignore.append('')
        gitignore.append('# Install manifest')
        gitignore.append('/install_manifest.txt')

    executables = [
        target.name for target in info.targets
        if target.type == buildinfo.TargetType.EXECUTABLE
    ]
    if executables:
        gitignore.append('')
        gitignore.append('# Executables')
        gitignore.append('\n'.join('/' + exe for exe in executables))

    gitignore.append('')
    gitignore.append(endline)

    gitignorefile = pathlib.Path('.gitignore')

    # Keep existing lines already in gitignore
    # (removing lines generated by a previous build run)
    extra = []
    try:
        existing = gitignorefile.read_text().split('\n')
        if startline in existing:
            extra += existing[:existing.index(startline)]
        if endline in existing:
            extra += existing[existing.index(endline)+1:-1]
    except FileNotFoundError:
        pass

    # If there are existing lines to add, add them to the beginning
    # and separate them with the generated lines by a single empty line
    while extra and not extra[-1]:
        extra.pop()
    if extra:
        extra.append('')

    gitignorefile.write_text('\n'.join(extra + gitignore) + '\n')


def run_cmake(builddir: pathlib.Path):
    with move_cmake_files(builddir, pathlib.Path.cwd()):
        command = ['cmake', '.']
        run_command(command)


def run_make(builddir: pathlib.Path, sudo: bool, args: List[str]):
    with move_cmake_files(builddir, pathlib.Path.cwd()):
        command = ['sudo'] if sudo else []
        command += ['make'] + args
        run_command(command)


def read_info(filename: pathlib.Path, libraries: Dict[str, library.Library],
              run_cmake: bool, run_make: bool) -> BuildData:
    if not filename.is_file():
        logging.error(f'Build info file "{filename}" does not exist. '
                      f'Run "build --help" for help')
        sys.exit(1)

    info = buildinfo.load(filename, libraries)

    if info.builddir:
        cmakefile = pathlib.Path('CMakeLists.txt')
        if cmakefile.is_file():
            need_init = (filename.stat().st_mtime > cmakefile.stat().st_mtime)
        else:
            need_init = True

    return BuildData(
        info=info,
        run_cmake=run_cmake,
        run_make=run_make,
        need_cmake=False,
        need_init=need_init
    )


def get_sources(pattern_path: pathlib.Path) -> Iterable[pathlib.Path]:
    parts = pattern_path.parts

    # Get the index of the first part of the path containing a pattern
    # e.g. /a/b/*.c -> [/, a, b, *.c] -> index 3
    first_pattern_idx = next((i for i, part in enumerate(parts) if '*' in part), None)
    if first_pattern_idx is None:
        return [pattern_path]

    # Insert ** into the pattern to recurse into subdirectories
    parent = pathlib.Path(*parts[:first_pattern_idx])
    pattern = pathlib.Path('**', *parts[first_pattern_idx:])
    return parent.glob(str(pattern))


def check_source_files(data: BuildData):
    # Get the source files for the targets from the previous run
    srcdir = pathlib.Path(data.info.builddir) / 'srcs'
    srcdir.mkdir(parents=True, exist_ok=True)
    all_srcs = {}
    for srcfile in srcdir.iterdir():
        all_srcs[srcfile.name] = [
            pathlib.Path(line) for line in srcfile.read_text().split('\n') if line
        ]
        os.remove(srcfile)

    # Get the source files for the targets now. If they differ, we need to rerun cmake
    for target in data.info.targets:
        srcs = [src for srcs in target.srcs for src in get_sources(srcs)]
        if not srcs:
            data.run_cmake = False
            data.run_make = False
        if target.name not in all_srcs or all_srcs[target.name] != srcs:
            data.need_cmake = True

        # Store the files for the next run
        (srcdir / target.name).write_text('\n'.join(str(src) for src in srcs) + '\n')


def generate_cmake(info: buildinfo.Info, filename: pathlib.Path):
    cmake_data = [
        'cmake_minimum_required(VERSION 2.8 FATAL_ERROR)',
        '',
        f'project({info.projectname})',
    ]

    logging.info('Generating CMakeLists.txt')

    all_libraries = util.unique_list(
        (lib for target in info.targets for lib in target.libraries),
        key=id)

    find_packs = [find for lib in all_libraries for find in lib.find_package]
    pkg_checks = [check for lib in all_libraries for check in lib.pkg_check]
    link_dirs = [dir for lib in all_libraries for dir in lib.link_dirs]

    if find_packs:
        cmake_data.append('')
        for pack in find_packs:
            cmake_data.append(f'find_package({pack})')

    if pkg_checks:
        cmake_data.append('')
        cmake_data.append('INCLUDE(FindPkgConfig)')
        cmake_data.append('')
        for pkg_check in pkg_checks:
            cmake_data.append(f'pkg_check_modules({pkg_check})')

    if link_dirs:
        link_dirs_str = ' '.join(str(link_dir) for link_dir in link_dirs)
        cmake_data.append(f'link_directories({link_dirs_str})')

    for target in info.targets:
        cmake_data.append('')
        files_var = f'SRC_FILES_{target.name}'
        srcs_str = ' '.join(str(path) for path in target.srcs)
        cmake_data.append(f'file(GLOB_RECURSE {files_var} {srcs_str})')
        type_dict = {
            buildinfo.TargetType.EXECUTABLE:
                f'add_executable({target.name} ${{{files_var}}})',
            buildinfo.TargetType.SHAREDLIB:
                f'add_library({target.name} SHARED ${{{files_var}}})',
            buildinfo.TargetType.STATICLIB:
                f'add_library({target.name} STATIC ${{{files_var}}})'
        }
        cmake_data.append(type_dict[target.type])
        if target.flags:
            options = f'{target.name} PRIVATE {target.flags}'
            cmake_data.append(f'target_compile_options({options})')

        include_dirs = [dir for lib in target.libraries for dir in lib.include_dirs]
        include_dirs += target.include_dirs
        if include_dirs:
            dirs = ' '.join(str(include_dir) for include_dir in include_dirs)
            cmake_data.append(
                f'target_include_directories({target.name} PRIVATE {dirs})')

        link_libs = [link_lib for lib in target.libraries for link_lib in lib.link_libs]
        if link_libs:
            links = ' '.join(link_libs)
            cmake_data.append(f'target_link_libraries({target.name} {links})')

    include_files = []
    include_patterns = []

    install_types = {
        buildinfo.TargetType.EXECUTABLE: 'RUNTIME',
        buildinfo.TargetType.SHAREDLIB: 'LIBRARY',
        buildinfo.TargetType.STATICLIB: 'ARCHIVE'
    }

    cmake_data.append('')

    for target in info.targets:
        install_type = install_types[target.type]
        for dest in target.install_to:
            cmake_data.append(
                f'install(TARGETS {target.name} {install_type} DESTINATION {dest})')

        for include in target.install_includes:
            if '*' in str(include):
                include_patterns.append(include)
            else:
                include_files.append(include)

    if include_files:
        files = ' '.join(str(include_file) for include_file in include_files)
        cmake_data.append(f'install(FILES {files} DESTINATION include)')
    for include_pattern in include_patterns:
        cmake_data.append(f'install(DIRECTORY {include_pattern.parent} DESTINATION '
                          f'include FILES_MATCHING PATTERN "{include_pattern.name}")')

    for copy in info.copy:
        cmake_data.append(copy)

    with move_cmake_files(pathlib.Path.cwd(), info.builddir):
        filename.write_text('\n'.join(cmake_data) + '\n')
