# ulna

ulna is the build system for Remige. It's designed to suit my needs for the project, so it's simple with no bloat or fuss.

If you happen to use it, don't. If you need a feature that ulna does not support, use a more powerful build system instead. **Do NOT open a feature request.**

## Commands

### Build

Build the current project.

```sh
ulna build
```

### Options

- `--help`/`-h`: prints the builder options.
- `--mode <MODE>`: this impacts the flags and arguments passed to the compiler. Supported modes: `release`, `development`. (default: `development`)
- `--verbose`: shows more output. Useful if the compiler threw an error.

### Examples

```sh
ulna build
ulna build --mode release
ulna build --verbose
```

## Configuration

ulna can build simple C projects that have a `ulna-project.toml` at their root.

### Scheme

`program.name` is the only field required.

```txt
[program]
name : identifier  # required
description : string

[dependencies]
include_dirs : list of string
include_shared : list of string

[build]
compiler : supported compiler name
additional_flags : list of string
```

#### Types

- `identifier`: a sequence of lowercase letters or underscores.

## Troubleshooting

### When I run `ulna build`, a `ModuleNotFoundError` error is shown

1. Make sure you have created a virtual environment.
2. Verify that you have activated it ; a `VIRTUAL_ENV` environment variable should be set.
3. Check that you have installed ulna in the virtual environment.

### When I run `ulna build`, it errors with the message "no virtual environment detected"

This means that ulna was unable to find the `VIRTUAL_ENV` environment variable. Make sure that it is indeed set, and that you don't have any program that might interfere or change the environment in the background.
