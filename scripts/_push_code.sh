#!/bin/bash

set -eux

cd ~

if [ ! -d "mathbot" ]; then
    git clone "https://github.com/DXsmiley/mathbot.git"
    cd mathbot/mathbot
    git checkout deploy-on-vps
    pm2 start "../scripts/pm2_main.sh" --name mathbot
    cd ~
fi

cd mathbot

git checkout deploy-on-vps
git fetch
git pull

pm2 restart mathbot
