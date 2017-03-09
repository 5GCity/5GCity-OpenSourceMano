SHELL := /bin/bash
all: connectors build package

prepare:
	mkdir -p build
	cp *.py build/
	#cd build; mv openmanod.py openmanod
	cp openmano build/
	cp openmanod.cfg build/
	cp openmano.service build/
	cp -r vnfs build/
	cp -r scenarios build/
	cp -r instance-scenarios build/
	cp -r scripts build/
	cd build/scripts; mv service-openmano.sh service-openmano; mv openmano-report.sh openmano-report
	cp -r database_utils build/

connectors:
	rm -f build/openmanolinkervimconn.py
	cd build; for i in `ls vimconn_*.py |sed "s/\.py//"` ; do echo "import $$i" >> openmanolinkervimconn.py; done
	python build/openmanolinkervimconn.py
	rm -f build/openmanolinkervimconn.py

build: prepare connectors
	python -m py_compile build/*.py

clean:
	rm -rf build
	#find build -name '*.pyc' -delete
	#find build -name '*.pyo' -delete

pip:
	cd build; ./setup.py sdist
	#cp dist/* /root/artifacts/...
	#fpm -s python -t deb build/setup.py

test:
	./test/basictest.sh --force --insert-bashrc --install-openvim --init-openvim


