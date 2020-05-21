#!/bin/bash

set -eux

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd ~/mathbot

export PIPENV_YES=1
pipenv install
cd mathbot
pipenv run python entrypoint.py ~/config.json
