#!/usr/bin/env python3
"""
MACD 交易策略專案安裝腳本
"""

from setuptools import setup, find_packages

# 讀取 README 文件
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 讀取 requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="macd-strategy",
    version="1.0.0",
    author="Trading Strategy Developer",
    author_email="developer@example.com",
    description="基於 MACD 指標的加密貨幣交易策略",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "macd-backtest=macd_strategy.backtest.backtest_engine:run_backtest",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 