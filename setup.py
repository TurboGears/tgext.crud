from setuptools import setup, find_packages
import os

version = '0.8.0'

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.txt')).read()
    CHANGES = open(os.path.join(here, 'CHANGELOG.txt')).read()
except IOError:
    README = CHANGES = ''

import sys
py_version = sys.version_info[:2]

test_requirements = [
  'nose',
  'webtest',
  'TurboGears2',
  'sqlalchemy',
  'zope.sqlalchemy',
  'transaction',
  'tw2.core',
  'tw2.forms',
  'mako'
]

if py_version == (3, 2):
    # jinja2 2.7 is incompatible with Python 3.2
    test_requirements.append('jinja2 < 2.7')
else:
    test_requirements.append('jinja2')

setup(name='tgext.crud',
      version=version,
      description="Crud Controller Extension for TG2",
      long_description=README + "\n" +
                       CHANGES,
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='turbogears2.extension, TG2, REST, crud, sprox',
      author='Christopher Perkins',
      author_email='chris@percious.com',
      url='https://github.com/TurboGears/tgext.crud',
      license='MIT',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['tgext'],
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          "TurboGears2 >= 2.3.0",
          'sprox >= 0.10.0',
      ],
      test_suite='nose.collector',
      tests_require=test_requirements,
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
