"""Send alarm info from Aodh to SO via MON"""

import json
from plugins.Openstack.Aodh.aodh_common import Aodh_Common


class Alarming(object):
    """Receives alarm info from Aodh."""

    def __init__(self):
        """Create the aodh_receiver instance."""
        self._aodh_common = Aodh_Common()

    def alarming(self):
        """Receive payload from Aodh."""
        auth_token = self._aodh_common._authenticate()
        endpoint = self._aodh_common.get_endpoint()

        alarm_list = self._get_alarm_list(endpoint, auth_token)
        # Confirm communication with Aodh by listing alarms
        print("Alarm List ", alarm_list.text)

        alarm_id = self._create_alarm(endpoint, auth_token)
        print(alarm_id)

#        alarm_info = self._get_alarm_info(endpoint,
#            auth_token, "372af0e2-5c36-4e4d-8ce9-ca92d97d07d0")
#        print("Alarm info", alarm_info.text)
        return

    def _get_alarm_list(self, endpoint, auth_token):
        """Get a list of alarms that exist in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        alarm_list = self._aodh_common._perform_request(url, auth_token,
                                                        req_type="get")
        return alarm_list

    def _get_alarm_info(self, endpoint, auth_token, alarmID):
        """Get information about a specific alarm from Aodh."""
        url = "{}/v2/alarms/%s".format(endpoint) % (alarmID)

        alarm_details = self._aodh_common._perform_request(url, auth_token,
                                                           req_type="get")
        return alarm_details

    def _create_alarm(self, endpoint, auth_token):
        """Get a list of alarms that exist in Aodh."""
        url = "{}/v2/alarms/".format(endpoint)

        rule = {'event_type': "threshold",}
        payload = json.dumps({'state': 'alarm',
                              'name': 'my_alarm',
                              'severity': 'moderate',
                              'type': 'event',
                              'event_rule': rule,})

        new_alarm = self._aodh_common._perform_request(url, auth_token,
                                                        req_type="post", payload=payload)
        alarm_id =json.loads(new_alarm.text)['alarm_id']
        return alarm_id

