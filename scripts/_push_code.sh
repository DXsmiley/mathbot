#!/bin/bash

set -eux

cd ~

if [ ! -d "mathbot" ]; then
    git clone "https://github.com/DXsmiley/mathbot.git"
    cd mathbot/mathbot
    pm2 start "../scripts/pm2_main.sh" -name mathbot
fi

cd mathbot

git checkout deploy-on-vps
git pull

pm2 restart mathbot
