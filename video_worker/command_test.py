"""
generate and fire a test task

"""

import os
import sys

from . import celeryapp


def fire_task():

    veda_id = 'XXXC93BC2016-V003600'
    encode_profile = 'desktop_mp4'
    jobid = 'testxx'

    celeryapp.worker_task_fire.apply_async(
        (veda_id, encode_profile, jobid),
        queue='test_node'
    )

if __name__ == '__main__':
    sys.exit(fire_task())
