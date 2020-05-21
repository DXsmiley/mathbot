#!/bin/bash

cd ~

set -eux

export DEBIAN_FRONTEND=noninteractive

apt-get install curl -y
curl --version

apt-get install git -y
git --version

apt-get install software-properties-common -y
apt-get update

apt-add-repository ppa:deadsnakes/ppa
apt-get update
apt-get install python3.6 -y
apt-get install python3.6-dev -y

apt-get install python-pip -y
pip --version

pip install pipenv
pipenv --version

curl -sL https://deb.nodesource.com/setup_12.x | bash -
apt-get install nodejs -y
node --version

npm install pm2@4.4.0 -g

apt-get install build-essential -y

apt-get autoremove -y
