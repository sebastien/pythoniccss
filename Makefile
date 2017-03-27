SOURCES     = $(wildcard src/*.py)
DOC_SOURCES = $(wildcard src/*.py)
MANIFEST    = $(SOURCES) $(wildcard *.py api/*.* AUTHORS* README* LICENSE*)
VERSION     = `grep VERSION src/pythoniccss/__init__.py | cut -d '=' -f2  | xargs echo`
DOC_PRODUCT = README.html API.html REFERENCE.html
PRODUCT     = MANIFEST

.PHONY: all doc clean check
	
all: $(PRODUCT)

release: $(PRODUCT)
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py clean sdist register upload

test:
	python tests/test-all.py

clean:
	@rm -rf api/ build dist MANIFEST ; true

check:
	pychecker -100 $(SOURCES)

API.html: $(DOC_SOURCES)
	sdoc --markup=texto src/pythoniccss.py API.html

doc: README.html

README.html:  tests/test-complete.pcss bin/makedoc
	python bin/makedoc

test:
	python tests/all.py

MANIFEST: $(MANIFEST)
	echo $(MANIFEST) | xargs -n1 | sort | uniq > $@

#EOF
