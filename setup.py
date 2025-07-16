from setuptools import setup, find_packages
import sdscli


setup(
    name="sdscli",
    version=sdscli.__version__,
    long_description=sdscli.__description__,
    url=sdscli.__url__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "PyYAML>=5.1",
        "Pygments>=2.4.0",
        "prompt-toolkit>=1.0,<2.0",
        "tqdm>=4.32.1",
        "backoff>=1.8.0",
        "requests>=2.22.0",
        "kombu>=4.5.0",
        "redis>=3.2.1",
        'elasticsearch>=7.0.0,<7.14.0',
        'elasticsearch-dsl>=7.0.0,<=7.4.0',
        "awscli>=1.17.1",
        "boto3>=1.11.1",
        "fab-classic>=1.19.2",
        "Jinja2>=3.0.0,<4.0.0",
    ],
    entry_points={"console_scripts": ["sds=sdscli.command_line:main"]},
    package_data={
        "": [
            "adapters/hysds/files/*",
            "adapters/hysds/files/*/*",
            "adapters/sdskit/files/*",
            "adapters/sdskit/files/*/*",
        ],
    },
)
