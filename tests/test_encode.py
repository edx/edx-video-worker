
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.abstractions import Video, Encode
from video_worker.config import WorkerSetup
from video_worker.generate_encode import CommandGenerate

"""
test Encode Abstraction and Command Gen

"""


class Test_Encode_Command(unittest.TestCase):

    def setUp(self):
        self.WS = WorkerSetup()
        if os.path.exists(self.WS.instance_yaml):
            self.WS.run()
        self.settings = self.WS.settings_dict
        self.encode_profile = 'desktop_mp4'
        """
        Gen abstractions
        """
        # Video
        self.VideoObject = Video(
            veda_id='XXXXXXXX2016-V00TEST',
        )
        self.VideoObject.activate()

        # Encode
        self.E = Encode(
            VideoObject=self.VideoObject,
            profile_name=self.encode_profile
        )
        self.E.pull_data()
        self.ffcommand = None

    def test_generate_command(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        """
        Generate the (shell) command / Encode Object
        """
        self.assertTrue(self.VideoObject.valid is True)

        """
        Generate the Encode Object
        """
        self.E.pull_data()
        self.assertFalse(self.E.filetype is None)

        """
        Generate the (shell) command
        """
        self.ffcommand = CommandGenerate(
            VideoObject=self.VideoObject,
            EncodeObject=self.E
        ).generate()

        self.assertFalse(self.ffcommand is None)

        """
        TODO: More sophisticated encode tests
        """
        # TODO: pillarbox, letterbox commands
        # TODO: scalar commands
        # TODO: destination file, etc.


def main():
    unittest.main()


if __name__ == '__main__':
    sys.exit(main())
