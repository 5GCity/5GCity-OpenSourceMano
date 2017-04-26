SHELL := /bin/bash
all: package install

clean_deb:
	rm -rf .build

clean:
	rm -rf build
	find osm_ro -name '*.pyc' -delete
	find osm_ro -name '*.pyo' -delete
prepare:
	pip install --user --upgrade setuptools
	mkdir -p build/
	VER1=$(shell git describe | sed -e 's/^v//' |cut -d- -f1); \
	VER2=$(shell git describe | cut -d- -f2); \
	VER3=$(shell git describe | cut -d- -f3); \
	echo "$$VER1.dev$$VER2+$$VER3" > build/RO_VERSION
	cp MANIFEST.in build/
	cp requirements.txt build/
	cp README.rst build/
	cp setup.py build/
	cp stdeb.cfg build/
	cp -r osm_ro build/
	cp openmano build/
	cp openmanod build/
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

build: clean connectors prepare
	python -m py_compile build/osm_ro/*.py

pip: prepare
	cd build && ./setup.py sdist

package: clean clean_deb prepare
	#apt-get install -y python-stdeb
	cd build && python setup.py --command-packages=stdeb.command sdist_dsc --with-python2=True
	cd build && cp osm_ro/scripts/python-osm-ro.postinst deb_dist/osm-ro*/debian/
	cd build/deb_dist/osm-ro* && dpkg-buildpackage -rfakeroot -uc -us
	mkdir -p .build
	cp build/deb_dist/python-*.deb .build/

snap:
	echo "Nothing to be done yet"

install:
	DEBIAN_FRONTEND=noninteractive apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install -y python-pip && \
	pip install --upgrade pip && \
	dpkg -i .build/*.deb

develop: prepare
	#pip install -r requirements.txt
	cd build && ./setup.py develop

test:
	./test/basictest.sh --force --insert-bashrc --install-openvim --init-openvim

build-docker-from-source:
	docker build -t osm/openmano -f docker/Dockerfile-local .

run-docker:
	docker-compose -f docker/openmano-compose.yml up

stop-docker:
	docker-compose -f docker/openmano-compose.yml down


