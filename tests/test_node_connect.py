
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_worker.config import WorkerSetup
"""
test connection to celery cluster

"""


class TestCeleryConnect(unittest.TestCase):

    def setUp(self):
        self.WS = WorkerSetup()
        if os.path.exists(self.WS.instance_yaml):
            self.WS.run()
        self.settings = self.WS.settings_dict

    def test_celery_setup(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        salient_variables = [
            'celery_app_name',
            'celery_receiver_queue',
            'rabbitmq_user',
            'rabbitmq_pass',
            'rabbitmq_broker'
        ]

        for s in salient_variables:
            self.assertFalse(len(self.settings[s]) == 0)

    @unittest.skip("not implemented")
    def test_celery_credentials(self):
        if not os.path.exists(self.WS.instance_yaml):
            self.assertTrue(True)
            return None

        """
        This is yuck, but I am in a hurry
        """
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        worker_call = 'python celeryapp.py worker --loglevel=info --concurrency=1 -Q ' \
            + str(self.settings['celery_receiver_queue'])
        a1 = subprocess.Popen(
            worker_call, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )

        print '** 10 sec of sleep while node connects to cluster **'
        time.sleep(10)
        a1.kill()  # Otherwise it's forever

        test_command = 'Connected to amqp://' + self.settings['rabbitmq_user'] + \
            ':**@' + self.settings['rabbitmq_broker'] + ':5672//'

        for line in iter(a1.stdout.readline, b''):
            print line
            if test_command in line:
                self.assertTrue(True)
                return None

        self.assertFalse(True)


def main():
    unittest.main()

if __name__ == '__main__':
    sys.exit(main())
