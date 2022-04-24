#!/bin/bash

set -eu

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd ~/mathbot/mathbot
exec pipenv run python -u startup_queue.py
