# Remige

some ~~fast~~ interpreter maybe

## Build & run

```sh
### Python >=3.12 required ###
# Create a virtual environment
virtualenv .venv -ppython312 && source .venv/bin/activate
# Install the builder dependencies
env -S pip install -r builder-deps.txt
# Run the builder
./build.py
# Execute Remige
remige
```

### Builder options

- `--compiler <NAME>`: selects the compiler to use to build Remige. Supported compilers: `gcc`. (default: `gcc`)
- `--help`/`-h`: prints the builder options.
- `--mode <MODE>`: this impacts the flags and arguments passed to the compiler. Supported modes: `release`, `development`. (default: `development`)
- `--verbose`: shows more output. Useful if the compiler threw an error.

> Why no short form for flags/arguments?

I like explicitness. If you can waste time caring about this project, you surely can bear typing a few more keystrokes.

### Troubleshooting

#### When I run `build.py`, a `ModuleNotFoundError` error is shown

1. Make sure you created a virtual environment.
2. Verify that you have activated it ; a `VIRTUAL_ENV` environment variable should be set.
3. Check that you have installed the builder dependencies in the virtual environment.

#### When I run `build.py`, it errors with the message "no virtual environment detected"

This means that `build.py` was unable to find the `VIRTUAL_ENV` environment variable. Make sure that it is indeed set, and that you don't have any program that might interfere or change the environment in the background.
