"""
Script to split the data into train and valid sets. Train 90% and valid 10%.
"""
import os
import random

data_dir = "/workspaces/BUIBert/robotframework/Web/frontend/data/to_buibert"
train_dir = "/workspaces/BUIBert/bertbui/static_popular/train"
valid_dir = "/workspaces/BUIBert/bertbui/static_popular/valid"

# Get all the *.json files in the data directory recursively
files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(data_dir) for f in filenames if os.path.splitext(f)[1] == '.json']

# Shuffle the files
random.shuffle(files)

# Split the files into train and valid
train_files = files[:int(len(files)*0.9)]
valid_files = files[int(len(files)*0.9):]

# Copy the files to the train and valid directories
for file in train_files:
    os.system(f"cp '{file}' '{train_dir}'")

for file in valid_files:
    os.system(f"cp '{file}' '{valid_dir}'")