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

### Troubleshooting

#### When I run `build.py`, a `ModuleNotFoundError` error is shown

1. Make sure you created a virtual environment.
2. Verify that you have activated it ; a `VIRTUAL_ENV` environment variable should be set.
3. Check that you have installed the builder dependencies in the virtual environment.

#### When I run `build.py`, it errors with the message "no virtual environment detected"

This means that `build.py` was unable to find the `VIRTUAL_ENV` environment variable. Make sure that it is indeed set, and that you don't have any program that might interfere or change the environment in the background.
