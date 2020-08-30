#!/bin/bash

# This is a temporary hack to deal with Heroku rolling
# the redis creds occasionally. Once the redis server
# is migrated, this script can be deleted.

# First and only argument: path to config file


# Don't use -x here because it'll end up leaking
# creds into the logs
set -eu

API_KEY=$(jq -rM '.reboot.heroku_key' "$1")

REDIS_URL=$(curl --silent --max-time 10 -n -X GET 'https://api.heroku.com/apps/dxbot/config-vars' \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/vnd.heroku+json; version=3' \
    -H "Authorization: Bearer $API_KEY" \
    | jq '.REDIS_URL')

OUTPUT=$(jq -M ".keystore.redis.url = $REDIS_URL" "$1")
echo "$OUTPUT" > "$1"
