# build
Script that uses git, cmake and make to create C and C++ projects.

## Getting started

Run `build --init PROJECTNAME` to create a new project. This will create a new git repository, generate a CMakeLists.txt, a .gitignore, and skeleton source code from a template. It then runs cmake and make to build the project right away:

```
$ build --init MyProject
Running git init
...
Generating CMakeLists.txt
Generating .gitignore
Running cmake .
...
Running make
...
$ ls
build.dir/  build.info  CMakeLists.txt  MyProject*  src/
$ cat src/main.cpp
#include <iostream>

int main(int argc, char* argv[])
{
    std::cout << "Hello world!" << std::endl;
    return 0;
}

$ ./MyProject
Hello world!
$
```

By default `build --init` creates a C++ project. You can change this using the `--template` argument. Run `build --listtemplates` to see available templates.

## Adding libraries and files

The build.info file contains the targets with required source files and libraries. Change this to easily add new libaries to your project.

```
$ cat build.info
{
    "projectname": "MyProject",
    "builddir": "build.dir",
    "flags": "-std=c++14 -g -Wall -Werror",
    "targets": [
        {
            "name": "MyProject",
            "type": "executable",
            "srcs": [ "src/*.cpp" ],
            "include_dirs": [ "src" ]
        }
    ]
}
```

Once a project is created run `build` with to build any changes to existing source files.
It will also regenerate CMakeLists.txt if build.info changes or if new source files are added (based on the `srcs` value in build.info).


Run `build -h` for usage information.
