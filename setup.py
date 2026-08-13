# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# imports
import re
from pathlib import Path

from setuptools import find_packages, setup

# -----------------------------------------------------------------------------
# metadata
# -----------------------------------------------------------------------------
ROOT = Path(__file__).parent

# Read the version rather than importing it; importing would pull in pynput
# before its dependencies are installed.
VERSION = re.search(
    r"^__version__ = '([^']+)'",
    (ROOT / 'autokeys' / '__init__.py').read_text(encoding='utf-8'),
    re.MULTILINE,
).group(1)

# -----------------------------------------------------------------------------
# setup
# -----------------------------------------------------------------------------
setup(
    name='autokeys',
    version=VERSION,
    author='Luis Monteiro',
    author_email='monteiro.lcm@gmail.com',
    description='Type credentials and text snippets from a global hotkey.',
    long_description=(ROOT / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    license='MIT',
    packages=find_packages(include=['autokeys', 'autokeys.*']),
    python_requires='>=3.8',
    install_requires=[
        'pyyaml',
        # 1.8 reports whether a key event was injected, which the pattern engine
        # needs in order to ignore the keystrokes it synthesises itself.
        'pynput>=1.8',
        'pyperclip',
    ],
    extras_require={
        'dev': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'autokeys=autokeys.service:main',
        ],
    },
    classifiers=[
        'Environment :: X11 Applications',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
)
# =======================================================================================
# End
# =======================================================================================
