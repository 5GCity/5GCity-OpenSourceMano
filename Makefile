
clean:
	rm -rf dist deb_dist .build osm_lcm-*.tar.gz osm_lcm.egg-info eggs

package:
	python3 setup.py --command-packages=stdeb.command sdist_dsc
	cp python3-osm-lcm.postinst deb_dist/osm-lcm*/debian
	cd deb_dist/osm-lcm*/debian && echo "osm-common python3-osm-common" > py3dist-overrides
	# cd deb_dist/osm-lcm*/debian && echo "pip3 python3-pip"       >> py3dist-overrides
	cd deb_dist/osm-lcm*/  && dpkg-buildpackage -rfakeroot -uc -us
	mkdir -p .build
	cp deb_dist/python3-osm-lcm*.deb .build/


