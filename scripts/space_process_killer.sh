#!/bin/bash

# --- #
# Shell Space Alerter
# --- #

USED_PCTG=$( df | awk '{print $5}'  | head -2 | tail -1 )
echo "${USED_PCTG//%}"

if [ "${USED_PCTG//%}" > 90 ]
    then
    DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    python $DIR/video_worker/reporting.py
    sudo kill $( ps ax | grep celery | awk '{print $1}' )
fi
