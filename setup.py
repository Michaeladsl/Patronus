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
            'edit=patronus.edit:main',
            'patronus=patronus.patronus:main',
            'redact=patronus.redact:main',
            'server=patronus.server:main',
            'split=patronus.split:main',
        ],
    },
    package_data={
        'patronus': ['static/*', 'configure.sh'],
    },
)
