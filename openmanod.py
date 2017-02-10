#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##

'''
openmano server.
Main program that implements a reference NFVO (Network Functions Virtualisation Orchestrator).
It interfaces with an NFV VIM through its API and offers a northbound interface, based on REST (openmano API),
where NFV services are offered including the creation and deletion of VNF templates, VNF instances,
network service templates and network service instances. 

It loads the configuration file and launches the http_server thread that will listen requests using openmano API.
'''
__author__="Alfonso Tierno, Gerardo Garcia, Pablo Montes"
__date__ ="$26-aug-2014 11:09:29$"
__version__="0.5.8-r518"
version_date="Jan 2017"
database_version="0.19"      #expected database schema version

import httpserver
import time
import sys
import getopt
import yaml
import nfvo_db
from jsonschema import validate as js_v, exceptions as js_e
from openmano_schemas import config_schema
from db_base import db_base_Exception
import nfvo
import logging
import logging.handlers as log_handlers
import socket

global global_config
global logger

class LoadConfigurationException(Exception):
    pass

def load_configuration(configuration_file):
    default_tokens ={'http_port':9090,
                     'http_host':'localhost',
                     'http_console_proxy': True,
                     'http_console_host': None,
                     'log_level': 'DEBUG',
                     'log_socket_port': 9022,
                     'auto_push_VNF_to_VIMs': True
                    }
    try:
        #Check config file exists
        with open(configuration_file, 'r') as f:
            config_str = f.read()
        #Parse configuration file
        config = yaml.load(config_str)
        #Validate configuration file with the config_schema
        js_v(config, config_schema)
        
        #Add default values tokens
        for k,v in default_tokens.items():
            if k not in config:
                config[k]=v
        return config
    
    except yaml.YAMLError as e:
        error_pos = ""
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            error_pos = " at line:{} column:{}".format(mark.line+1, mark.column+1)
        raise LoadConfigurationException("Bad YAML format at configuration file '{file}'{pos}".format(file=configuration_file, pos=error_pos) )
    except js_e.ValidationError as e:
        error_pos = ""
        if e.path:
            error_pos=" at '" + ":".join(map(str, e.path))+"'"
        raise LoadConfigurationException("Invalid field at configuration file '{file}'{pos} {message}".format(file=configuration_file, pos=error_pos, message=str(e)) ) 
    except Exception as e:
        raise LoadConfigurationException("Cannot load configuration file '{file}' {message}".format(file=configuration_file, message=str(e) ) )
                

def console_port_iterator():
    '''this iterator deals with the http_console_ports 
    returning the ports one by one
    '''
    index = 0
    while index < len(global_config["http_console_ports"]):
        port = global_config["http_console_ports"][index]
        #print("ports -> ", port)
        if type(port) is int:
            yield port
        else: #this is dictionary with from to keys
            port2 = port["from"]
            #print("ports -> ", port, port2)
            while port2 <= port["to"]:
                #print("ports -> ", port, port2)
                yield port2
                port2 += 1
        index += 1
    
    
def usage():
    print("Usage: ", sys.argv[0], "[options]")
    print( "      -v|--version: prints current version")
    print( "      -c|--config [configuration_file]: loads the configuration file (default: openmanod.cfg)")
    print( "      -h|--help: shows this help")
    print( "      -p|--port [port_number]: changes port number and overrides the port number in the configuration file (default: 9090)")
    print( "      -P|--adminport [port_number]: changes admin port number and overrides the port number in the configuration file (default: 9095)")
    #print( "      -V|--vnf-repository: changes the path of the vnf-repository and overrides the path in the configuration file")
    print( "      --log-socket-host HOST: send logs to this host")
    print( "      --log-socket-port PORT: send logs using this port (default: 9022)")
    print( "      --log-file FILE: send logs to this file")
    return
    
if __name__=="__main__":
    #Configure logging step 1
    hostname = socket.gethostname()
    #streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
    # "%(asctime)s %(name)s %(levelname)s %(filename)s:%(lineno)d %(funcName)s %(process)d: %(message)s"
    log_formatter_complete = logging.Formatter(
        '%(asctime)s.%(msecs)03d00Z[{host}@openmanod] %(filename)s:%(lineno)s severity:%(levelname)s logger:%(name)s log:%(message)s'.format(host=hostname),
        datefmt='%Y-%m-%dT%H:%M:%S',
    )
    log_format_simple =  "%(asctime)s %(levelname)s  %(name)s %(filename)s:%(lineno)s %(message)s"
    log_formatter_simple = logging.Formatter(log_format_simple, datefmt='%Y-%m-%dT%H:%M:%S')
    logging.basicConfig(format=log_format_simple, level= logging.DEBUG)
    logger = logging.getLogger('openmano')
    logger.setLevel(logging.DEBUG)
    socket_handler = None
    file_handler = None
    # Read parameters and configuration file
    httpthread = None
    try:
        #load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvc:V:p:P:", ["config=", "help", "version", "port=", "vnf-repository=", "adminport=", "log-socket-host=", "log-socket-port=", "log-file="])
        port=None
        port_admin = None
        config_file = 'openmanod.cfg'
        vnf_repository = None
        log_file = None
        log_socket_host = None
        log_socket_port = None
        
        for o, a in opts:
            if o in ("-v", "--version"):
                print ("openmanod version " + __version__ + ' ' + version_date)
                print ("(c) Copyright Telefonica")
                sys.exit()
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-V", "--vnf-repository"):
                vnf_repository = a
            elif o in ("-c", "--config"):
                config_file = a
            elif o in ("-p", "--port"):
                port = a
            elif o in ("-P", "--adminport"):
                port_admin = a
            elif o == "--log-socket-port":
                log_socket_port = a
            elif o == "--log-socket-host":
                log_socket_host = a
            elif o == "--log-file":
                log_file = a
            else:
                assert False, "Unhandled option"
        global_config = load_configuration(config_file)
        #print global_config
        # Override parameters obtained by command line
        if port:
            global_config['http_port'] = port
        if port_admin:
            global_config['http_admin_port'] = port_admin
        if log_socket_host:
            global_config['log_socket_host'] = log_socket_host
        if log_socket_port:
            global_config['log_socket_port'] = log_socket_port
        if log_file:
            global_config['log_file'] = log_file
#         if vnf_repository is not None:
#             global_config['vnf_repository'] = vnf_repository
#         else:
#             if not 'vnf_repository' in global_config:  
#                 logger.error( os.getcwd() )
#                 global_config['vnf_repository'] = os.getcwd()+'/vnfrepo'
#         #print global_config
#         if not os.path.exists(global_config['vnf_repository']):
#             logger.error( "Creating folder vnf_repository folder: '%s'.", global_config['vnf_repository'])
#             try:
#                 os.makedirs(global_config['vnf_repository'])
#             except Exception as e:
#                 logger.error( "Error '%s'. Ensure the path 'vnf_repository' is properly set at %s",e.args[1], config_file)
#                 exit(-1)
        
        global_config["console_port_iterator"] = console_port_iterator
        global_config["console_thread"]={}
        global_config["console_ports"]={}
        if not global_config["http_console_host"]:
            global_config["http_console_host"] = global_config["http_host"]
            if global_config["http_host"]=="0.0.0.0":
                global_config["http_console_host"] = socket.gethostname()
        
        #Configure logging STEP 2
        if "log_host" in global_config:
            socket_handler= log_handlers.SocketHandler(global_config["log_socket_host"], global_config["log_socket_port"])
            socket_handler.setFormatter(log_formatter_complete)
            if global_config.get("log_socket_level") and global_config["log_socket_level"] != global_config["log_level"]: 
                socket_handler.setLevel(global_config["log_socket_level"])
            logger.addHandler(socket_handler)
        #logger.addHandler(log_handlers.SysLogHandler())
        if "log_file" in global_config:
            try:
                file_handler= logging.handlers.RotatingFileHandler(global_config["log_file"], maxBytes=100e6, backupCount=9, delay=0)
                file_handler.setFormatter(log_formatter_simple)
                logger.addHandler(file_handler)
                #logger.debug("moving logs to '%s'", global_config["log_file"])
                #remove initial stream handler
                logging.root.removeHandler(logging.root.handlers[0])
                print ("logging on '{}'".format(global_config["log_file"]))
            except IOError as e:
                raise LoadConfigurationException("Cannot open logging file '{}': {}. Check folder exist and permissions".format(global_config["log_file"], str(e)) ) 
        #logging.basicConfig(level = getattr(logging, global_config.get('log_level',"debug")))
        logger.setLevel(getattr(logging, global_config['log_level']))
        logger.critical("Starting openmano server version: '%s %s' command: '%s'",  
                         __version__, version_date, " ".join(sys.argv))
        
        for log_module in ("nfvo", "http", "vim", "db", "console"):
            log_level_module = "log_level_" + log_module
            log_file_module = "log_file_" + log_module
            logger_module = logging.getLogger('openmano.' + log_module)
            if log_level_module in global_config:
                logger_module.setLevel(global_config[log_level_module])
            if log_file_module in global_config:
                try:
                    file_handler= logging.handlers.RotatingFileHandler(global_config[log_file_module], maxBytes=100e6, backupCount=9, delay=0)
                    file_handler.setFormatter(log_formatter_simple)
                    logger_module.addHandler(file_handler)
                except IOError as e:
                    raise LoadConfigurationException("Cannot open logging file '{}': {}. Check folder exist and permissions".format(global_config[log_file_module], str(e)) ) 
            global_config["logger_"+log_module] = logger_module
        #httpserver.logger = global_config["logger_http"]
        #nfvo.logger = global_config["logger_nfvo"]
        
        # Initialize DB connection
        mydb = nfvo_db.nfvo_db();
        mydb.connect(global_config['db_host'], global_config['db_user'], global_config['db_passwd'], global_config['db_name'])
        try:
            r = mydb.get_db_version()
            if r[1] != database_version:
                logger.critical("DATABASE wrong version '%s'. \
                                Try to upgrade/downgrade to version '%s' with './database_utils/migrate_mano_db.sh'",
                                r[1], database_version)
                exit(-1)
        except db_base_Exception as e:
            logger.critical("DATABASE is not a MANO one or it is a '0.0' version. Try to upgrade to version '%s' with \
                            './database_utils/migrate_mano_db.sh'", database_version)
            exit(-1)

        nfvo.global_config=global_config
        nfvo.start_service(mydb)
        
        httpthread = httpserver.httpserver(mydb, False, global_config['http_host'], global_config['http_port'])
        
        httpthread.start()
        if 'http_admin_port' in global_config: 
            httpthreadadmin = httpserver.httpserver(mydb, True, global_config['http_host'], global_config['http_admin_port'])
            httpthreadadmin.start()
        time.sleep(1)      
        logger.info('Waiting for http clients')
        print('Waiting for http clients')
        print('openmanod ready')
        print('====================')
        time.sleep(20)
        sys.stdout.flush()

        #TODO: Interactive console must be implemented here instead of join or sleep

        #httpthread.join()
        #if 'http_admin_port' in global_config:
        #    httpthreadadmin.join()
        while True:
            time.sleep(86400)

    except KeyboardInterrupt as e:
        logger.info(str(e))
    except SystemExit:
        pass
    except getopt.GetoptError as e:
        logger.critical(str(e)) # will print something like "option -a not recognized"
        #usage()
        exit(-1)
    except LoadConfigurationException as e:
        logger.critical(str(e))
        exit(-1)
    except db_base_Exception as e:
        logger.critical(str(e))
        exit(-1)
    nfvo.stop_service()
    if httpthread:
        httpthread.join(1)
    for thread in global_config["console_thread"]:
        thread.terminate = True

