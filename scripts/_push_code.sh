#!/bin/bash

set -eux

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd ~

LAST_SHARD=$(( $(jq -rM '.shards.total' config.json) - 1 ))

if [ ! -d "mathbot" ]; then
    git clone "https://github.com/DXsmiley/mathbot.git"
fi

cd mathbot

git checkout master
git fetch
git pull

echo "Stopping shards"
pm2 stop all

export PIPENV_YES=1
pipenv install

pm2 start "./scripts/startup_queue.sh" --name "startup-queue"

echo "Starting shards again"
for i in $(seq 0 $LAST_SHARD)
do
    pm2 start "./scripts/pm2_main.sh" --name "mathbot-$i" -- $i
done
