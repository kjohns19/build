import logging
import pathlib
import subprocess
import sys


def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    if not pathlib.Path('./CMakeLists.txt').exists():
        logging.error('No CMakeLists.txt file found in current directory!')
        return 1

    build_dir = pathlib.Path('./build.dir')
    build_dir.mkdir(exist_ok=True)
    rc = run_cmake(build_dir)
    if rc:
        return rc
    rc = run_make(build_dir, sys.argv[1:])
    return rc


def run_cmake(build_dir: pathlib.Path) -> int:
    proc = subprocess.run(['cmake', '..'], cwd=build_dir)
    proc.returncode


def run_make(build_dir: pathlib.Path, argv: list[str]) -> int:
    proc = subprocess.run(['make'] + argv, cwd=build_dir)
    proc.returncode


if __name__ == '__main__':
    sys.exit(main())
