#!/bin/bash

set -eu

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ $# -ne 1 ];
    then echo "illegal number of parameters"
    exit 1
fi

cd ~/mathbot

REDIS_URL=$(bash ./scripts/pull_redis_creds_from_heroku.sh "../config.json")

cd mathbot
exec pipenv run python -u entrypoint.py ~/config.json \
    "{\"shards\": {\"mine\": [$1]}, \"keystore\": {\"redis\": {\"url\": \"${REDIS_URL}\"}}}"
