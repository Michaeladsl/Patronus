from setuptools import setup

setup(
    name='patronus',
    version='0.1.0',
    py_modules=['patronus', 'edit', 'split', 'redact', 'server'],  # Specify each script as a module
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
    '': ['configure.sh', 'static/**/*'],
    },
)
