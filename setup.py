from setuptools import setup, find_packages

setup(
    name='patronus',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'pyte',
        'tqdm',
        'asciinema',
    ],
    include_package_data=True, 
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
        '': ['static/*'],
    },
)
