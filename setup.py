#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="seo-farm-orchestrator",
    version="1.0.0",
    author="SEO Farm Orchestrator",
    author_email="admin@seo-farm.com",
    description="AI-powered SEO content orchestrace pomocí Temporal.io + OpenAI Assistant API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/seo-farm-orchestrator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest", "pytest-asyncio", "black", "flake8"],
        "db": ["sqlalchemy>=2.0.0", "psycopg2-binary>=2.9.0"],
    },
    entry_points={
        "console_scripts": [
            "seo-farm=seo_farm_orchestrator.cli:main",
        ],
    },
    package_data={
        "seo_farm_orchestrator": [
            "*.py",
            "activities/*.py",
            "workflows/*.py",
            "scripts/*.py",
        ],
    },
    include_package_data=True,
) 