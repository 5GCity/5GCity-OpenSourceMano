
clean:
	rm -rf dist deb_dist .build osm_common-*.tar.gz osm_common.egg-info eggs

package:
	python3 setup.py --command-packages=stdeb.command sdist_dsc
	cp python3-osm-common.postinst deb_dist/osm-common*/debian
	cd deb_dist/osm-common*/debian && echo "pymongo python3-pymongo" > py3dist-overrides
	cd deb_dist/osm-common*/debian && echo "pip3 python3-pip"       >> py3dist-overrides
	cd deb_dist/osm-common*/  && dpkg-buildpackage -rfakeroot -uc -us
	mkdir -p .build
	cp deb_dist/python3-osm-common*.deb .build/


