#!/bin/sh
SCRIPT_PATH="`dirname $0`"
cd ${SCRIPT_PATH}
source /var/spool/omnibox/omniboxenv/bin/activate
python pyurlfetcher.py "$@"
deactivate