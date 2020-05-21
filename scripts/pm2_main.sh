#!/bin/bash

set -eux

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd ~/mathbot

pipenv install
pipenv shell
cd mathbot
echo "we'd run the bot at this point..."
# python entrypoint.py "~/config.json"
