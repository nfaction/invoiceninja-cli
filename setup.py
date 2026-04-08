from setuptools import setup, find_packages

setup(
    name="invoiceninja-cli",
    version="0.1.0",
    description="CLI harness for InvoiceNinja v5 REST API",
    long_description=open("INVOICENINJA.md").read() if __import__("os").path.exists("INVOICENINJA.md") else "",
    long_description_content_type="text/markdown",
    packages=find_packages(include=["invoiceninja_cli", "invoiceninja_cli.*"]),
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
        "tabulate>=0.9",
        "prompt_toolkit>=3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-mock>=3.0",
            "responses>=0.23",
        ]
    },
    entry_points={
        "console_scripts": [
            "invoiceninja-cli=invoiceninja_cli.invoiceninja_cli:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
