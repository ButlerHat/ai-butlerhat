#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This script is used to resolve the conda secret.
It is used in the Dockerfile.
"""

import os
import sys
import argparse


parser = argparse.ArgumentParser(description='Resolve conda secret')
parser.add_argument('--token', default=None, help='GitHub access token')
args = parser.parse_args()

try:
    token = args.token if args.token else os.environ["GITHUB_ACCESS_TOKEN"]
except KeyError:
    print("Please set the environment variable GITHUB_ACCESS_TOKEN or set --token argument")
    sys.exit(1)

replacements = {
    "{GITHUB_ACCESS_TOKEN}": args.token
}

with open("conda-prod.yaml", "r", encoding="utf-8") as infile, open("conda_pass.yaml", "w", encoding="utf-8") as outfile:
    # Read the content of the input file
    filedata = infile.read()
    # Replace the variables with their values
    for src, target in replacements.items():
        filedata = filedata.replace(src, target)
    # Write the modified content to the output file
    outfile.write(filedata)
