
from __future__ import absolute_import
from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='edx-video-worker',
    version='1.0',
    description='Worker node for edx-video-pipeline',
    long_description=readme(),
    url='http://github.com/edx/edx-video-worker',
    author='',
    author_email='',
    license='',
    packages=['video_worker'],
    dependency_links=['https://github.com/yro/chunkey.git'],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst', '*.yaml'],
    },
    install_requires=[
        'boto==2.39.0',
        'requests==2.10.0',
        'celery==4.1.1',
        'pyyaml==3.11',
        'nose==1.3.3',
        'newrelic',
        'redis==2.10.6',
	'kombu==4.2.2post1',
	'amqp==2.3.2',
	'vine==1.3.0'
    ],
    zip_safe=False
)
