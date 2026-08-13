# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
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
    packages= find_packages(include=['autokeys', 'autokeys/*']),
    install_requires=[
        'pyyaml',
        # 1.8 reports whether a key event was injected, which the pattern engine
        # needs in order to ignore the keystrokes it synthesises itself
        'pynput>=1.8',
        'pyperclip'
    ],
    extras_require={
        'dev': ['pytest']
    },
    entry_points={
        'console_scripts': [
            "autokeys=autokeys.service:main"
        ]
    }
)
# =======================================================================================
# End
# =======================================================================================