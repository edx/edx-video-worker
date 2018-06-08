"""
Determines ffmpeg command based on video and encode information.

-resolution (frame size)
-CRF (increase for lower bitrate videos)

This is built to generate commands for a very small number of encodes and is not a substitute
for knowledgable use of ffmpeg if one's intention is to broaden use beyond the very limited set of
endpoints the edX platform provides

input, via two classes, encode and video, which can be generated either via the node independently
or via celery connection to VEDA (VEDA will send video_id and encode_profile via Celery queue)
"""

import logging
import os
import sys

from video_worker.utils import get_config
from global_vars import ENCODE_WORK_DIR, TARGET_ASPECT_RATIO, ENFORCE_TARGET_ASPECT

logger = logging.getLogger(__name__)


class CommandGenerate:

    def __init__(self, VideoObject, EncodeObject, **kwargs):
        self.settings = kwargs.get('settings', self.settings_setup())
        self.VideoObject = VideoObject
        self.EncodeObject = EncodeObject
        self.jobid = kwargs.get('jobid', None)
        self.workdir = kwargs.get('workdir', None)
        self.ffcommand = []

    def settings_setup(self):
        return get_config()

    def generate(self):
        """
        Generate command for ffmpeg lib
        """
        if self.VideoObject is None:
            logger.error('Command generation: No Video object')
            return

        if self.EncodeObject is None:
            logger.error('Command generation: No Encode object')
            return

        if self.workdir is None:
            if self.jobid is None:
                self.workdir = ENCODE_WORK_DIR
            else:
                self.workdir = os.path.join(ENCODE_WORK_DIR, self.jobid)

        # These build the command, and, unfortunately, must be in order
        self._call()
        self._codec()

        if ENFORCE_TARGET_ASPECT:
            self._scalar()

        self._bitdepth()
        self._passes()
        self._destination()
        return ' '.join(self.ffcommand)

    def _call(self):
        """
        Begin Command Proper
        """
        self.ffcommand.append(self.settings['ffmpeg_compiled'])
        self.ffcommand.append('-hide_banner')
        self.ffcommand.append('-y')
        self.ffcommand.append('-i')
        if self.VideoObject.veda_id is not None and len(self.VideoObject.mezz_extension) > 0:
            self.ffcommand.append(os.path.join(
                self.workdir,
                '.'.join((
                    self.VideoObject.veda_id,
                    self.VideoObject.mezz_extension
                ))
            ))
        elif len(self.VideoObject.mezz_extension) > 0:
            self.ffcommand.append(os.path.join(
                self.workdir,
                '.'.join((
                    os.path.basename(self.VideoObject.mezz_filepath).split('.')[0],
                    self.VideoObject.mezz_extension
                ))
            ))
        else:
            self.ffcommand.append(os.path.join(
                self.workdir,
                os.path.basename(self.VideoObject.mezz_filepath)
            ))
        if self.EncodeObject.filetype != 'mp3':
            self.ffcommand.append('-c:v')
        else:
            self.ffcommand.append('-c:a')

    def _codec(self):
        """
        This, as an addendum to the relatively simple deliverables to edX, is only intended to
        work with a few filetypes (see config)
        """
        if self.ffcommand is None:
            return

        if self.EncodeObject.filetype == 'mp4':
            self.ffcommand.append('libx264')
        elif self.EncodeObject.filetype == 'webm':
            self.ffcommand.append('libvpx')
        elif self.EncodeObject.filetype == 'mp3':
            self.ffcommand.append('libmp3lame')

    def _scalar(self):
        if self.ffcommand is None:
            return
        if not ENFORCE_TARGET_ASPECT:
            return
        if self.EncodeObject.filetype == 'mp3':
            return

        # Padding (if requested and needed)
        # letter/pillarboxing Command example: -vf pad=720:480:0:38
        # (target reso, x, y)

        horiz_resolution = int(float(self.EncodeObject.resolution) * TARGET_ASPECT_RATIO)

        # BITRATE as int
        if self.VideoObject.mezz_bitrate != 'Unparsed' and len(self.VideoObject.mezz_bitrate) > 0:
            mezz_parse_bitrate = self.VideoObject.mezz_bitrate.strip().split(' ')[0]
        else:
            mezz_parse_bitrate = None

        # RESOLUTION as int
        if self.VideoObject.mezz_resolution != 'Unparsed' and len(self.VideoObject.mezz_resolution) > 0:
            mezz_vert_resolution = int(self.VideoObject.mezz_resolution.strip().split('x')[1])
            mezz_horiz_resolution = int(self.VideoObject.mezz_resolution.strip().split('x')[0])
        else:
            mezz_vert_resolution = None
            mezz_horiz_resolution = None

        # Aspect Ratio as float
        if mezz_vert_resolution is not None and mezz_horiz_resolution is not None:
            mezz_aspect_ratio = float(mezz_horiz_resolution) / float(mezz_vert_resolution)
        else:
            mezz_aspect_ratio = None

        # Append commands

        # Improve conditions below - See EDUCATOR-1071
        # An `and` condition would be prefered - See EDUCATOR-1071
        if mezz_aspect_ratio is not None or float(mezz_aspect_ratio) == float(TARGET_ASPECT_RATIO):
            aspect_fix = False

        # Improve this condition - See EDUCATOR-1071
        # This if condition would never be True because if above is false it means mezz_aspect_ratio is None
        # which only happens if mezz_vert_resolution and mezz_horiz_resolution are None.
        elif mezz_vert_resolution == 1080 and mezz_horiz_resolution == 1440:
            aspect_fix = False
        else:
            aspect_fix = True

        # This would raise TypeError when doing on  int(None) for mezz_vert_resolution - See EDUCATOR-1071
        if int(self.EncodeObject.resolution) == int(mezz_vert_resolution):
            resolution_fix = False
        else:
            resolution_fix = True

        if not aspect_fix and not resolution_fix:
            return

        if not aspect_fix and resolution_fix:
            self.ffcommand.append('-vf')
            self.ffcommand.append('scale=' + str(horiz_resolution) + ':' + str(self.EncodeObject.resolution))

        # Flow would never reaches this line due to TypeError on mezz_aspect_ratio when it is None - See EDUCATOR-1071
        elif aspect_fix:
            if mezz_aspect_ratio > self.settings['target_aspect_ratio']:
                # LETTERBOX
                scalar = (int(self.EncodeObject.resolution) - (horiz_resolution / mezz_aspect_ratio)) / 2

                self.ffcommand.append('-vf')
                scalar_command = 'scale=' + str(horiz_resolution)
                scalar_command += ':' + str(int(self.EncodeObject.resolution) - (int(scalar) * 2))
                scalar_command += ',pad=' + str(horiz_resolution) + ':' + str(self.EncodeObject.resolution)
                scalar_command += ':0:' + str(int(scalar))
                self.ffcommand.append(scalar_command)

            if mezz_aspect_ratio < self.settings['target_aspect_ratio']:
                # PILLARBOX
                scalar = (horiz_resolution - (mezz_aspect_ratio * int(self.EncodeObject.resolution))) / 2

                self.ffcommand.append('-vf')
                scalar_command = 'scale=' + str(horiz_resolution - (int(scalar) * 2))
                scalar_command += ':' + str(self.EncodeObject.resolution)
                scalar_command += ',pad=' + str(horiz_resolution) + ':' + str(self.EncodeObject.resolution)
                scalar_command += ':' + str(int(scalar)) + ':0'
                self.ffcommand.append(scalar_command)

    def _bitdepth(self):
        """
        TODO: add tables translating CRF to bitrate,
        some experimenting is needed - a lossless solution
        to low bitdepth videos can be in the offing, but for now,
        stock
        """
        return

    def _passes(self):
        """
        Passes / 2 for VBR
        1 for CRF
        1 for WEBM
        """
        if self.EncodeObject.filetype == 'webm':
            self.ffcommand.append('-b:v')
            if self.EncodeObject.rate_factor > self.VideoObject.mezz_bitrate:
                self.ffcommand.append(str(self.VideoObject.mezz_bitrate) + 'k')
                self.ffcommand.append('-minrate')
                self.ffcommand.append('10k')
                self.ffcommand.append('-maxrate')
                self.ffcommand.append(str(int(float(self.VideoObject.mezz_bitrate) * 1.25)) + 'k')
                self.ffcommand.append('-bufsize')
                self.ffcommand.append(str(int(self.VideoObject.mezz_bitrate) - 24) + 'k')
            else:
                self.ffcommand.append(str(self.EncodeObject.rate_factor) + 'k')
                self.ffcommand.append('-minrate')
                self.ffcommand.append('10k')
                self.ffcommand.append('-maxrate')
                self.ffcommand.append(str(int(float(self.EncodeObject.rate_factor) * 1.25)) + 'k')
                self.ffcommand.append('-bufsize')
                self.ffcommand.append(str(int(self.EncodeObject.rate_factor) - 24) + 'k')

        elif self.EncodeObject.filetype == 'mp4':
            crf = str(self.EncodeObject.rate_factor)
            self.ffcommand.append('-crf')
            self.ffcommand.append(crf)

        elif self.EncodeObject.filetype == 'mp3':
            self.ffcommand.append('-b:a')
            self.ffcommand.append(str(self.EncodeObject.rate_factor) + 'k')

        # for a possible two-pass encodes state:
        # need: two-pass global bool
        #     ffmpeg -y -i -pass 1 -c:a libfdk_aac -b:a 128k -passlogfile ${LOGFILE} \
        #     -f mp4 /dev/null && ${FFCOMMAND} -pass 2 -c:a libfdk_aac -b:a 128k ${DESTINATION}

    def _destination(self):
        if self.EncodeObject.filetype == 'mp4':
            self.ffcommand.append('-movflags')
            self.ffcommand.append('faststart')
        elif self.EncodeObject.filetype == 'webm':
            # This is WEBM = 1 Pass
            self.ffcommand.append('-c:a')
            self.ffcommand.append('libvorbis')

        if self.VideoObject.veda_id is not None:
            self.ffcommand.append(
                os.path.join(
                    self.workdir,
                    self.VideoObject.veda_id + '_' + self.EncodeObject.encode_suffix + '.' + self.EncodeObject.filetype
                )
            )
        else:
            self.ffcommand.append(
                os.path.join(
                    self.workdir,
                    '%s_%s.%s' % (
                        os.path.basename(self.VideoObject.mezz_filepath).split('.')[0],
                        self.EncodeObject.encode_suffix,
                        self.EncodeObject.filetype
                    )
                )
            )
