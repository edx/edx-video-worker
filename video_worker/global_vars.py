#! user/bin/env python
"""
Globals

"""

import os

from video_worker.utils import get_config, ROOT_DIR

DEFAULT_ENCODE_WORK_DIR = os.path.join(ROOT_DIR, 'ENCODE_WORKDIR')
WORKER_CONFIG = get_config()
ENCODE_WORK_DIR = WORKER_CONFIG.get('ENCODE_WORK_DIR', DEFAULT_ENCODE_WORK_DIR)

NODE_TRANSCODE_STATUS = 'Active Transcode'
VAL_TRANSCODE_STATUS = 'transcode_active'

# Initially set to 16:9, can be changed
# We can also just ignore this,
# and push through video at original res/ar
# but you probably shouldn't ##

ENFORCE_TARGET_ASPECT = True
TARGET_ASPECT_RATIO = float(1920) / float(1080)

# The subbed out profile for HLS
HLS_SUBSTITUTE = 'mobile_low'

# For BOTO Multipart uploader
MULTI_UPLOAD_BARRIER = 2000000000
BOTO_TIMEOUT = 60

# Settings for testing
TEST_VIDEO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'test_videofiles'
)
TEST_VIDEO_FILE = 'OVTESTFILE_01.mp4'

# TERM COLORS
NODE_COLORS_BLUE = '\033[94m'
NODE_COLORS_GREEN = '\033[92m'
NODE_COLORS_RED = '\033[91m'
NODE_COLORS_END = '\033[0m'
