"""
Quick and dirty error handling & logging

"""

from __future__ import absolute_import
import boto.ses
import os
import socket
import sys
import yaml


from .global_vars import *


class Credentials(object):

    def __init__(self):
        self.auth_yaml = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'instance_config.yaml'
        )
        self.auth_dict = self._AUTH()

    def _AUTH(self):
        if not os.path.exists(self.auth_yaml):
            return None
        with open(self.auth_yaml, 'r') as stream:
            try:
                return yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                return None


class Output(object):
    """
    Various reporting methods
    """
    @staticmethod
    def seconds_from_string(duration):

        hours = float(duration.split(':')[0])
        minutes = float(duration.split(':')[1])
        seconds = float(duration.split(':')[2])
        duration_seconds = (((hours * 60) + minutes) * 60) + seconds
        return duration_seconds

    @staticmethod
    def status_bar(process):
        """
        This is a little gross, but it'll get us a status bar thingy

        """
        fps = None
        duration = None
        while True:
            line = process.stdout.readline().strip()

            if line == '' and process.poll() is not None:
                break
            if fps is None or duration is None:
                if "Stream #" in line and " Video: " in line:
                    fps = [s for s in line.split(',') if "fps" in s][0].strip(' fps')

                if "Duration: " in line:
                    dur = line.split('Duration: ')[1].split(',')[0].strip()
                    duration = Output().seconds_from_string(duration=dur)

            else:
                if 'frame=' in line:
                    cur_frame = line.split('frame=')[1].split('fps=')[0].strip()
                    end_frame = float(duration) * float(fps.strip())
                    pctg = (float(cur_frame) / float(end_frame))
                    sys.stdout.write('\r')
                    i = int(pctg * 20.0)
                    sys.stdout.write("%s : [%-20s] %d%%" % ('Transcode', '=' * i, int(pctg * 100)))
                    sys.stdout.flush()

        # Just for politeness
        sys.stdout.write('\r')
        sys.stdout.write("%s : [%-20s] %d%%" % ('Transcode', '=' * 20, 100))
        sys.stdout.flush()


class EmailAlert(object):

    def __init__(self, **kwargs):
        self.auth_dict = Credentials().auth_dict
        self.message = kwargs.get('message', None)

        self.recipients = [
            'greg@edx.org',
        ]
        self.ipaddy = socket.gethostbyname(socket.gethostname())
        self.sender = 'veda-noreply@edx.org'

    def email(self):
        email_subject = '[ VEDA ALERTING ]'
        email_subject += ' : Worker Node Fault : '
        email_subject += self.ipaddy

        email_body = 'There has been a fault in a veda worker:\n'
        email_body += self.message + '.\n'
        email_body += self.ipaddy
        email_body += ' : This worker has been terminated\n'

        conn = boto.ses.connect_to_region('us-east-1')

        conn.send_email(
            self.sender,
            email_subject,
            email_body,
            self.recipients
        )


def main():
    """
    Just to sneak a peek
    """
    daemon_error = "Disk Free Space Alert"
    E2 = EmailAlert(message=daemon_error)
    E2.email()


if __name__ == '__main__':
    sys.exit(main())
