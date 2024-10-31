from setuptools import setup, find_packages

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
        '': ['configure.sh', 'static/**/*'],
    },
    data_files=[
        ('', ['configure.sh']),  # This places configure.sh in the root of the installation
    ],
    data_files=[
        ('static', ['static/**/*']),
    ],
)
