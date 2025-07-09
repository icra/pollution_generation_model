# setup.py
from setuptools import setup, find_packages

setup(
    name="pollution_generation_model",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
        "pandas",
        "openpyxl",
        "psycopg2-binary",  # for PostgreSQL
        # etc.
    ],
    entry_points={
        "console_scripts": [
            "run_pollution_generation_model=pollution_generation_model.pipeline:main",
        ],
    },
)