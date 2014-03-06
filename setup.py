#!/usr/bin/env python

from setuptools import setup


def readreq(filename):
    result = []
    with open(filename) as f:
        for req in f:
            req = req.partition('#')[0].strip()
            if not req:
                continue
            result.append(req)
    return result


def readfile(filename):
    with open(filename) as f:
        return f.read()

setup(
    name='heyu',
    version='0.1.0',
    author='Kevin L. Mitchell',
    author_email='klmitch@mit.edu',
    url='http://github.com/klmitch/heyu',
    description='Self-Notification Utility',
    long_description=readfile('README.rst'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Environment :: No Input/Output (Daemon)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=['heyu'],
    requires=readreq('requirements.txt'),
    tests_require=readreq('test-requirements.txt'),
    entry_points={
        'console_scripts': [
            'heyu-notify = heyu.submitter:send_notification.console',
            'heyu-hub = heyu.hub:start_hub.console',
            'heyu-notifier = heyu.notifier:notification_server.console',
        ],
        'heyu.notifier': [
            'stdout = heyu.notifier:stdout_notification_driver',
            'file = heyu.notifier:file_notification_driver',
            'script = heyu.notifier:script_notification_driver',
        ],
    },
)
