SHELL := /bin/bash
all: pip deb

prepare:
	mkdir -p build/
	cp MANIFEST.in build/
	cp requirements.txt build/
	cp README.rst build/
	cp setup.py build/
	cp -r osm_ro build/
	cp openmano build/
	cp openmanod build/
	cp openmanod.cfg build/
	cp osm-ro.service build/
	cp -r vnfs build/osm_ro
	cp -r scenarios build/osm_ro
	cp -r instance-scenarios build/osm_ro
	cp -r scripts build/osm_ro
	cp -r database_utils build/osm_ro

connectors: prepare
	# python-novaclient is required for that
	rm -f build/osm_ro/openmanolinkervimconn.py
	cd build/osm_ro; for i in `ls vimconn_*.py |sed "s/\.py//"` ; do echo "import $$i" >> openmanolinkervimconn.py; done
	python build/osm_ro/openmanolinkervimconn.py
	rm -f build/osm_ro/openmanolinkervimconn.py

build: connectors prepare
	python -m py_compile build/osm_ro/*.py

pip: prepare
	cd build && ./setup.py sdist
	cd build && ./setup.py bdist_wheel

deb: prepare
	echo "Nothing to be done"
	#cd build; ./setup.py --command-packages=stdeb.command bdist_deb
	#fpm -s python -t deb build/setup.py

snap:
	echo "Nothing to be done yet"

install:
	cd build && pip install dist/*.tar.gz

develop: prepare
	cd build && ./setup.py develop

sync:
	#cp build/dist/* /root/artifacts/...

test:
	./test/basictest.sh --force --insert-bashrc --install-openvim --init-openvim

clean:
	rm -rf build
	#find build -name '*.pyc' -delete
	#find build -name '*.pyo' -delete

