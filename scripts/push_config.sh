#!/bin/bash

set -eux

if [ $# -ne 1 ];
    then echo "illegal number of parameters"
else
    scp "$1" mathbot:config.json
fi
