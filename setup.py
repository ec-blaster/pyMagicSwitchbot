from setuptools import setup

setup(
    name='pyMagicSwitchbot',
    packages=['magicswitchbot'],
    install_requires=['bluepy', 'pycryptodome'],
    version='0.0.1',
    description='Library to control MagicSwitchbot devices (chinese clone of SwitchBot)',
    author='Isidoro Aguilar Baeza',
    url='https://github.com/ec-blaster/pyMagicSwitchbot',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: Linux',
        'Programming Language :: Python :: 3.5',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ]
)
