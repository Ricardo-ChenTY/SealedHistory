from setuptools import setup, find_packages

setup(
    name="provetok",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "pyyaml>=6.0",
        "openai>=1.10.0",
    ],
    extras_require={
        "viz": ["matplotlib>=3.7", "numpy>=1.24"],
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "provetok=provetok.cli:main",
        ],
    },
)
