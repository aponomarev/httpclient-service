#!/bin/sh
SCRIPT_PATH="`dirname $0`"
cd ${SCRIPT_PATH}
python pyurlfetcher.py "$@"