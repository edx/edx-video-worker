
from video_worker import VideoWorker

VW = VideoWorker()

VW = VideoWorker(
    veda_id='XXXXXXXXT114-V013800',
    encode_profile='hls',
    jobid='xxxxx'
)

VW.run()
