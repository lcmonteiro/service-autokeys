# =======================================================================================
# File:   setup.py
# Author: Luis Monteiro
# =======================================================================================
# imports
from setuptools import setup, find_packages

# -----------------------------------------------------------------------------
# setup
# -----------------------------------------------------------------------------
setup(
    name='autokeys',  
    version='0.1',
    author='Luis Monteiro',
    author_email='monteiro.lcm@gmail.co',
    description='',
    packages= find_packages(include=['autokeys']),
    install_requires=[
        'click',
        'dpath',
        'pynput'
    ],
    entry_points={
        'console_scripts': [
            "autokeys=autokeys.service:main"
        ]
    }
)
# =======================================================================================
# End
# =======================================================================================