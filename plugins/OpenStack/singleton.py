from __future__ import unicode_literals


class Singleton(object):
    """Simple singleton class"""

    def __init__(self, decorated):
        self._decorated = decorated

    def instance(self):
        """Return singleton instance"""
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance
