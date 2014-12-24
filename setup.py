#!/usr/bin/env python
# Encoding: utf-8
# See: <http://docs.python.org/distutils/introduction.html>
import os
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

VERSION = eval(filter(lambda _:_.startswith("VERSION"), file("src/pythoniccss.py").readlines())[0].split("=")[1])
# If pandoc is installed, we translate the documentation to RST
LONG_DESCRIPTION  = None
if os.popen("which pandoc").read():
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst README.md").read()

setup(
	name             = "pythoniccss",
	version          = VERSION,
	description      = "A Pythonic CSS pre-processor, designed as a replacement/upgrade to CleverCSS",
	long_description = LONG_DESCRIPTION,
	author           = "Sébastien Pierre",
	author_email     = "sebastien.pierre@gmail.com",
	url              = "http://github.com/sebastien/pythoniccss",
	download_url     = "https://github.com/sebastien/pythoniccss/tarball/%s" % (VERSION),
	keywords         = ["css", "pre-processor", "clever css",],
	install_requires = ["libparsing",],
	package_dir      = {"":"src"},
	py_modules       = ["pythoniccss"],
	scripts          = ["bin/pythoniccss"],
	license          = "License :: OSI Approved :: BSD License",
	# SEE: https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers      = [
		"Programming Language :: Python",
		"Programming Language :: Python :: 2.6",
		"Programming Language :: Python :: 2.7",
		"Development Status :: 4 - Beta",
		"Natural Language :: English",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"Operating System :: OS Independent",
		"Topic :: Utilities"
	],
)

# EOF - vim: ts=4 sw=4 noet
