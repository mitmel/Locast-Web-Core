import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "locast-core",
    version = "1.4",
    author = "Amar Boghani",
    author_email = "amarkb@mit.edu",
    description = ("Locast Core"),
    license = "GPLv2",
    keywords = "",
    url = "http://locast.mit.edu/",
    packages=find_packages(),
    install_requires = ['Django>=1.5'],
    include_package_data = True,
    long_description=read('locast/README'),
    scripts=['bin/lcvideo_combine', 'bin/lcvideo_mkflv', 'bin/lcvideo_preview', 'bin/lcvideo_screenshot', 'bin/qt-faststart-inplace'],
    classifiers=[
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: GNU General Public License (GPL)",
    ],
)
