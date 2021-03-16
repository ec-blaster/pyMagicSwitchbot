from setuptools import setup

setup(
    name='pyMagicSwitchbot',
    packages=['magicswitchbot'],
    install_requires=['bluepy', 'pycryptodome'],
    version='1.0.0',
    description='Library to control Magic Switchbot devices (chinese clone of Switchbot)',
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
      ],
    include_package_data=True
)
