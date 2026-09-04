from setuptools import setup, find_packages

setup(
    name="plug_n_play_connector",
    version="0.1.0",
    description="Standardized Client Connector SDK for the Plug-N-Play AI Data Layer",
    author="Plug-N-Play AI",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "pydantic>=2.0.0"
    ],
    python_requires=">=3.9",
)
