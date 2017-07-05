
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.__init__ import VideoWorker
from video_worker.abstractions import Video, Encode
from video_worker.config import WorkerSetup
from video_worker.generate_encode import CommandGenerate
from video_worker.reporting import ErrorObject

"""
This represents an end-to-end 'master' test of openVEDA


"""


class TestEndtoEnd(unittest.TestCase):

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

    @unittest.skip("not implemented")
    def test_intake(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        """
        copied from __init__
        """
        self.VW.VideoObject = Video(
            veda_id=self.VW.veda_id
        )
        self.VW.VideoObject.activate()
        self.assertTrue(self.VW.VideoObject.valid)
        self.VW.settings = self.settings

        self.VW._engine_intake()
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

        self._update_api()
        self._GENERATE_ENCODE()
        self._execute_encode()
        self._VALIDATE_ENCODE()
        if self.encoded is True:
            self._DELIVER_FILE()

        if self.endpoint_url is not None:
            """
            Integrate with main
            """
            final_name = self.output_file
            celery_task_fire.deliverable_route.apply_async(
                (final_name, ),
                queue='transcode_stat'
            )

    def tearDown(self):
        """
        Clean up workdir
        """
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

    @unittest.skip("not implemented")
    def determine_config(self):
        """
        Determine the configuration of the node
        based on tests
        """
        if self.Settings.VAL_ATTACH is True:
            """Off if off in settings"""
            self.val = ConnectionTest(
                Settings=self.Settings,
                val_test=True
            ).passed

        if self.Settings.NODE_VEDA_ATTACH is True:
            """Off if off in settings"""
            self.veda = ConnectionTest(
                Settings=self.Settings,
                veda_test=True
            ).passed
            self.celery = CeleryConnect(
                Settings=self.Settings
            ).passed

        AC = AssetConnection(Settings=self.Settings)

        if AC.passed is False:
            pass
        else:
            self.ingest = AC.ingest
            self.hotstore = AC.hotstore
            self.deliver = AC.deliver

        # TODO: MAKE THIS PRETTIER
        self.report_config()

    @unittest.skip("not implemented")
    def intake_test(self):
        """
        Generate Ingest
        """
        if self.mezz_video is None:
            print 'KEYKEY'
        if self.veda is False:
            FI = Ingest(
                Settings=self.Settings,
                mezz_video=self.mezz_video
            )
            if self.ingest is False and self.hotstore is True:
                """
                Copy FROM Hotstore
                """
                FI.hotstore = True

            if self.ingest is True:
                """
                Copy TO Hotstore and destroy original in Ingest dir
                """
                FI.hotstore = True
                FI.ingest = True
        else:
            FI = Ingest(
                Settings=self.Settings,
                mezz_video=self.Settings.TEST_VIDEO_ID
            )
            """
            Will always be hotstore true and ingest false, so leaving edge cases
            """
            FI.hotstore = True
            FI.ingest = False

        FI.activate()
        self.AbstractionLayer.VideoObject = FI.VideoObject
        print self.AbstractionLayer.VideoObject.mezz_filepath
        return FI.passed

    @unittest.skip("not implemented")
    def qa_test(self):
        """
        QA the test video
        """
        Q1 = QAVideo(
            filepath=self.AbstractionLayer.VideoObject.mezz_filepath,
            VideoObject=self.AbstractionLayer.VideoObject,
            mezz_file=True
        )
        self.AbstractionLayer.valid = Q1.activate()
        return self.AbstractionLayer.valid

    @unittest.skip("not implemented")
    def generate_encodes(self):
        """
        Generate the (shell) command / Encode Object
        and tack it into the AbstractionLayer Object
        """
        if self.AbstractionLayer.VideoObject is None:
            ErrorObject(
                method=self,
                message='Encode Gen Fail\nNo Video Object'
            )
            return False

        if self.veda is True:
            """
            If this is a VEDA-Attached Node, it'll only receive one enc command
            at a time, so we'll just test the one
            """
            E1 = Encode(
                Settings=self.Settings,
                VideoObject=self.AbstractionLayer.VideoObject,
                profile_name=self.Settings.TEST_ENCODE_PROFILE
            )
            E1.activate()
            self.AbstractionLayer.Encodes.append(E1)

        else:
            """
            Get all the NODE_ENCODE_PROFILES from node_config
            """
            for key, entry in self.Settings.NODE_ENCODE_PROFILES.iteritems():
                E1 = Encode(
                    Settings=self.Settings,
                    VideoObject=self.AbstractionLayer.VideoObject,
                    profile_name=key
                )
                E1.activate()
                self.AbstractionLayer.Encodes.append(E1)

        for E in self.AbstractionLayer.Encodes:
            CG = CommandGenerate(
                Settings=self.Settings,
                VideoObject=self.AbstractionLayer.VideoObject,
                EncodeObject=E
            )
            CG.activate()
            E.ffcommand = CG.ffcommand

        for E in self.AbstractionLayer.Encodes:
            if E.ffcommand is None or len(E.ffcommand) == 0:
                ErrorObject(
                    method=self,
                    message='Encode Gen Fail\nCommand Gen Fail'
                )
                return False

        return True

    @unittest.skip("not implemented")
    def transcode_test(self):
        """
        Run the commands, which tests for a file and returns
        a bool and the filename
        """
        for E in self.AbstractionLayer.Encodes:
            FF = CommandExecute(
                ffcommand=E.ffcommand,
            )
            E.complete = FF.activate()
            E.output_file = FF.output
            # just being polite
            print('')
            if E.complete is False:
                return False

        self.AbstractionLayer.complete = True
        return True

    @unittest.skip("not implemented")
    def deliver_qa_test(self):
        for E in self.AbstractionLayer.Encodes:
            if not os.path.exists(E.output_file):
                return False
            Q1 = QAVideo(
                filepath=E.output_file,
                VideoObject=self.AbstractionLayer.VideoObject,
                mezz_file=False
            )
            if Q1.activate() is False:
                return False
        return True

    @unittest.skip("not implemented")
    def deliver_test(self):
        if self.deliver is False:
            return False
        for E in self.AbstractionLayer.Encodes:
            if E.complete is False:
                return False
            if not os.path.exists(E.output_file):
                return False
            """
            Deliver Here
            """
            D1 = Deliverable(
                Settings=self.Settings,
                VideoObject=self.AbstractionLayer.VideoObject,
                EncodeObject=E
            )
            passed = D1.activate()

            if passed is False:
                return False

            E.upload_filesize = D1.upload_filesize
            E.hash_sum = D1.hash_sum
            E.endpoint_url = D1.endpoint_url
        return True

    @unittest.skip("not implemented")
    def val_api_test(self):
        if self.Settings.VAL_ATTACH is True:
            self.AbstractionLayer.VideoObject.course_url = 'TESTURL/TEST'
            self.AbstractionLayer.VideoObject.val_id = self.Settings.TEST_VAL_ID
            for E in self.AbstractionLayer.Encodes:
                V1 = VALData(
                    Settings=self.Settings,
                    VideoObject=self.AbstractionLayer.VideoObject,
                    EncodeObject=E
                )
                passed = V1.activate()
                if passed is False:
                    return False
            return True
        else:
            return False

    @unittest.skip("not implemented")
    def veda_status_test(self):
        if self.Settings.NODE_VEDA_ATTACH is True:
            V2 = VEDAData(
                Settings=self.Settings,
                VideoObject=self.AbstractionLayer.VideoObject,
                video_status=True
            )
            passed = V2.activate()
            return passed
        else:
            return False

    @unittest.skip("not implemented")
    def veda_url_test(self):
        if self.Settings.NODE_VEDA_ATTACH is True:
            for E in self.AbstractionLayer.Encodes:
                V2 = VEDAData(
                    Settings=self.Settings,
                    VideoObject=self.AbstractionLayer.VideoObject,
                    EncodeObject=E
                )
                passed = V2.activate()
                if passed is False:
                    return False
            return True
        else:
            return False

    @unittest.skip("not implemented")
    def cleanup_directory(self):
        """
        This is too broad a brush for everyday use, but for testing is fine
        """
        for file in os.listdir(self.Settings.VEDA_WORK_DIR):
            os.remove(os.path.join(self.Settings.VEDA_WORK_DIR, file))


def main():
    """
    Prior Implementation

        # mezz_video = kwargs.get('mezz_video', None)

    if Settings == None:
        S1 = Settings(
            node_config = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'settings.py'
                )
            )
        S1.activate()
    else:
        S1 = Settings

    EE1 = EndtoEnd(
        Settings=S1
        )
    if mezz_video == None:
        EE1.mezz_video=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'test_videofiles',
            S1.TEST_VIDEO_FILE
            )
    else:
        EE1.mezz_video = mezz_video

    EE1.determine_config()

    test_name = 'E2E : INGEST'
    passed = EE1.intake_test()
    TestReport(passed, test_name)

    test_name = 'E2E : QA'
    passed = EE1.qa_test()
    TestReport(passed, test_name)

    test_name = 'E2E : Command Gen'
    passed = EE1.generate_encodes()
    TestReport(passed, test_name)

    test_name = 'E2E : Command Run'
    passed = EE1.transcode_test()
    TestReport(passed, test_name)

    test_name = 'E2E : Deliver QA'
    passed = EE1.deliver_qa_test()
    TestReport(passed, test_name)

    if len(S1.DELIVERY_ENDPOINT) > 0:
        test_name = 'E2E : Deliver File'
        passed = EE1.deliver_test()
        TestReport(passed, test_name)

    if S1.VAL_ATTACH is True:

        test_name = 'E2E : VAL Data'
        passed = EE1.val_api_test()
        TestReport(passed, test_name)

    if S1.NODE_VEDA_ATTACH is True:
        test_name = 'E2E : VEDA Video Status'
        passed = EE1.veda_status_test()
        TestReport(passed, test_name)

        test_name = 'E2E : VEDA URL'
        passed = EE1.veda_url_test()
        TestReport(passed, test_name)

    EE1.cleanup_directory()
    """
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
