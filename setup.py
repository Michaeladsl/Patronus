from setuptools import setup

setup(
    name='patronus',
    version='0.1.0',
    py_modules=['edit', 'patronus', 'redact', 'server', 'split'],
    install_requires=[
        'Flask',
        'pyte',
        'tqdm',
        'asciinema',
    ],
    include_package_data=True,  
    package_data={
        '': ['configure.sh'], 
    },
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
