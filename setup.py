#!/usr/bin/env python
# Encoding: utf-8
# See: <http://docs.python.org/distutils/introduction.html>
import os
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

NAME        = "pythoniccss"
WEBSITE     = "http://www.github.com/sebastien/pythoniccss"
SUMMARY     = "CSS-preprocessor with Pythonic syntax."
DESCRIPTION = """\
A Pythonic CSS pre-processor, designed as a replacement/upgrade to CleverCSS.
"""
LONG_DESCRIPTION  = None
if os.path.exists("README.md") and os.popen("which pandoc").read():
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst README.md").read()

VERSION = eval([_.rsplit("=",1)[1] for _ in open("src/pythoniccss/__init__.py").readlines() if _.startswith("VERSION")][0])
WEBSITE = "http://www.github.com/sebastien/pythoniccss"

setup(
	name             = NAME,
	version          = VERSION,
	description      = DESCRIPTION,
	long_description = LONG_DESCRIPTION,
	author           = "Sébastien Pierre",
	author_email     = "sebastien.pierre@gmail.com",
	url              =  WEBSITE,
	download_url     =  WEBSITE + "/%s-%s.tar.gz" % (NAME.lower(), VERSION) ,
	keywords         = ["css", "pre-processor", "clever css",],
	install_requires = ["libparsing",],
	packages         = ["pythoniccss"],
	package_dir      = {"pythoniccss":"src/pythoniccss"},
	package_data     = {"pythoniccss":["rgb.txt"]},
	scripts          = ["bin/pcss"],
	license          = "License :: OSI Approved :: BSD License",
	# SEE: https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers      = [
		"Programming Language :: Python",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3.5",
		"Development Status :: 4 - Beta",
		"Natural Language :: English",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"Operating System :: OS Independent",
		"Topic :: Utilities"
	],
)

# EOF - vim: ts=4 sw=4 noet
