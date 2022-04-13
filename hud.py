import digitalocean
import paramiko
import digitalocean
import fabric
import bittensor
import os
import yaml
import json
from typing import List
from fabric import Connection
import pandas as pd

import os
import sys
import time
import random
import threading
from bittensor._subtensor.subtensor_impl import Subtensor
import yaml
import bittensor
import argparse
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import utils
from rich import print
from rich.console import Console
from rich.table import Table
from rich import pretty
import patchwork.transfers
pretty.install()

from retry import retry

from loguru import logger
logger.add( sys.stdout, format="{level} {message}", level="INFO", colorize=True, enqueue=True)


DEBUG = False
VERSION = "0.1.0"

class Neuron:
    def __init__( self, name: str, sshkey:str, ip_address: str, wallet: 'bittensor.Wallet' ):
        self.name = name
        self.sshkey = sshkey
        self.wallet = wallet
        self.ip_address = ip_address
        self._connection = None
        try:
            self.history = pd.read_csv( "history/{}.csv".format(self.name) )
            self.history = self.history.set_index('datetime', drop = False)
            self.history = self.history.sort_index(ascending=False)
        except:
            self.history = pd.DataFrame()

    def __str__(self) -> str:
        return "neuron({},{},{},{})".format( self.name, self.sshkey, self.ip_address, self.wallet)

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def connection(self) -> Connection:
        if self._connection is None:
            key = paramiko.RSAKey.from_private_key_file( os.path.expanduser( self.sshkey ) )
            self._connection = Connection( self.ip_address, user='root', connect_kwargs={ "pkey" : key })
            return self._connection
        else:
            return self._connection

    @property
    def can_connect( self ) -> bool:
        try:
            result = self.connection.run('')
            return True
        except:
            return False
    
    def _check( self ):
        if not self.can_connect:
            raise Exception( "Can't connect to machine" )
    
    def run( self, cmd:str ):
        if DEBUG:
            print ( "{}| Running: {}".format(self.name, cmd) )
        result = self.connection.run( cmd, warn = True, hide = not DEBUG)
        return result

    @property
    def is_installed( self ) -> bool:
        result = self.run( 'python3 -c "import bittensor"' )
        return result.ok

    @retry(tries=3)
    def get_neuron( self ) -> dict:
        sub = bittensor.subtensor(network='nakamoto')
        return sub.neuron_for_pubkey( ss58_hotkey = self.wallet.hotkey.ss58_address )

    @property
    def neuron(self) -> 'bittensor.Neuron':
        return self.get_neuron()

    @property
    def is_registered( self ) -> bool:
        neuron = self.get_neuron()
        return not neuron.is_null

    @property
    def hotkey( self ) -> str:
        result = self.run( "cat ~/.bittensor/wallets/{}/hotkeys/{}".format( self.wallet.name, self.wallet.hotkey_str )  )
        if result.failed: return None
        else: return json.loads(result.stdout)['ss58Address']

    @property
    def coldkey( self ) -> str:
        result = self.run( "cat ~/.bittensor/wallets/{}/coldkeypub.txt".format( self.wallet.name ) )
        if result.failed: return None
        else: return json.loads(result.stdout)['ss58Address']

    @property
    def branch(self) -> str:
        try:
            result = self.run( 'cd ~/.bittensor/bittensor ; git branch --show-current' )
            if result.failed: return None
            else: return result.stdout.strip()
        except:
            return 'None'

    @property
    def is_running( self ) -> bool:
        result = self.run( 'pm2 pid script')
        if len(result.stdout) > 1: return True
        else: return False  

    def pull(self):
        self.run('rm -rf ~/HUD')
        self.run('git clone --recurse-submodules https://github.com/unconst/HUD.git ~/HUD')
    
    def install(self):
        self.run("sudo apt-get update && sudo apt-get install --no-install-recommends --no-install-suggests -y apt-utils curl git cmake build-essential gnupg lsb-release ca-certificates software-properties-common apt-transport-https")
        self.run("sudo apt-get install --no-install-recommends --no-install-suggests -y python3")
        self.run("sudo apt-get install --no-install-recommends --no-install-suggests -y python3-pip python3-dev python3-venv")
        self.run("ulimit -n 50000 && sudo fallocate -l 20G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && sudo cp /etc/fstab /etc/fstab.bak")
        self.run("sudo apt install npm -y")
        self.run("sudo npm install pm2@latest -g")
        self.run('mkdir -p ~/.bittensor/bittensor/')
        self.run('rm -rf ~/.bittensor/bittensor')
        self.run('git clone --recurse-submodules https://github.com/opentensor/bittensor.git ~/.bittensor/bittensor')
        self.run('cd ~/.bittensor/bittensor ; pip3 install -e .')
        self.run("sudo apt-get update && sudo apt install docker.io -y && rm /usr/bin/docker-compose || true && curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose  && rm -rf subtensor || true && git clone https://github.com/opentensor/subtensor.git && cd subtensor && docker-compose up -d")
    
    def checkout_branch(self, branch):
        if "tags/" in branch:
            branch_str = "%s -b tag-%s" % (branch, branch.split("/")[1])
        else:
            branch_str = branch
        self.run( 'cd ~/.bittensor/bittensor ; git checkout %s' % branch_str )

    def pm2_show_script( self ):
        print( self.run( "pm2 show script" ) )

    def pm2_describe_script( self ):
        print( self.run( "pm2 describe script" ) )

    # write a function that returns the last n lines of the file /root/.pm2/logs/script-out.log on the machine
    def get_logs( self, lines:int ):
        result = self.run( "tail -n {} /root/.pm2/logs/script-out.log".format( lines ) )
        return result.stdout

    def clear_cache( self ):
        self.run( "rm -rf ~/.bittensor/miners && rm -rf /root/.pm2/logs/" )

    def reboot( self ):
        self.run( "sudo shutdown -r now -f")

    # write a function that returns the CPU usage of the machine
    def get_cpu_usage( self ):
        result = self.run( "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'" )
        return result.stdout

    # write a function that returns all running procesess on the machine
    def get_running_procs(self):
        result = self.run( "ps aux" )
        return result.stdout

    def load_wallet( self ):
        self.run( "mkdir -p ~/.bittensor/wallets/{}/hotkeys".format( self.wallet.name ) ) 
        self.run( "echo '{}' > ~/.bittensor/wallets/{}/hotkeys/{}".format( open(self.wallet.hotkey_file.path, 'r').read(), self.wallet.name, self.wallet.hotkey_str ) )
        self.run( "echo '{}' > ~/.bittensor/wallets/{}/coldkeypub.txt".format( open(self.wallet.coldkeypub_file.path, 'r').read(), self.wallet.name ) )

    def add_wallet( self, wallet: bittensor.Wallet ):
        self.run( "mkdir -p ~/.bittensor/wallets/{}/hotkeys".format( wallet.name ) ) 
        self.run( "echo '{}' > ~/.bittensor/wallets/{}/hotkeys/{}".format( open(wallet.hotkey_file.path, 'r').read(), wallet.name, wallet.hotkey_str ) )
        self.run( "echo '{}' > ~/.bittensor/wallets/{}/coldkeypub.txt".format( open(wallet.coldkeypub_file.path, 'r').read(), wallet.name ) )

    def register( 
            self, 
            wallet: 'bittensor.Wallet' 
        ):
        self.add_wallet( wallet )
        self.connection.run(
            "pm2 start ~/.bittensor/bittensor/bin/btcli --name register_{}_{} --interpreter python3 -- register --wallet.name {} --wallet.hotkey {} --no_prompt".format( wallet.name, wallet.hotkey_str, wallet.name, wallet.hotkey_str ), 
            warn=False, 
            hide=not DEBUG, 
            disown = False, 
        )

    def subtensor_best(self) -> int:
        sublogs = self.run( 'docker logs node-subtensor --tail 100').stderr
        idx = int(sublogs.rfind("best: #"))
        return int( sublogs[idx + 7: idx + 14] )

    def kill_register( self, wallet: 'bittensor.Wallet' ):
        self.connection.run(
            "pm2 delete register_{}_{}".format( wallet.name, wallet.hotkey_str ), 
            warn=False, 
            hide=not DEBUG, 
            disown = False, 
        )

    def kill_old_register( self, wallet: 'bittensor.Wallet' ):
        self.run( "pm2 delete registration")

    def stats(self, forced:bool = False, refresh_secs: int = 60 * 20) -> dict:
        seconds_since_epoch = int( time.time() )
        if len(list(self.history.index)) != 0:
            latest_time = self.history.index.max()
            if seconds_since_epoch - latest_time < refresh_secs and not forced:
                return self.history.loc[latest_time]
        neuron = self.get_neuron()
        stats = {
            'version': VERSION,
            'datetime': int( seconds_since_epoch ),
            'name': self.name,
            'ip_address': self.ip_address,
            'sshkey': self.sshkey,
            'can_connect': self.can_connect,
            'branch': self.branch,
            'is_installed': self.is_installed,
            'is_running': self.is_running,
            'is_registered': not neuron.is_null,
            'uid': neuron.uid,
            'stake': neuron.stake,
            'rank': neuron.rank,
            'trust': neuron.trust,
            'consensus': neuron.consensus,
            'incentive': neuron.incentive,
            'dividends': neuron.dividends,
            'emission': neuron.emission,
            'last_update': neuron.last_update,
            'active': neuron.active,
            'cpu_usage': self.get_cpu_usage(),
            'hotkey': self.hotkey,
            'coldkey': self.coldkey
        }
        if self.history.empty:
            self.history = pd.DataFrame( [stats], index = [stats['datetime']], columns=stats.keys() )
            self.history = self.history.sort_index(ascending=False)
            self.history = self.history.set_index('datetime', drop = False)
        else:
            self.history.loc[seconds_since_epoch] = stats
        self.history = self.history.loc[:, ~self.history.columns.str.contains('^Unnamed')]
        self.history.to_csv( "history/{}.csv".format(self.name), index=False)
        self.history = self.history.sort_index(ascending=False)
        self.history = self.history.set_index('datetime', drop = False)
        return self.history.loc[seconds_since_epoch]


class HUD:

    def debug():
        global DEBUG
        DEBUG = True
    
    def set_debug(debug):
        global DEBUG
        DEBUG = debug
    
    @staticmethod
    def append_to_config( neurons: list['Neuron'] ):
        config = {}
        for n in neurons:
            if n.wallet.name not in config:
                config[n.wallet.name] = {}
            config[ n.wallet.name ][ n.wallet.hotkey_str ] = {  'sshkey': str(n.sshkey), 'ip_address': str(n.ip_address) }
        with open( 'config.yaml', 'a' ) as f:
            yaml.dump( config, f, default_flow_style=False )

    @staticmethod
    def write_to_config( neurons: list['Neuron'] ):
        config = {}
        for n in neurons:
            if n.wallet.name not in config:
                config[n.wallet.name] = {}
            config[ n.wallet.name ][ n.wallet.hotkey_str ] = {  'sshkey': str(n.sshkey), 'ip_address': str(n.ip_address) }
        with open( 'config.yaml', 'w' ) as f:
            yaml.dump( config, f, default_flow_style=False )

    @staticmethod
    def load_from_digital_ocean( tag:str = None ) -> list['Neuron']:
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
        return neurons

    @staticmethod
    def load_all_from_config( tag: str = None ) -> dict[list['Neuron']]:
        with open( 'config.yaml', "r") as config_file:
            config = yaml.safe_load(config_file)
        neurons = []
        if tag == None:
            config = bittensor.Config.fromDict(config)
            for coldkey in config:
                for hotkey in config[coldkey]:
                    name = "{}-{}".format( coldkey, hotkey )
                    neurons.append( Neuron(
                        name = name,
                        sshkey = config[coldkey][hotkey]['sshkey'],
                        ip_address = config[coldkey][hotkey]['ip_address'],
                        wallet = bittensor.wallet( name = coldkey, hotkey=hotkey)
                    ))
        else:
            config = bittensor.Config.fromDict(config)[tag]
            for hotkey in config:
                name = "{}-{}".format( tag, hotkey )
                neurons.append( Neuron(
                    name = name,
                    sshkey = config[hotkey]['sshkey'],
                    ip_address = config[hotkey]['ip_address'],
                    wallet = bittensor.wallet( name = tag, hotkey=hotkey)
                ))
        return neurons


    @staticmethod
    def rsync( neurons: List[Neuron] ):
        results = {}
        import subprocess
        for n in tqdm( neurons ):
            command = "rsync  -pthrvz  --rsh='ssh -i {} -p 22 ' copy root@{}:/root/copy".format(n.sshkey, n.ip_address)
            results[n.name] = subprocess.run(command, shell=True)
        return results

    @staticmethod
    def run( neurons: List[Neuron], script:str, disown: bool = True, hide:bool = not DEBUG, warn:bool = False) -> List[str]:
        results = {}
        def _run(n):
            if not hide: logger.info( 'Running | {} | warn:{}, hide:{}, disown:{}, script:{} '.format( n.name, warn, hide, disown, script ) )
            try:
                result = n.connection.run(
                    script, 
                    warn = warn, 
                    hide = hide, 
                    disown = disown, 
                )
                results[n.name] = result
            except Exception as e:
                if warn or not hide: logger.warning( 'Error | {} | error:{}'.format( n.name, e ) )

        with ThreadPoolExecutor(max_workers=len(neurons)) as executor:
            for n in tqdm( neurons ):
                executor.submit(_run, n)
        return results


    @staticmethod
    def register( workers, neuron, timeout) -> bool:
        def _kill_register(worker):
            logger.info( 'Killing | {} '.format( worker.name ) )
            worker.kill_register( neuron.wallet )
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            for worker in workers:
                executor.submit(_kill_register, worker)
        def _register(worker):
            logger.info( 'Killing | {} '.format( worker.name ) )
            worker.register( neuron.wallet )
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            for worker in workers:
                executor.submit(_register, worker)
        print ('Registrations sumbitted')
        inc = 5
        n_blocks = int( timeout / inc )
        blocks = list(range(n_blocks))
        for b in tqdm(blocks):
            try:
                meta = neuron.get_neuron()
                if not meta.is_null:
                    print ('Registered :)')
                    return True
            except Exception as e:
                print ( '{}'.format(e) )
            time.sleep(inc)
        def _kill_register(worker):
            worker.kill_register( neuron.wallet )
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            for worker in workers:
                print ('Killing: {} --> {}'.format(neuron.wallet, worker ))
                executor.submit(_kill_register, worker)
        print ('Failed to register :( ')
        return False



    @staticmethod
    def status(neurons:dict['Neuron'], forced:bool = False, refresh_secs: int = 60 * 20) -> dict:
        def get_stats(neuron):
            try:
                return neuron.stats(forced = forced, refresh_secs = refresh_secs)
            except:
                return 

        def get_pandas(list_neurons):
            stats = []
            with ThreadPoolExecutor(max_workers=len(list_neurons)) as executor:
                stats = list(tqdm(executor.map(get_stats, list_neurons), total=len(list_neurons)))
            return pd.DataFrame( stats, columns=stats[0].keys() )
        if isinstance( neurons, list):
            return get_pandas( neurons )
        else:
            result = []
            for key in neurons.keys():
                result.append( get_pandas( neurons[key] ))
            return pd.concat( result, axis=0 )

    @staticmethod
    def rich_row( stats ) -> str:
        name_str = '[bold green]' + stats['name']
        ip_address_str = '[bold green]' + stats['ip_address']
        sshkey_str = '[bold green]' + stats['sshkey']
        hotkey_str =  '[bold green]' + stats['hotkey']
        coldkey_str =  '[bold green]' + stats['coldkey']
        branch_str = '[bold yellow] Yes' + stats['branch']
        can_connect_str = '[bold green] Yes' if stats['can_connect'] else '[bold red] No'
        is_installed_str = '[bold green] Yes' if stats['is_installed'] else '[bold red] No'
        is_running_str = '[bold green] Yes' if stats['is_running'] else '[bold red] No'
        is_registered_str = '[bold green] Yes' if stats['is_registered'] else '[bold red] No'
        metrics = [
            str( stats['uid'] ), 
            '{:.5f}'.format( stats['stake']),
            '{:.5f}'.format(  stats['rank']), 
            '{:.5f}'.format(  stats['trust']), 
            '{:.5f}'.format(  stats['consensus']), 
            '{:.5f}'.format(  stats['incentive']),
            '{:.5f}'.format(  stats['dividends']),
            '{:.5f}'.format(  stats['emission']),
            str( stats['last_update']),
            str( stats['active'] ), 
        ]
        return [ name_str, ip_address_str, sshkey_str, can_connect_str, branch_str, is_installed_str, is_running_str, is_registered_str] + metrics + [ coldkey_str, hotkey_str ]  

    @staticmethod
    def table( neurons:list['Neuron'] ):

        def get_stats(neuron):
            return neuron.stats()

        stats = []
        with ThreadPoolExecutor(max_workers=len(neurons)) as executor:
            stats = list(tqdm(executor.map(get_stats, neurons), total=len(neurons)))

        total_stake = 0
        total_rank = 0
        total_trust = 0
        total_dividends = 0
        total_consensus = 0
        total_emission = 0
        total_incentive = 0
        for s in stats:
            total_stake += s['stake']
            total_rank += s['rank']
            total_trust += s['trust']
            total_consensus += s['consensus']
            total_dividends += s['dividends']
            total_emission += s['emission']
            total_incentive += s['incentive']

        TABLE_DATA = [ HUD.rich_row(s) for s in stats ]
        print ( TABLE_DATA )
        TABLE_DATA = [row for row in TABLE_DATA if row != None ]
        TABLE_DATA.sort(key = lambda TABLE_DATA: TABLE_DATA[0])
        table = Table(show_footer=False)
        table.title = (
            "[bold white]HUD" 
        )
        table.add_column("[overline white]Name",  str(len(neurons)), footer_style = "overline white", style='white')
        table.add_column("[overline white]IP", style='blue')
        table.add_column("[overline white]sshkey", style='green')
        table.add_column("[overline white]Connected", style='green')
        table.add_column("[overline white]Branch", style='bold purple')
        table.add_column("[overline white]Installed")
        table.add_column("[overline white]Running")
        table.add_column("[overline white]Registered")
        table.add_column("[overline white]Uid", footer_style = "overline white", style='yellow')
        table.add_column("[overline white]Stake", '{:.5f}'.format(total_stake), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Rank", '{:.5f}'.format(total_rank), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Trust", '{:.5f}'.format(total_trust), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Consensus", '{:.5f}'.format(total_consensus), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Incentive", '{:.5f}'.format(total_incentive), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Dividends", '{:.5f}'.format(total_dividends), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Emission", '{:.5f}'.format(total_emission), footer_style = "overline white", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Lastupdate (blocks)", justify='right', no_wrap=True)
        table.add_column("[overline white]Active", justify='right', style='green', no_wrap=True)
        table.add_column("[overline white]Coldkey", style='bold blue', no_wrap=False)
        table.add_column("[overline white]Hotkey", style='blue', no_wrap=False)
        table.show_footer = True

        for row in TABLE_DATA:
            table.add_row(*row)
        table.box = None
        table.pad_edge = False
        table.width = None
        console = Console()
        console.print(table, width=10000)