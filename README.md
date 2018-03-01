# N2VC

## Objective

The N2VC library provides an OSM-centric interface to the VCA. This enables any OSM module (SO, LCM, osmclient) to use a standard pattern for communicating with Juju and the charms responsible for configuring a VNF.

N2VC relies on the IM module, enforcing compliance with the OSM Information Model.

## Caveats

This library is in active development for OSM Release FOUR. The interface is subject to change prior to release.

## Roadmap
- Create the N2VC API (in progress)
- Create a Python library implementing the N2VC API (in progress)
- Implement N2VC API in SO
- Implement N2VC API in lcm
- Add support for N2VC in OSMClient

## Requirements

Because this is still in heavy development, there are a few manual steps required to use this library.


```
# This list is incomplete
apt install python3-nose
```

### Install LXD and Juju

In order to run the test(s) included in N2VC, you'll need to install Juju locally.

*Note: It's not necessary to install the juju library via pip3; N2VC uses a version bundled within the modules/ directory.*

```bash
snap install lxd
snap install juju --classic
```

### Install the IM

The pyangbind library, used by the IM to parse the Yang data models does not support Python3 at the moment. Work is being done in coordination with the pyangbind maintainer, and Python3 support is expected to hand in the near future.

In the meantime, we will install and use Python3-compatible branches of pyangbind and the IM module.

```
sudo apt install libxml2-dev libxslt1-dev build-essential

git clone http://github.com/adamisrael/pyangbind.git
cd pyangbind
pip3 install -r requirements.txt
pip3 install -r requirements.DEVELOPER.txt

sudo python3 setup.py develop
```

Checkout the IM module and use the proposed branch from Gerrit:
```bash
git clone https://osm.etsi.org/gerrit/osm/IM.git
cd IM
git fetch https://israelad@osm.etsi.org/gerrit/osm/IM refs/changes/78/5778/2 && git checkout FETCH_HEAD
sudo python3 setup.py develop
```

```bash
git clone https://osm.etsi.org/gerrit/osm/N2VC.git
cd N2VC
git fetch https://israelad@osm.etsi.org/gerrit/osm/N2VC refs/changes/70/5870/5 && git checkout FETCH_HEAD
sudo python3 setup.py develop

```

## Testing
A basic test has been written to exercise the functionality of the library, and to serve as a demonstration of how to use it.

### Export settings to run test

Export a few environment variables so the test knows where to find the VCA, and the compiled pingpong charm from the devops repository.

```bash
# You can find the ip of the VCA by running `juju status -m controller` and looking for the DNS for Machine 0
export VCA_HOST=
export VCA_PORT=17070
# You can find these variables in ~/.local/share/juju/accounts.yaml
export VCA_USER=admin
export VCA_SECRET=PASSWORD
```

### Run the test(s)

*Note: There is a bug in the cleanup of the N2VC/Juju that will throw an exception after the test has finished. This is on the list of things to fix for R4 and should not impact your tests or integration.*

```bash
nosetests3 --nocapture tests/test_python.py
```

## Known Issues

Many. This is still in active development for Release FOUR.

- `GetMetrics` does not work yet. There seems to be
- An exception is thrown after using N2VC, probably related to the internal AllWatcher used by juju.Model. This shouldn't break usage of N2VC, but it is ugly and needs to be fixed.

```
Exception ignored in: <generator object WebSocketCommonProtocol.close_connection at 0x7f29a3b3f780>                                     
Traceback (most recent call last):                                  
  File "/home/stone/.local/lib/python3.6/site-packages/websockets/protocol.py", line 743, in close_connection                           
    if (yield from self.wait_for_connection_lost()):                
  File "/home/stone/.local/lib/python3.6/site-packages/websockets/protocol.py", line 768, in wait_for_connection_lost                   
    self.timeout, loop=self.loop)
  File "/usr/lib/python3.6/asyncio/tasks.py", line 342, in wait_for
    timeout_handle = loop.call_later(timeout, _release_waiter, waiter)                                                                  
  File "/usr/lib/python3.6/asyncio/base_events.py", line 543, in call_later                                                             
    timer = self.call_at(self.time() + delay, callback, *args)      
  File "/usr/lib/python3.6/asyncio/base_events.py", line 553, in call_at                                                                
    self._check_closed()          
  File "/usr/lib/python3.6/asyncio/base_events.py", line 357, in _check_closed                                                          
    raise RuntimeError('Event loop is closed')                      
RuntimeError: Event loop is closed                                  
Exception ignored in: <generator object Queue.get at 0x7f29a2ac6938>                                                                    
Traceback (most recent call last):                                  
  File "/usr/lib/python3.6/asyncio/queues.py", line 169, in get     
    getter.cancel()  # Just in case getter is not done yet.         
  File "/usr/lib/python3.6/asyncio/base_events.py", line 574, in call_soon                                                              
    self._check_closed()          
  File "/usr/lib/python3.6/asyncio/base_events.py", line 357, in _check_closed                                                          
    raise RuntimeError('Event loop is closed')                      
RuntimeError: Event loop is closed                                  
Exception ignored in: <coroutine object AllWatcherFacade.Next at 0x7f29a3bd9990>                                                        
Traceback (most recent call last):                                  
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/client/facade.py", line 412, in wrapper                                           
    reply = await f(*args, **kwargs)                                
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/client/_client1.py", line 59, in Next                                             
    reply = await self.rpc(msg)   
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/client/overrides.py", line 104, in rpc                                            
    result = await self.connection.rpc(msg, encoder=TypeEncoder)    
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/client/connection.py", line 306, in rpc                                           
    result = await self._recv(msg['request-id'])                    
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/client/connection.py", line 208, in _recv                                         
    return await self.messages.get(request_id)                      
  File "/home/stone/src/osm/N2VC/modules/libjuju/juju/utils.py", line 61, in get                                                        
    value = await self._queues[id].get()                            
  File "/usr/lib/python3.6/asyncio/queues.py", line 169, in get     
    getter.cancel()  # Just in case getter is not done yet.         
  File "/usr/lib/python3.6/asyncio/base_events.py", line 574, in call_soon                                                              
    self._check_closed()          
  File "/usr/lib/python3.6/asyncio/base_events.py", line 357, in _check_closed                                                          
    raise RuntimeError('Event loop is closed')                      
RuntimeError: Event loop is closed
```
