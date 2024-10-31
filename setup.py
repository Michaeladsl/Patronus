from setuptools import setup

setup(
    name='patronus',
    version='0.1.0',
    py_modules=['edit', 'patronus', 'redact', 'server', 'split'],  # List of scripts in the root directory
    install_requires=[
        'Flask',
        'pyte',
        'tqdm',
        'asciinema',
    ],
    entry_points={
        'console_scripts': [
            'edit=edit:main',
            'patronus=patronus:main',
            'redact=redact:main',
            'server=server:main',
            'split=split:main',
        ],
    },
)
