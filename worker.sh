#!/bin/bash
#--- Startup Script for VEDA Worker --#

echo "
* Video Worker *
"

ROOTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd ${ROOTDIR}

# Get vars from yaml
QUEUE=$(cat ${ROOTDIR}/instance_config.yaml | grep celery_worker_queue)
QUEUE=${QUEUE#*: }
CONCUR=$(cat ${ROOTDIR}/instance_config.yaml | grep celery_threads)
CONCUR=${CONCUR#*: }
echo $QUEUE
echo $CONCUR

python ${ROOTDIR}/video_worker/celeryapp.py worker --loglevel=info --concurrency=${CONCUR} -Q ${QUEUE} -n worker.%h
