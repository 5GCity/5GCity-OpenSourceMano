from connection import Connection
import unittest
import sys
import jsmin
import json
import os
import time
from jsmin import jsmin
sys.path.append("../../test/core/")
from test_producer import KafkaProducer
from kafka import KafkaConsumer
try:
    import boto
    import boto.ec2
    import boto.vpc
    import boto.ec2.cloudwatch
    import boto.ec2.connection
except:
    exit("Boto not avialable. Try activating your virtualenv OR `pip install boto`")

#--------------------------------------------------------------------------------------------------------------------------------------

# Test Producer object to generate request

producer = KafkaProducer('')
obj = Connection() 
connections = obj.setEnvironment()
connections_res = obj.connection_instance()
cloudwatch_conn = connections_res['cloudwatch_connection'] 

# Consumer Object to consume response from message bus
server = {'server': 'localhost:9092', 'topic': 'metric_request'}
_consumer = KafkaConsumer(bootstrap_servers=server['server'])
_consumer.subscribe(['metric_response'])

#--------------------------------------------------------------------------------------------------------------------------------------

'''Test E2E Flow : Test cases has been tested one at a time.
1) Commom Request is generated using request function in test_producer.py(/core/message-bus)
2) The request is then consumed by the comsumer (plugin)
3) The response is sent back on the message bus in plugin_metrics.py using
   response functions in producer.py(/core/message-bus)
4) The response is then again consumed by the unit_tests_metrics.py
   and the test cases has been applied on the response.
'''
class test_create_metrics(unittest.TestCase):

    def test_status_positive(self):
        time.sleep(2)
        # To generate Request of testing valid meric_name in create metrics requests
        producer.request("create_metrics/create_metric_req_valid.json",'create_metric_request', '','metric_request')  

        for message in _consumer:
            if message.key == "create_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertTrue(resp['metric_create_response']['status'])
                self.assertEqual(resp['metric_create_response']['metric_uuid'],0)
                return 

    def test_status_negative(self):
        time.sleep(2)
        # To generate Request of testing invalid meric_name in create metrics requests
        producer.request("create_metrics/create_metric_req_invalid.json",'create_metric_request', '','metric_request')  

        for message in _consumer:
            if message.key == "create_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['metric_create_response']['status'])
                self.assertEqual(resp['metric_create_response']['metric_uuid'],None)
                return 

class test_metrics_data(unittest.TestCase):

    def test_met_name_positive(self):
        time.sleep(2)
        # To generate Request of testing valid meric_name in read_metric_data_request
        producer.request("read_metrics_data/read_metric_name_req_valid.json",'read_metric_data_request', '','metric_request')  
        for message in _consumer:
            if message.key == "read_metric_data_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertEqual(type(resp['metrics_data']),dict)
                return 

    def test_met_name_negative(self):
        time.sleep(2)
        # To generate Request of testing invalid meric_name in read_metric_data_request
        producer.request("read_metrics_data/read_metric_name_req_invalid.json",'read_metric_data_request', '','metric_request')  
        for message in _consumer:
            if message.key == "read_metric_data_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['metrics_data'])
                return 

    def test_coll_period_positive(self):
        # To generate Request of testing valid collection_period in read_metric_data_request
        # For AWS metric_data_stats collection period should be a multiple of 60
        time.sleep(2)
        producer.request("read_metrics_data/read_coll_period_req_valid.json",'read_metric_data_request', '','metric_request')  
        for message in _consumer:
            if message.key == "read_metric_data_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertEqual(type(resp),dict)
                return

    def test_coll_period_negative(self):
        time.sleep(2)
        # To generate Request of testing invalid collection_period in read_metric_data_request
        producer.request("read_metrics_data/read_coll_period_req_invalid.json",'read_metric_data_request', '','metric_request')  
        for message in _consumer:
            if message.key == "read_metric_data_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['metrics_data'])
                return

class test_update_metrics(unittest.TestCase):

    def test_upd_status_positive(self):
        time.sleep(2)
        # To generate Request of testing valid meric_name in update metrics requests
        producer.request("update_metrics/update_metric_req_valid.json",'update_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "update_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertTrue(resp['metric_update_response']['status'])
                self.assertEqual(resp['metric_update_response']['metric_uuid'],0)
                return

    def test_upd_status_negative(self):
        time.sleep(2)
        # To generate Request of testing invalid meric_name in update metrics requests
        producer.request("update_metrics/update_metric_req_invalid.json",'update_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "update_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['metric_update_response']['status'])
                self.assertEqual(resp['metric_update_response']['metric_uuid'],None)
                return

class test_delete_metrics(unittest.TestCase):

    def test_del_met_name_positive(self):
        time.sleep(2)
        # To generate Request of testing valid meric_name in delete metrics requests
        producer.request("delete_metrics/delete_metric_req_valid.json",'delete_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "delete_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['status'])
                return

    def test_del_met_name_negative(self):
        time.sleep(2)
        # To generate Request of testing invalid meric_name in delete metrics requests
        producer.request("delete_metrics/delete_metric_req_invalid.json",'delete_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "delete_metric_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp)
                return

class test_list_metrics(unittest.TestCase):

    def test_list_met_name_positive(self):
        time.sleep(2)
        # To generate Request of testing valid meric_name in list metrics requests
        producer.request("list_metrics/list_metric_req_valid.json",'list_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "list_metrics_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertEqual(type(resp['metrics_list']),list)
                return

    def test_list_met_name_negitive(self):
        time.sleep(2)
        # To generate Request of testing invalid meric_name in list metrics requests
        producer.request("list_metrics/list_metric_req_invalid.json",'list_metric_request', '','metric_request')  
        for message in _consumer:
            if message.key == "list_metrics_response": 
                resp = json.loads(json.loads(json.loads(message.value)))
                time.sleep(1)
                self.assertFalse(resp['metrics_list'])
                return


if __name__ == '__main__':

    # Saving test reults in Log file

    log_file = 'log_file.txt'
    f = open(log_file, "w")
    runner = unittest.TextTestRunner(f)
    unittest.main(testRunner=runner)
    f.close()

    # For printing results on Console
    # unittest.main()

