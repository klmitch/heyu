#!/usr/bin/env python

import os
import sys

import setuptools


# Utility function to read the README file
def readfile(filename):
    with open(filename) as f:
        return f.read()


# Utility function to read requirements.txt files
def readreq(filename):
    result = []
    with open(filename) as f:
        for line in f:
            line = line.lstrip()

            # Process requirement file references
            if line.startswith('-r '):
                subfilename = line.split(None, 1)[-1].split('#', 1)[0].strip()
                if subfilename:
                    result += readreq(subfilename)
                continue

            # Strip out "-e" prefixes
            if line.startswith('-e '):
                line = line.split(None, 1)[-1]

            # Detect URLs in the line
            idx = line.find('#egg=')
            if idx >= 0:
                line = line[idx + 5:]

            # Strip off any comments
            line = line.split('#', 1)[0].strip()

            # Save the requirement
            if line:
                result.append(line.split('#', 1)[0].strip())

    return result


# Read in the requirements.txt file first
install_requires = readreq('requirements.txt')

# Determine what package we need to add to get asyncio
if sys.version_info >= (3, 4):
    pass
elif sys.version_info >= (3, 3):
    install_requires.append('asyncio')
elif sys.version_info >= (2, 6):
    install_requires.append('trollius')
else:
    sys.exit("No support for asyncio available in this version of Python")


setuptools.setup(
    name='heyu',
    version='0.2.0',
    author='Kevin L. Mitchell',
    author_email='kevin.mitchell@rackspace.com',
    url='http://github.com/klmitch/heyu',
    description='Self-Notification Utility',
    long_description=readfile('README.rst'),
    license='Apache License (2.0)',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    install_requires=install_requires,
    tests_require=readreq('test-requirements.txt'),
    entry_points={
        'console_scripts': [
            'heyu-notify = heyu.submitter:send_notification.console',
            'heyu-hub = heyu.hub:start_hub.console',
            'heyu-notifier = heyu.notifier:notification_server.console',
        ],
        'heyu.notifier': [
            'stdout = heyu.notifications:stdout_notifier',
            'file = heyu.notifications:file_notifier',
            'script = heyu.notifications:script_notifier',
            'gtk = heyu.gtk:gtk_notifier',
        ],
    },
)
