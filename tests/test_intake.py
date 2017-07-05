
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.__init__ import VideoWorker
from video_worker.abstractions import Video, Encode
from video_worker.config import WorkerSetup

"""
file intake test

"""


class TestIntake(unittest.TestCase):

    def setUp(self):
        self.WS = WorkerSetup()
        if os.path.exists(self.WS.instance_yaml):
            self.WS.run()
        self.settings = self.WS.settings_dict
        self.encode_profile = 'desktop_mp4'
        self.veda_id = 'XXXXXXXX2016-V00TEST'
        self.jobid = 'xx4xx'

        self.VW = VideoWorker(
            veda_id=self.veda_id,
            encode_profile=self.encode_profile,
            jobid=self.jobid
        )

    def test_intake(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        # copied from __init__
        self.VW.VideoObject = Video(
            veda_id=self.VW.veda_id
        )
        self.VW.VideoObject.activate()
        self.assertTrue(self.VW.VideoObject.valid)
        self.VW.settings = self.settings

        self.VW._engine_intake()
        print self.VW.VideoObject
        self.assertTrue(self.VW.VideoObject.valid)
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.VW.workdir,
                    self.VW.source_file
                )
            )
        )

        self.assertTrue(self.VW.VideoObject.valid)

    @unittest.skip("not implemented")
    def tearDown(self):
        if self.jobid is not None:
            shutil.rmtree(self.VW.workdir)
        else:
            os.remove(
                os.path.join(
                    self.VW.workdir,
                    self.VW.output_file
                )
            )
            os.remove(
                os.path.join(
                    self.VW.workdir,
                    self.VW.source_file
                )
            )


def main():
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
