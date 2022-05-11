from setuptools import setup

from atri_bot import VERSION

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()

setup(
    name="atri_bot",
    version=VERSION,
    author="",
    py_modules=["atri_bot"],
    description="a toolkit for reposting tweet to weibo",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kozakai-ayaya/ATRI-BOT",
    install_requires=[
        "requests",
        "tweepy",
        "schedule",
    ],
)
