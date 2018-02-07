"""
One off script to force re-encode 422 (satellite encoded) videos for iOS/Android decoded playback

"""

'''
Normal Command
ffmpeg -hide_banner -y -i /Users/gregmartin/ENCODE_WORKDIR/UBCSC1SC2017-V007900.mov \
-c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4

Should Read
-pix_fmt yuv420p
ffmpeg -hide_banner -y -i /Users/gregmartin/ENCODE_WORKDIR/UBCSC1SC2017-V007900.mov \
-c:v libx264 -vf scale=640:360 -crf 27 -movflags faststart ${ENCODE_WORKDIR}/UBCSC1SC2017-V007900_MB2.mp4


'''