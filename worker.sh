#!/bin/bash
#--- Startup Script for VEDA Worker --#

echo "
* Video Worker *
"

ROOTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd ${ROOTDIR}

# if second parameter is passed than add its value to worker name
WORKER_NAME=worker.%h
if [ $# -eq 2 ]
  then
    WORKER_NAME=worker.$2.%h
fi

# Get vars from yaml
QUEUE=$(cat ${ROOTDIR}/instance_config.yaml | grep $1)
QUEUE=${QUEUE#*: }
CONCUR=$(cat ${ROOTDIR}/instance_config.yaml | grep celery_threads)
CONCUR=${CONCUR#*: }
echo $QUEUE
echo $CONCUR

python ${ROOTDIR}/video_worker/celeryapp.py worker --loglevel=info --concurrency=${CONCUR} -Q ${QUEUE} -n ${WORKER_NAME}
