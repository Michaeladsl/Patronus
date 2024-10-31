from setuptools import setup, find_packages
import os

# Helper function to gather all files in the static directory
def gather_static_files():
    static_files = []
    for dirpath, _, filenames in os.walk('static'):
        for filename in filenames:
            static_files.append(os.path.join(dirpath, filename))
    return static_files

setup(
    name='patronus',
    version='0.1.0',
    py_modules=['patronus', 'edit', 'split', 'redact', 'server'],
    install_requires=[
        'Flask',
        'pyte',
        'tqdm',
        'asciinema',
    ],
    include_package_data=True,  # This ensures MANIFEST.in is used
    entry_points={
        'console_scripts': [
            'edit=edit:main',
            'patronus=patronus:main',
            'redact=redact:main',
            'server=server:main',
            'split=split:main',
        ],
    },
    package_data={
        '': ['configure.sh'],
    },
    data_files=[
        ('', ['configure.sh']),  # This places configure.sh in the root of the installation
        ('static', gather_static_files()),  # Includes all files under the static directory
    ],
)
