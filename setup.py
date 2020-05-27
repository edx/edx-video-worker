
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
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.8",
    ],
)
