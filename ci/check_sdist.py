#!/usr/bin/env python
# Check that sdist contains everything we expect

import sys
import tarfile

expected_files = [
    "docs/requirements.txt",
    "jsx/package.json",
    "package.json",
    "README.md",
]

assert len(sys.argv) == 2, "Expected one file"
print(f"Checking {sys.argv[1]}")

tar = tarfile.open(name=sys.argv[1], mode="r:gz")
try:
    # Remove leading jupyterhub-VERSION/
    filelist = {f.partition('/')[2] for f in tar.getnames()}
finally:
    tar.close()

for e in expected_files:
    assert e in filelist, f"{e} not found"

print("OK")
