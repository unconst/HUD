from asyncio import futures
from invoke import Result
import digitalocean
import bittensor
import paramiko
import fabric
import os
from regex import R
import yaml
import json
from typing import Callable, List, Optional, Union, Tuple
from fabric import Connection
import pandas as pd

import os
import sys
import re
import time
import random
import threading
import concurrent
from bittensor._subtensor.subtensor_impl import Subtensor
import yaml
import bittensor
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import utils
from rich import print
from rich.console import Console
from rich.table import Table
from rich import pretty
from tqdm import trange

import patchwork.transfers
pretty.install()

from retry import retry

from loguru import logger
logger.add( sys.stdout, format="{level} {message}", level="INFO", colorize=True, enqueue=True)


DEBUG = False
VERSION = "0.1.0"
MAX_THREADS = 100000
TIMEOUT = 30

class Neuron:
    def __init__( self, name: str, sshkey:str, ip_address: str, wallet: 'bittensor.Wallet' ):
        self.name = name
        self.sshkey = sshkey
        self.wallet = wallet
        self.ip_address = ip_address
        self._connection = None
        self.metadata = None 

    def __str__(self) -> str:
        return "N({})".format( self.name)

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other):
        if self.wallet.name == other.wallet.name:
            try:
                me = int( re.findall(r'\d+', self.wallet.hotkey_str )[-1] )
                them = int( re.findall(r'\d+', other.wallet.hotkey_str)[-1] )
                return me < them
            except Exception as e:
                return self.wallet.hotkey_str < other.wallet.hotkey_str
        else:
            return self.wallet.name < other.wallet.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == hash(other)
        else:
            return self.name == other.name

    @property
    def connection(self) -> Connection:

        if self._connection is None:
            key = paramiko.RSAKey.from_private_key_file( os.path.expanduser( self.sshkey ) )
            self._connection = Connection( self.ip_address, user='root', connect_kwargs={ "pkey" : key } )
            return self._connection
        else:
            return self._connection

    def reset_connection(self):
        key = paramiko.RSAKey.from_private_key_file( os.path.expanduser( self.sshkey ) )
        self._connection = Connection( self.ip_address, user='root', connect_kwargs={ "pkey" : key } )

    @property
    def can_connect( self ) -> bool:
        try:
            result = self.connection.run('')
            return True
        except:
            return False

    def is_installed( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> bool:
        return HUD(self).is_installed(warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def is_registered( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> bool:
        return HUD(self).is_registered(warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def is_running( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> bool:
        return HUD(self).is_running(warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def get_metadata(self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> 'dict':
        return HUD(self).get_network_metadata(warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def get_hotkey( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> str:
        return HUD(self).get_hotkey( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def get_coldkey( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> str:
        return HUD(self).get_coldkey( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def get_branch( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> str:
        return HUD(self).get_branch(warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def start( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> bool:
        return HUD(self).start(warn = warn, hide = hide, disown = disown, timeout = timeout)

    def get_logs( self, lines:int = 5, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ):
        return HUD(self).get_logs(lines = lines, warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def get_cpu_usage( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).get_cpu_usage( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]
        #result = self.run( "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'" )
        #return result.stdout

    def clear_cache( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).clear_cache( warn = warn, hide = hide, disown = disown, timeout = timeout )[self]
        #self.run( "rm -rf ~/.bittensor/miners && rm -rf /root/.pm2/logs/" )

    def reboot( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).reboot( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def pull(self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).pull( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def install(self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).install( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def checkout_branch(self, branch, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).checkout( branch = branch, warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def pm2_show_script( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).pm2_show_script( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def pm2_describe_script( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        return HUD(self).pm2_describe_script( warn = warn, hide = hide, disown = disown, timeout = timeout)[self]

    def subtensor_best(self) -> int:
        sublogs = self.run( 'docker logs node-subtensor --tail 100').stderr
        idx = int(sublogs.rfind("best: #"))
        return int( sublogs[idx + 7: idx + 14] )


class HUDDict(dict):
    def __init__(self,*args,**kwargs) : dict.__init__(self,*args,**kwargs) 
    def __getitem__(self, key):
        if isinstance(key, HUD):
            return super().__getitem__(key.item())
        elif isinstance(key, Neuron):
            return super().__getitem__(key)
        elif isinstance(key, str):
            for k,v in self.items():
                if k.name == key:
                    return v
            raise KeyError(key)

class HUD(list):
    max_threads = 10000

    def __init__(self, neurons: Union[ Neuron, List[Neuron], 'HUD' ] = []):
        if isinstance( neurons, HUD ):
            self.values = neurons.values
        elif isinstance( neurons, Neuron ):
            self.values = [ neurons ]
        else:
            self.values = neurons
        self.values = sorted(self.values)
        self._set()

    def _set(self):
        super(HUD, self).__init__( self.values )
        self.ndict = {}
        for n in self.values:
            self.ndict[n.name] = n

    def debug():
        global DEBUG
        DEBUG = True
    
    def set_debug(debug):
        global DEBUG
        DEBUG = debug

    def __getitem__(self, idx ):
        if isinstance( idx, str ):
            return HUD( self.ndict[idx] )
        return HUD( self.values[ idx ] )

    def __setitem__(self, idx, value):
        if isinstance( value, HUD ):
            self.values[idx] = value.values
        else:
            self.values[idx] = value
        self._set()

    def __iadd__(self, other):
        self.values.extend( other.values )
        self._set()
        return self  

    def __add__(self, other):
        self.values.extend( other.values )
        self._set()
        return self  

    def append(self, item):
        print(self, self.values, item )
        self.values.extend( item.values )
        self._set()
        print(self)
        return self

    def extend(self, items):
        self.values.extend( items )
        self._set()

    def item(self):
        if len(self) == 1:
            return self.values[0]

    def get(self, *args):
        nn = []
        for v in args:
            if isinstance(v, list):
                nn = nn + v
            else:
                nn.append(v)
        return HUD( [ self.ndict[n] for n in nn] )

    def start(
            self, 
            script: str = "~/.bittensor/bittensor/bittensor/_neuron/text/advanced_server/main.py", 
            args: str = "--logging.debug --neuron.blacklist.stake.backward 1000 --neuron.blacklist.stake.forward 1000 --subtensor.network nakamoto neuron.model_name distilgpt2", 
            disown: bool = False, 
            hide:bool = not DEBUG,
            warn:bool = False, 
            max_threads: int = MAX_THREADS, 
            timeout: int = TIMEOUT, 
            stdout:bool = True 
        ) -> HUDDict[Neuron, bool]:
        return HUD._start( neurons = self.values, script = script, args = args, warn = warn, hide = hide, disown = disown, max_threads = max_threads, timeout = timeout, stdout = stdout )

    def _start(
            neurons: Union[ List[Neuron], 'HUD' ],
            script: str = "~/.bittensor/bittensor/bittensor/_neuron/text/advanced_server/main.py", 
            args: str = "--logging.debug --neuron.blacklist.stake.backward 1000 --neuron.blacklist.stake.forward 1000 --subtensor.network nakamoto neuron.model_name distilgpt2", 
            disown: bool = False, 
            hide:bool = not DEBUG,
            warn:bool = False, 
            max_threads: int = MAX_THREADS, 
            timeout: int = TIMEOUT, 
            stdout:bool = True
        ) -> HUDDict[Neuron, bool]:
        for n in tqdm(neurons):
            delete_script = "pm2 delete script"
            try:
                n.connection.run( delete_script, warn = warn, hide = hide, disown = disown, timeout = timeout)
            except:
                pass
            neuron_script = "pm2 start {} -f --name script --interpreter python3 -- {} {}".format(script, args, "--wallet.name {} --wallet.hotkey {}".format(n.wallet.name, n.wallet.hotkey_str))
            n.connection.run( neuron_script, warn = warn, hide = hide, disown = disown, timeout = timeout)
        HUD._is_running( neurons, disown = disown, warn = warn, hide = hide )

    def stop(
            self, 
            disown: bool = False, 
            hide:bool = not DEBUG,
            warn:bool = False, 
            max_threads: int = MAX_THREADS, timeout: int = TIMEOUT, 
            stdout:bool = True 
        ) -> HUDDict[Neuron, bool]:
        return HUD._stop( neurons = self.values, warn = warn, hide = hide, disown = disown, max_threads = max_threads, timeout = timeout, stdout = stdout )

    def _stop(
            neurons: Union[ List[Neuron], 'HUD' ],
            disown: bool = False, 
            hide:bool = not DEBUG,
            warn:bool = False, 
            max_threads: int = MAX_THREADS, 
            timeout: int = TIMEOUT, 
            stdout:bool = True
        ) -> HUDDict[Neuron, bool]:
        for n in tqdm(neurons):
            delete_script = "pm2 delete script"
            try:
                n.connection.run( delete_script, warn = warn, hide = hide, disown = disown, timeout = timeout)
            except:
                pass
        HUD._is_running( neurons, disown = disown, warn = warn, hide = hide, timeout = timeout)
    
    def run(self, script: Union[str, Callable], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT, stdout:bool = True ) -> HUDDict[Union[List[str], List[fabric.Result]]]:
        return HUD._run( neurons = self.values, script = script, warn = warn, hide = hide, disown = disown, max_threads = max_threads, timeout = timeout, stdout = stdout )

    @staticmethod
    def _run( neurons: Union[ List[Neuron], 'HUD' ], script: Union[str, Callable], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT, stdout:bool = True, is_ok:bool = False) -> HUDDict[Union[List[str], List[fabric.Result]]]:
        neurons = neurons if isinstance(neurons, list) else HUD(neurons)
        if len(neurons) == 0: return {}
        if isinstance(neurons, Neuron): neurons = [neurons]
        is_script = isinstance(script, str)
        results = HUDDict()
        tbar = trange(len(neurons), desc="Running: {}".format(script), leave=True)
        def _run( n ):
            if not hide: logger.info( 'Running | {} | warn:{}, hide:{}, disown:{}, timeout {}, script:{} '.format( n.name, warn, hide, disown, script, timeout) )
            if not n.can_connect: n.reset_connection()
            try:
                if is_script:
                    r = n.connection.run( script, warn = warn, hide = hide, disown = disown, timeout = timeout )
                    tbar.update(1)
                    return r.stdout.strip() if stdout else r.ok if is_ok else r
                else:
                    tbar.update(1)
                    return script( neuron = n, disown = disown, hide = hide, warn = warn, timeout = timeout)
            except Exception as e:
                if warn or not hide: logger.warning( 'Error | {} | error:{}'.format( n.name, e ) )
                tbar.update(1)
                result = fabric.Result(connection = n.connection)
                result.stdout = str(e)
                result.stderr = str(e)
                return result.stdout.strip() if stdout or not is_script else False if is_ok else result
        futs = []
        with ThreadPoolExecutor(max_workers=min(max_threads, len(neurons))) as executor:
            for n in neurons:
                futs.append( (n, executor.submit(_run, n)) )
        results = HUDDict()
        for n, fut in futs:
            try:
                results[n] = fut.result(timeout = timeout)
            except concurrent.futures.TimeoutError:
                results[n] = "Timeout"            
        return results

    def iters( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, dict[str, int]]:
        return HUD._iters( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout)

    @staticmethod
    def _iters( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, dict[str, int]]:
        neurons = neurons if isinstance(neurons, list) else HUD(neurons)
        def get_total_iters( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT ) -> int:
            result = {}
            try:
                pow_files = neuron.connection.run( "find | grep pow_", disown = disown, hide = hide, warn = warn, timeout = timeout).stdout.strip().split("\n")
            except:
                return HUDDict()
            for filename in pow_files:
                name = filename.split("_c")[1].split("_h")[0] + "-" + filename.split("_h")[1].split(".out")[0]
                if name not in result: result[name] = 0
                out = neuron.connection.run( "tail -n 1 {}".format(filename), disown = disown, hide = hide, warn = warn, timeout = timeout ).stdout
                try:
                    iters = out.rfind("Iters"); block = out.rfind("Block:")
                    niters = int( out[iters+6:block-1] )
                    result[name] += niters
                except:
                    pass
            return result
        return HUD._run( neurons, script = get_total_iters, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def get_network_metadata( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, dict]:
        return HUD._get_network_metadata( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _get_network_metadata( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, dict]:
        neurons = neurons if isinstance(neurons, list) else HUD(neurons)
        def __get_network_metadata( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT ) -> int:
            sub = bittensor.subtensor(network = 'nakamoto')
            metadata = sub.neuron_for_pubkey( ss58_hotkey = neuron.wallet.hotkey.ss58_address )
            neuron.metadata = metadata
            return metadata
        return HUD._run( neurons, script = __get_network_metadata, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout  )

    def is_registered( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._is_registered( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _is_registered( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = neurons if isinstance(neurons, list) else HUD(neurons)
        def __get_is_registered( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            sub = bittensor.subtensor(network = "nakamoto") 
            uid = sub.substrate.query( module='SubtensorModule',  storage_function='Hotkeys', params = [ neuron.wallet.hotkey.ss58_address ] ).value
            if uid == 0:
                return False
            else:
                return True
        return HUD._run( neurons, script = __get_is_registered, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
    
    def query( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._query( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _query( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        bittensor.logging(debug=not hide)
        neurons = HUD(neurons)
        def _do_query( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            wallet = bittensor.wallet( name = "const", hotkey = "Nero" )
            dend = bittensor.dendrite( wallet = wallet )
            endpoint = bittensor.endpoint( version=bittensor.__version_as_int__, uid = 9, hotkey=neuron.wallet.hotkey.ss58_address, ip=neuron.ip_address, ip_type=4, port=bittensor.defaults.axon.port, modality=0, coldkey=neuron.wallet.coldkeypub.ss58_address)
            logger.info( 'Querying | {} | wallet:{}, dend:{}, endpoint:{} '.format( neuron, wallet, dend, endpoint ) )
            return dend.forward_text( endpoints=endpoint, inputs="query")
        bittensor.logging(debug=False)
        return HUD._run( neurons, script = _do_query, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def can_connect( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        return HUD._can_connect( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _can_connect( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        return HUD._run( neurons, script = "", disown = disown, hide = hide, warn = warn, max_threads = max_threads, stdout = False, is_ok = True)

    def reconnect( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        return HUD._reconnect( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _reconnect( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        def ___reconnect( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            neuron.reset_connection()
            return neuron.can_connect
        return HUD._run( neurons, script = ___reconnect, disown = disown, hide = hide, warn = warn, max_threads = max_threads )

    def get_branch( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        return HUD._get_branch( self.values, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _get_branch( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, str]:
        return HUD._run( neurons, script = "cd ~/.bittensor/bittensor ; git branch --show-current", disown = disown, hide = hide, warn = warn, max_threads = max_threads, stdout=True )

    def load_wallet( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._load_wallet( self, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _load_wallet( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        def ___load_wallet( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            neuron.connection.run( "mkdir -p ~/.bittensor/wallets/{}/hotkeys".format( neuron.wallet.name ), warn = warn, hide = hide, disown = disown, timeout = timeout)
            neuron.connection.run( "echo '{}' > ~/.bittensor/wallets/{}/hotkeys/{}".format( open(neuron.wallet.hotkey_file.path, 'r').read(), neuron.wallet.name, neuron.wallet.hotkey_str ), warn = warn, hide = hide, disown = disown, timeout = timeout)
            neuron.connection.run( "echo '{}' > ~/.bittensor/wallets/{}/coldkeypub.txt".format( open(neuron.wallet.coldkeypub_file.path, 'r').read(), neuron.wallet.name ), warn = warn, hide = hide, disown = disown, timeout = timeout)
            return True
        return HUD._run( neurons, script = ___load_wallet, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def get_hotkey( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._get_hotkey( self, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _get_hotkey( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        def ___get_hotkey( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            result = neuron.connection.run( "cat ~/.bittensor/wallets/{}/hotkeys/{}".format( neuron.wallet.name, neuron.wallet.hotkey_str ), warn = warn, hide = hide, disown = disown, timeout = timeout)
            if result.failed: return None
            else: return json.loads(result.stdout)['ss58Address']
        return HUD._run( neurons, script = ___get_hotkey, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def get_coldkey( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._get_coldkey( self, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _get_coldkey( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        def ___get_coldkey( neuron:Neuron, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, timeout: int = TIMEOUT) -> bool:
            result = neuron.connection.run( "cat ~/.bittensor/wallets/{}/coldkeypub.txt".format( neuron.wallet.name ), warn = warn, hide = hide, disown = disown, timeout = timeout)
            if result.failed: return None
            else: return json.loads(result.stdout)['ss58Address']
        return HUD._run( neurons, script = ___get_coldkey, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def install( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, reinstall: bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._install( self, disown = disown, hide = hide, warn = warn, reinstall = reinstall, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _install( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, reinstall: bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        if not reinstall:
            neurons = HUD( [n for n, is_installed in neurons.is_installed().items() if not is_installed] )
        HUD._run( neurons, script = "sudo apt-get update && sudo apt-get install --no-install-recommends --no-install-suggests -y apt-utils curl git cmake build-essential gnupg lsb-release ca-certificates software-properties-common apt-transport-https", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "sudo apt-get install --no-install-recommends --no-install-suggests -y python3", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "sudo apt-get install --no-install-recommends --no-install-suggests -y python3-pip python3-dev python3-venv", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "ulimit -n 500000000 && sudo fallocate -l 20G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && sudo cp /etc/fstab /etc/fstab.bak", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "sudo apt install npm -y", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "sudo npm install pm2@latest -g", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "mkdir -p ~/.bittensor/bittensor/", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "rm -rf ~/.bittensor/bittensor", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "git clone --recurse-submodules https://github.com/opentensor/bittensor.git ~/.bittensor/bittensor", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "cd ~/.bittensor/bittensor ; pip3 install -e .", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._load_wallet( neurons, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._pull( neurons, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        HUD._run( neurons, script = "sudo apt-get update && sudo apt install docker.io -y && rm /usr/bin/docker-compose || true && curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose  && rm -rf subtensor || true && git clone https://github.com/opentensor/subtensor.git && cd subtensor && docker-compose up -d", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        return HUD._is_installed( neurons, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    def is_installed( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._is_installed(self.values, disown, hide, warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _is_installed( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        results = HUD._run( neurons, script = "python3 -c 'import bittensor'", disown=disown, hide=hide, warn=warn, stdout=False, max_threads = max_threads, timeout = timeout )
        for key in results:
            if "ModuleNotFoundError" in results[key].stdout:
                results[key] = False
            else:
                results[key] = True
        return results

    def is_running( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        return HUD._is_running(self.values, disown, hide, warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _is_running( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT ) -> HUDDict[Neuron, bool]:
        neurons = HUD(neurons)
        results = HUD._run( neurons, script = "pm2 pid script", disown=disown, hide=hide, warn=warn, stdout=False, max_threads = max_threads, timeout = timeout )
        for key in results:
            try:
                if int(results[key].stdout) > 1:
                    results[key] = True
                else:
                    results[key] = False
            except:
                results[key] = False
        return results

    def pull( self, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, fabric.Result]:
        return HUD._pull(self.values, disown, hide, warn, max_threads = max_threads, timeout = timeout )
    
    @staticmethod
    def _pull( neurons: Union[ List[Neuron], 'HUD' ], disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, fabric.Result]:
        neurons = neurons if isinstance(neurons, list) else HUD(neurons)
        return HUD._run( neurons, script = "rm -rf ~/HUD && git clone --recurse-submodules https://github.com/unconst/HUD.git ~/HUD", disown=disown, hide=hide, warn=warn, max_threads = max_threads, timeout = timeout, stdout=False )

    def get_logs( self, lines:int = 5, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, str]:
        return HUD._get_logs(self.values, lines = lines, disown=disown, hide=hide, warn=warn, max_threads = max_threads, timeout = timeout )
    
    @staticmethod
    def _get_logs( neurons: Union[ List[Neuron], 'HUD' ], lines:int = 5, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> HUDDict[Neuron, str]:
        neurons = HUD(neurons)
        return HUD._run( neurons, script = "tail -n {} /root/.pm2/logs/script-out.log".format( lines ), disown=disown, hide=hide, warn=warn, stdout=True )

    def pow( self, targets: Union[ Neuron, List[Neuron], 'HUD' ], pow_key: int = int(time.time()), n_procs: int = 1, network:str = "nakamoto", disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> None:
        return HUD._pow( self.values, targets = targets, n_procs = n_procs, network = network, disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )

    @staticmethod
    def _pow( workers: Union[ List[Neuron], 'HUD' ], targets: Union[ Neuron, List[Neuron], 'HUD' ], n_procs: int = 1, network:str = "nakamoto", disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT):
        workers = HUD(workers)
        targets = HUD(targets)
        logger.info( "Starting PoW | targets:{} workers: {}".format( targets, workers ) )
        for target, is_registered in targets.is_registered().items():
            if not is_registered:
                HUD._run( workers, script = "pkill -f **h{}** & rm **h{}**".format( target.wallet.hotkey_str, target.wallet.hotkey_str ), disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
                HUD._run( workers, script = "mkdir -p ~/.bittensor/wallets/{}/hotkeys".format( target.wallet.name ), disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
                HUD._run( workers, script = "echo '{}' > ~/.bittensor/wallets/{}/hotkeys/{}".format( open(target.wallet.hotkey_file.path, 'r').read(), target.wallet.name, target.wallet.hotkey_str ), disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
                HUD._run( workers, script = "echo '{}' > ~/.bittensor/wallets/{}/coldkeypub.txt".format( open(target.wallet.coldkeypub_file.path, 'r').read(), target.wallet.name ), disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
                for i in range(n_procs):
                    HUD._run( workers, script = "nohup python3 HUD/pow.py --subtensor.network {} --wallet.name {} --wallet.hotkey {} > pow_{}_c{}_h{}.out &".format(network, target.wallet.name, target.wallet.hotkey_str, i, target.wallet.name, target.wallet.hotkey_str), disown = True, hide = True, warn = False, max_threads = max_threads, timeout = timeout )

    def kill_pow( self, targets:Optional[Union[ Neuron, List[Neuron], 'HUD' ]] = None, disown: bool = False, hide:bool = not DEBUG, warn:bool = False, max_threads: int = MAX_THREADS, timeout: int = TIMEOUT) -> None:
        if targets != None:
            targets = HUD(targets)
            for tar in targets:
                logger.info( "Killing PoW | target:{} ".format( tar ) )
                HUD._run( self.values, script = "pkill -f **h{}** & rm **h{}**".format( tar.wallet.hotkey_str, tar.wallet.hotkey_str ), disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )
        else:
            HUD._run( self.values, script = "pkill -f pow.py & rm  pow_*", disown = disown, hide = hide, warn = warn, max_threads = max_threads, timeout = timeout )


    @staticmethod
    def write_to_config( neurons: list['Neuron'] ):
        config = {}
        for n in neurons:
            if n.wallet.name not in config:
                config[n.wallet.name] = {}
                config[n.wallet.name][n.wallet.name] = {}
            config[ n.wallet.name ][ n.wallet.name ][ n.wallet.hotkey_str ] = {  'sshkey': str(n.sshkey), 'ip_address': str(n.ip_address) }
        for project in config.keys():
            with open( 'configs/{}.yaml'.format(project), 'w' ) as f:
                yaml.dump( config[project], f, default_flow_style=False )

    @staticmethod
    def load_from_digital_ocean( tag:str = None ) -> 'HUD[Neuron]':
        manager = digitalocean.Manager( token = os.getenv( 'MARIUS_DOTOKEN' ))
        if tag is None:
            droplets = manager.get_all_droplets()
        else:
            droplets = manager.get_all_droplets( tag_name = [ tag ] )
        neurons = []
        for drop in droplets:
            try:
                tag = drop.tags[0]
                name = "{}-{}".format( tag, drop.name )
                neurons.append( Neuron ( 
                    name, 
                    sshkey = os.getenv( 'MARIUS_SSH_KEY' ),
                    ip_address = drop.ip_address,
                    wallet = bittensor.wallet( name = tag, hotkey = drop.name )
                ) ) 
            except:
                pass
        return HUD( neurons )

    @staticmethod
    def load_from_config( project ) -> 'HUD[Neuron]':
        with open( 'configs/{}.yaml'.format( project ), "r") as config_file:
            config = yaml.safe_load(config_file)
        config = bittensor.Config.fromDict(config)[project]
        neurons = []
        for hotkey in config:
            name = "{}-{}".format( project, hotkey )
            neurons.append( Neuron(
                name = name,
                sshkey = config[hotkey]['sshkey'],
                ip_address = config[hotkey]['ip_address'],
                wallet = bittensor.wallet( name = project, hotkey=hotkey)
            ))
        return HUD( neurons )