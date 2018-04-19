===========
osm-common
===========

Contains general modules for lightweight build database, storage and message access.
The target is to use same library for OSM modules, in order to easy migration to other technologies, that is
different database or storage object system.
For database: mongo and memory (volatile) are implemented.
For message: Kafka and local file system are implemented.
For storage: only local file system is implemented.

