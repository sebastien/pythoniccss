#!/usr/bin/env python
# Encoding: utf-8
# See: <http://docs.python.org/distutils/introduction.html>
import os
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup


NAME        = "pythoniccss"
VERSION     = texto.__version__
WEBSITE     = "http://www.github.com/sebastien/texto"
SUMMARY     = "Intuitive, flexible structured text to markup processor"
DESCRIPTION = """\
A Pythonic CSS pre-processor, designed as a replacement/upgrade to CleverCSS.
"""
LONG_DESCRIPTION  = None
if os.popen("which pandoc").read():
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst README.md").read()


VERSION = eval(filter(lambda _:_.startswith("VERSION"), file("src/pythoniccss/__init__.py").readlines())[0].split("=")[1])
WEBSITE = "http://www.github.com/sebastien/texto"
# If pandoc is installed, we translate the documentation to RST


setup(
	name             = NAME,
	version          = VERSION,
	description      = DESCRIPTION,
	long_description = LONG_DESCRIPTION,
	author           = "Sébastien Pierre",
	author_email     = "sebastien.pierre@gmail.com",
	url              = "http://github.com/sebastien/pythoniccss",
	download_url     = "https://github.com/sebastien/pythoniccss/tarball/%s" % (VERSION),
	download_url=  WEBSITE + "/%s-%s.tar.gz" % (NAME.lower(), VERSION) ,
	keywords         = ["css", "pre-processor", "clever css",],
	install_requires = ["libparsing",],
	package_dir      = {"":"src"},
	py_modules       = ["pythoniccss"],
	scripts          = ["bin/pcss"],
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
