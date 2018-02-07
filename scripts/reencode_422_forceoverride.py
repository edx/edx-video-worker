"""
One off script to force re-encode 422 (satellite encoded) videos for iOS/Android decoded playback

"""

'''
Normal Command
ffmpeg -hide_banner -y -i ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900.mov \
-c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4

Should Read
ffmpeg -hide_banner -y -i ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900.mov \
-pix_fmt yuv420p -c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4


'''

import os


def download_file():
    pass


def encode_file():
    pass


def upload_file():
    pass

