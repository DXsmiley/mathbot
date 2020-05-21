#!/bin/bash

set -eux

cd ~/mathbot

pipenv install
pipenv shell
cd mathbot
echo "we'd run the bot at this point..."
# python entrypoint.py "~/config.json"
