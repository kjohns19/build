import argparse
import dataclasses
import logging
import pathlib
import subprocess
import sys


@dataclasses.dataclass
class Args:
    sudo: bool


def main() -> int:
    args, argv = parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    current_dir = pathlib.Path.cwd()

    if not (current_dir / 'CMakeLists.txt').exists():
        logging.error('No CMakeLists.txt file found in current directory!')
        return 1

    build_dir = current_dir / 'build.dir'
    build_dir.mkdir(exist_ok=True)
    rc = run_cmake(build_dir=build_dir, output_dir=current_dir)
    if rc:
        return rc

    rc = run_make(build_dir, args.sudo, argv)
    return rc


def parse_args() -> tuple[Args, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--sudo', action='store_true',
        help='run make using sudo')
    args, remaining = parser.parse_known_args()
    return Args(args.sudo), remaining


def run_cmake(build_dir: pathlib.Path, output_dir: pathlib.Path) -> int:
    logging.info('Running cmake')
    proc = subprocess.run(
        ['cmake', f'-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={output_dir}', '..'],
        cwd=build_dir)
    proc.returncode


def run_make(build_dir: pathlib.Path, sudo: bool, argv: list[str]) -> int:
    logging.info('Running make')
    cmd = ['make'] + argv
    if sudo:
        cmd = ['sudo'] + cmd
    proc = subprocess.run(cmd, cwd=build_dir)
    proc.returncode


if __name__ == '__main__':
    sys.exit(main())
