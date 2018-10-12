#!/bin/bash

# Bootstrap example script
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# - The first parameter for the Bootstrap Script is the USER.
USER=$1
if [ "$USER" == "" ]; then
    exit 1
fi
# ----------------------------------------------------------------------------


# This example script will do the following:
# - create one directory for the user $USER in a BASE_DIRECTORY (see below)
# - create a "tutorials" directory within and download and unzip the PythonDataScienceHandbook from GitHub

# Start the Bootstrap Process
echo "bootstrap process running for user $USER ..."

# Base Directory: All Directories for the user will be below this point
BASE_DIRECTORY=/volumes/jupyterhub

# User Directory: That's the private directory for the user to be created, if none exists
USER_DIRECTORY=$BASE_DIRECTORY/$USER

if [ -d "$USER_DIRECTORY" ]; then
    echo "...directory for user already exists. skipped"
    exit 0 # all good. nothing to do.
else
    echo "...creating a directory for the user: $USER_DIRECTORY"
    mkdir $USER_DIRECTORY

    # mkdir did not succeed?
    if [ $? -ne 0 ] ; then
        exit 1
    fi

    echo "...initial content loading for user ..."
    mkdir $USER_DIRECTORY/tutorials
    cd $USER_DIRECTORY/tutorials
    wget https://github.com/jakevdp/PythonDataScienceHandbook/archive/master.zip
    unzip -o master.zip
    rm master.zip
fi

exit 0
