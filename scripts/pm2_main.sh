#!/bin/bash

set -eux

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

./pull_redis_creds_from_heroku.sh "~/config.json"

cd ~/mathbot

export PIPENV_YES=1
pipenv install
cd mathbot
pipenv run python entrypoint.py ~/config.json
