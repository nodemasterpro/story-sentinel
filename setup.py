"""Setup script for Story Sentinel."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() 
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="story-sentinel",
    version="1.1.0",
    author="Story Sentinel Team",
    description="Automated monitoring and upgrade system for Story Protocol validator nodes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/story-sentinel",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'story-sentinel=sentinel.__main__:cli',
        ],
    },
    include_package_data=True,
    package_data={
        'sentinel': ['*.yaml', '*.json'],
    },
)