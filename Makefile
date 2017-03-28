SHELL := /bin/bash
all: pypackage debpackage

prepare:
	mkdir -p build
	cp *.py build/
	#cd build; mv openmanod.py openmanod
	cp openmano build/
	cp openmanod.cfg build/
	cp requirements.txt build/
	cp README.rst build/
	cp openmano.service build/
	cp -r vnfs build/
	cp -r scenarios build/
	cp -r instance-scenarios build/
	cp -r scripts build/
	cd build/scripts; mv service-openmano.sh service-openmano; mv openmano-report.sh openmano-report
	cp -r database_utils build/

connectors: prepare
	# python-novaclient is required for that
	rm -f build/openmanolinkervimconn.py
	cd build; for i in `ls vimconn_*.py |sed "s/\.py//"` ; do echo "import $$i" >> openmanolinkervimconn.py; done
	python build/openmanolinkervimconn.py
	rm -f build/openmanolinkervimconn.py

build: prepare
	python -m py_compile build/*.py

pypackage: build
	cd build; ./setup.py sdist
	#cp build/dist/* /root/artifacts/...

debpackage: build
	echo "Nothing to be done yet"
	#fpm -s python -t deb build/setup.py

snappackage:
	echo "Nothing to be done yet"

test:
	./test/basictest.sh --force --insert-bashrc --install-openvim --init-openvim

clean:
	rm -rf build
	#find build -name '*.pyc' -delete
	#find build -name '*.pyo' -delete

