===========
osm-common
===========
Contains common modules for OSM lightweight build, that manages database, storage and messaging access.
It uses a plugin stile in order to easy migration to other technologies, as e.g. different database or storage object system.
For database: mongo and memory (volatile) are implemented.
For messaging: Kafka and local file system are implemented.
For storage: local file system is implemented.

