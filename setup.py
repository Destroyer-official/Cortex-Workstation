#!/usr/bin/env python3
"""
Setup script for Deep Cleaner.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="deep-cleaner",
    version="1.0.0",
    author="Deep Cleaner Team",
    author_email="team@deepcleaner.com",
    description="A comprehensive utility to find and remove unnecessary files and folders",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/deepcleaner/deep-cleaner",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "visualization": [
            "plotly>=5.15.0",
        ],
        "docker": [
            "docker>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "deep-cleaner=deep_cleaner.cli:main",
            "deep-cleaner-gui=deep_cleaner.gui_app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "deep_cleaner": [
            "i18n/locales/*.json",
            "*.md",
        ],
    },
    keywords="cleaner, disk, files, duplicates, temp, system, maintenance",
    project_urls={
        "Bug Reports": "https://github.com/deepcleaner/deep-cleaner/issues",
        "Source": "https://github.com/deepcleaner/deep-cleaner",
        "Documentation": "https://deepcleaner.readthedocs.io/",
    },
)