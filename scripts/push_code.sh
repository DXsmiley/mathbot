#!/bin/bash
cd "$( dirname "${BASH_SOURCE[0]}" )"
ssh mathbot 'bash -s' < "./_push_code.sh"
