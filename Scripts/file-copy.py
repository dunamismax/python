#!/usr/bin/env python3

import os
import shutil
from pathlib import Path


def main():
    # Define source and destination directories.
    source_dir = Path("~/textual/docs/examples").expanduser()
    dest_dir = Path("~/textual-examples-py").expanduser()

    # Create the destination directory if it doesn't exist.
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Recursively find all .py files and copy them.
    for py_file in source_dir.rglob("*.py"):
        # Copy file to the destination directory.
        # If a file with the same name exists, it will be overwritten.
        shutil.copy2(py_file, dest_dir / py_file.name)

    print(f"Copied all .py files from {source_dir} to {dest_dir}")


if __name__ == "__main__":
    main()
