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

producer = KafkaProducer('create_alarm_request')
obj = Connection() 
connections = obj.setEnvironment()
connections_res = obj.connection_instance()
cloudwatch_conn = connections_res['cloudwatch_connection'] 

#--------------------------------------------------------------------------------------------------------------------------------------

'''Test E2E Flow : Test cases has been tested one at a time.
1) Commom Request is generated using request function in test_producer.py(/test/core)
2) The request is then consumed by the comsumer (plugin)
3) The response is sent back on the message bus in plugin_alarm.py using
   response functions in producer.py(/core/message-bus)
4) The response is then again consumed by the unit_tests_alarms.py
   and the test cases has been applied on the response.
'''

class config_alarm_name_test(unittest.TestCase):
   

    def setUp(self):
        pass
    #To generate a request of testing new alarm name and new instance id in create alarm request
    def test_differentName_differentInstance(self):
        time.sleep(2)
        producer.request("test_schemas/create_alarm/create_alarm_differentName_differentInstance.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                self.assertTrue(info['alarm_create_response']['status'])
                return        

    #To generate a request of testing new alarm name and existing instance id in create alarm request
    def test_differentName_sameInstance(self):
        time.sleep(2)
        producer.request("test_schemas/create_alarm/create_alarm_differentName_sameInstance.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete1.json",'delete_alarm_request','','alarm_request')
                self.assertTrue(info['alarm_create_response']['status'])   
                return

    #To generate a request of testing existing alarm name and new instance id in create alarm request    
    def test_sameName_differentInstance(self): 
        time.sleep(2)
        producer.request("test_schemas/create_alarm/create_alarm_sameName_differentInstance.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete2.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_create_response']['status']) 
                return    

    #To generate a request of testing existing alarm name and existing instance id in create alarm request
    def test_sameName_sameInstance(self):  
        time.sleep(2)
        producer.request("test_schemas/create_alarm/create_alarm_sameName_sameInstance.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info,"---"
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid.json",'delete_alarm_request', '','alarm_request')
                self.assertEqual(info, None)  
                return        

    #To generate a request of testing valid statistics in create alarm request
    def test_statisticValid(self):       
        time.sleep(2)
        producer.request("test_schemas/create_alarm/statistic_valid.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete3.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_create_response']['status']) 
                return

    #To generate a request of testing Invalid statistics in create alarm request    
    def test_statisticValidNot(self):       
        time.sleep(2)
        producer.request("test_schemas/create_alarm/statistic_invalid.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info,"---"
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete3.json",'delete_alarm_request', '','alarm_request')
                self.assertEqual(info, None)
                return  

    #To generate a request of testing valid operation in create alarm request
    def test_operationValid(self):       
        time.sleep(2)
        producer.request("test_schemas/create_alarm/operation_valid.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete3.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_create_response']['status']) 
                return

    #To generate a request of testing Invalid operation in create alarm request
    def test_operationValidNot(self):       
        time.sleep(2)
        producer.request("test_schemas/create_alarm/operation_invalid.json",'create_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "create_alarm_response": 
                info = json.loads(json.loads(message.value))
                print info
                time.sleep(1)
                self.assertEqual(info,None) 
                return                 
                 

#--------------------------------------------------------------------------------------------------------------------------------------
class update_alarm_name_test(unittest.TestCase):

    #To generate a request of testing valid alarm_id in update alarm request    
    def test_nameValid(self):
        producer.request("test_schemas/update_alarm/update_alarm_new_alarm.json",'create_alarm_request', '','alarm_request')  
        time.sleep(2)
        producer.request("test_schemas/update_alarm/name_valid.json",'update_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "update_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid_delete4.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_update_response']['status'])
                return 
    
    #To generate a request of testing invalid alarm_id in update alarm request
    def test_nameInvalid(self):
        time.sleep(2)
        producer.request("test_schemas/update_alarm/name_invalid.json",'update_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "update_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)
                self.assertEqual(info,None)
                return

    #To generate a request of testing valid statistics in update alarm request
    def test_statisticValid(self):
        producer.request("test_schemas/create_alarm/create_alarm_differentName_differentInstance.json",'create_alarm_request', '','alarm_request')  
        time.sleep(2)
        producer.request("test_schemas/update_alarm/statistic_valid.json",'update_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "update_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_update_response']['status'])
                return

    #To generate a request of testing Invalid statistics in update alarm request
    def test_statisticInvalid(self):
        time.sleep(2)
        producer.request("test_schemas/update_alarm/statistic_invalid.json",'update_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "update_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)
                self.assertEqual(info,None)
                return            

    #To generate a request of testing valid operation in update alarm request
    def test_operationValid(self):
        producer.request("test_schemas/create_alarm/create_alarm_differentName_differentInstance.json",'create_alarm_request', '','alarm_request')  
        time.sleep(2)
        producer.request("test_schemas/update_alarm/operation_valid.json",'update_alarm_request', '','alarm_request')  
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "update_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)
                producer.request("test_schemas/delete_alarm/name_valid.json",'delete_alarm_request', '','alarm_request')
                self.assertTrue(info['alarm_update_response']['status'])
                return
              
#--------------------------------------------------------------------------------------------------------------------------------------
class delete_alarm_test(unittest.TestCase):

    #To generate a request of testing valid alarm_id in delete alarm request   
    def test_nameValid(self):             
        producer.request("test_schemas/create_alarm/create_alarm_differentName_differentInstance.json",'create_alarm_request', '','alarm_request')  
        time.sleep(2)
        producer.request("test_schemas/delete_alarm/name_valid.json",'delete_alarm_request', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "delete_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertTrue(info['alarm_deletion_response']['status'])
                return

    #To generate a request of testing Invalid alarm_id in delete alarm request
    def test_nameInvalid(self):              
        time.sleep(2)
        producer.request("test_schemas/delete_alarm/name_invalid.json",'delete_alarm_request', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "delete_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertEqual(info,None)
                return             

#--------------------------------------------------------------------------------------------------------------------------------------
class list_alarm_test(unittest.TestCase): 

    #To generate a request of testing valid input fields in alarm list request   
    def test_valid_no_arguments(self):
        time.sleep(2)
        producer.request("test_schemas/list_alarm/list_alarm_valid_no_arguments.json",'alarm_list_request', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "list_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertEqual(type(info),dict)
                return

    #To generate a request of testing valid input fields in alarm list request
    def test_valid_one_arguments(self):
        time.sleep(2)
        producer.request("test_schemas/list_alarm/list_alarm_valid_one_arguments.json",'alarm_list_request', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "list_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertEqual(type(info),dict)
                return

    #To generate a request of testing valid input fields in alarm list request
    def test_valid_two_arguments(self):
        time.sleep(2)
        producer.request("test_schemas/list_alarm/list_alarm_valid_two_arguments.json",'alarm_list_request', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "list_alarm_response": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertEqual(type(info),dict)
                return


#--------------------------------------------------------------------------------------------------------------------------------------
class alarm_details_test(unittest.TestCase):

    #To generate a request of testing valid input fields in acknowledge alarm
    def test_Valid(self):
        time.sleep(2)
        producer.request("test_schemas/alarm_details/acknowledge_alarm.json",'acknowledge_alarm', '','alarm_request') 
        server = {'server': 'localhost:9092', 'topic': 'alarm_request'}

        _consumer = KafkaConsumer(bootstrap_servers=server['server'])
        _consumer.subscribe(['alarm_response'])

        for message in _consumer:
            if message.key == "notify_alarm": 
                info = json.loads(json.loads(json.loads(message.value)))
                print info
                time.sleep(1)                
                self.assertEqual(type(info),dict)
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
