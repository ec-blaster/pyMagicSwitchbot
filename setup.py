from setuptools import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyMagicSwitchbot',
    packages=['magicswitchbot'],
    install_requires=['bluepy', 'pycryptodome'],
    version='1.0.13',
    description='Library to control Magic Switchbot devices',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Isidoro Aguilar Baeza',
    url='https://github.com/ec-blaster/pyMagicSwitchbot',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ],
    include_package_data=True
)
