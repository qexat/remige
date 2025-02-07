# Remige

some ~~fast~~ interpreter maybe

## Build & run

```sh
### Python >=3.12 required ###
# Create a virtual environment
virtualenv .venv -ppython312 && source .venv/bin/activate
# Install the ulna build system
env -S pip install ulna
# Build
ulna build
# Execute
remige
```

For detailed information about ulna, check out the project's [README](./ulna/README.md).
