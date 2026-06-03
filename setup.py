"""
setup.py — Package configuration for crtsh-recon.

Install for development:
    pip install -e .

Install from source:
    pip install .

After installation the CLI is available as:
    crtsh-recon --help
"""

from setuptools import setup, find_packages
from pathlib import Path

HERE = Path(__file__).parent
LONG_DESCRIPTION = (HERE / "README.md").read_text(encoding="utf-8")

setup(
    name="crtsh-recon",
    version="1.0.0",
    author="ahmed_tripping",
    author_email="ahmadouniass2@gmail.com",
    description="Professional subdomain enumeration via crt.sh Certificate Transparency logs",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/yourhandle/crtsh-recon",
    project_urls={
        "Bug Tracker": "https://github.com/yourhandle/crtsh-recon/issues",
        "Documentation": "https://github.com/yourhandle/crtsh-recon#readme",
        "Source": "https://github.com/yourhandle/crtsh-recon",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: System :: Networking",
    ],
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "urllib3>=2.0.0",
        "colorama>=0.4.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "crtsh-recon=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "osint",
        "subdomain",
        "enumeration",
        "reconnaissance",
        "bug-bounty",
        "certificate-transparency",
        "crt.sh",
        "security",
        "cybersecurity",
    ],
)
