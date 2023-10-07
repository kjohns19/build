# build

A simple wrapper around `cmake`, `ctest` and `make`.

By default, `build` with run `cmake` followed by `make`. The build files will be put in a
`build.dir` directory.

If you pass `--sudo`, it will run `sudo make` instead to run the `make` command as root (e.g. for
installing libraries with `build --sudo install`.

Run `ctest` with `build ctest`

Any extra arguments are passed directly to the command (`make` or `ctest`)
