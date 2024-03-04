import os
import subprocess
import requests
import re
import sys
import logging

logger = logging.getLogger('cookieDough')

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class Assets():
    def __init__(self, name, type, status, flagged_custom, flagged_generic, culprit=False):
        self.name = name
        self.type = type
        self.status = status
        self.flagged_custom = flagged_custom
        self.flagged_generic = flagged_generic
        self.culprit = culprit
        logger.info(f'Starting asset {self.name}...')
    
class Site():
    def __init__(self, warning_re, wp_cli_path='wp'):
        self.wp_cli_path = wp_cli_path
        self.wordpress_info = {
            'site_url': None,
            'plugins': [],
            'theme': []
        }
        self.warning_re = warning_re
        logger.info('Setting up site...')
    
    def get_siteurl(self):
        directory = list(filter(None, os.getcwd().split('/')))
        regex_urL = re.compile(r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
        cmd = 'wp option get siteurl --skip-themes --skip-plugins'
        stdout, stderr = run_command(cmd)
        if self.warning_re.search(stderr) or stdout is None or not regex_urL.search(stdout):
            print('SiteURL CLI failed, falling back to getting the domain name based on the domain directory')
            self.wordpress_info['site_url'] = f'https://{directory[3]}'
            logger.debug(f'WP-CLI failed to obtain the URL: {stderr}')
        else:
            self.wordpress_info['site_url'] = stdout
            logger.info('SiteURL loaded from WP-CLI...')
        if self.url_mod:
            if self.url_mod.startswith('/'):
                self.url_mod = self.url_mod
            else:
                self.url_mod = f'/{self.url_mod}'
            self.wordpress_info['site_url'] = self.wordpress_info['site_url'] + self.url_mod
            logger.info(f'Added {self.url_mod} to the siteURL...')
        else:
            self.wordpress_info['site_url'] = stdout
        logger.info('Loaded siteURL...')
        
    
    def create_assets(self, mode):
        if mode == 'plugin':
            assets = self.wordpress_info['plugins'].split()
        else:
            assets = self.wordpress_info['theme'].split()
        result = []
        for asset in assets:
            asset_info = Assets(asset, mode, 'active', False, False, False)
            info = {'name': asset_info.name,
                    'type': asset_info.type, 
                    'status': asset_info.status, 
                    'flagged_custom': asset_info.flagged_custom,
                    'flagged_generic': asset_info.flagged_generic, 
                    'culprit': asset_info.culprit}
            result.append(info)
        logger.info(f'Creating asset dictionary for {mode}...')
        return result

    def active_plugins_and_themes(self):
        cmd = 'wp plugin list --status=active --field=name --skip-themes --skip-plugins'
        plugins_out, stderr  = run_command(cmd)
        if self.warning_re.search(stderr) or plugins_out is None:
            print(f'Active plugins cannot be listed.')
            logger.debug(f'WP-CLI failed to list plugins: {stderr}')
            sys.exit()
        else:
            self.wordpress_info['plugins'] = plugins_out
            plugins_info = self.create_assets('plugin')
        cmd = 'wp theme list --status=active,parent --field=name --skip-themes --skip-plugins'
        themes_out, stderr = run_command(cmd)
        if self.warning_re.search(stderr) or themes_out is None:
            print(f'Active themes cannot be listed.')
            logger.debug(f'WP-CLI failed to list themes: {stderr}')
            sys.exit()
        else:
            self.wordpress_info['theme'] = themes_out
            themes_info = self.create_assets('theme')
        logger.info('Returning plugin/theme info...')
        return plugins_info, themes_info
    
    def get_wordpress_info(self, url_mod):
        self.url_mod = url_mod
        self.get_siteurl()
    
    def folder_check(self):
        directory = list(filter(None, os.getcwd().split('/')))
        if len(directory) <= 2:
            print(f'This script cannot be run on the user directory or lower. Current path is {directory}\nBye!')
            logger.debug(f'Script ran from {directory}, exiting...')
            exit()
        elif len(directory) > 3:
            move_backwards = ''
            directory_size = len(directory) - 3
            for size in range(directory_size):
                move_backwards = move_backwards + '../'
            os.chdir(move_backwards)
            directory = os.getcwd()
            return directory

class CookieMonster():
    def __init__(self, warning_re):
        self.cookie_jar = None
        self.headers = None
        self.warning_re = warning_re

    def go_back(self, toggled_plugins):
        if toggled_plugins:
            print(f'cURL failed after plugins had been toggled, Re-activating. \nYou can use the flag --skip_plugins to skip this (Run python3 cookie_monster.py --h for more info).')
            for plugin in toggled_plugins:
                self.plugin_toggler(plugin)

    ## - Function to cURL to the site, used multiple times on the script.
    def curling_not_the_sport(self, curl_url, toggled_plugins, timeout, redirects):
        if not timeout:
            timeout = 30
        if not redirects:
            redirects = True
        try:
            curl_site = requests.get(curl_url, timeout=timeout, allow_redirects=redirects)
            curl_site.raise_for_status()
            self.cookie_jar = curl_site.cookies.get_dict().keys()
            self.headers = curl_site.headers
            logger.info(f'cURL successful: {curl_site.status_code}...')
        except requests.exceptions.HTTPError as errh:
            print (f'HTTP error, cURL to {curl_url} failed. Error below \n  {errh}')
            self.go_back(toggled_plugins)
            logger.debug(f'cURL failed: {errh}\nExiting after toggling all plugins back.')
            exit()
        except requests.exceptions.ConnectionError as errc:
            print (f'Error connecting, cURL to {curl_url} failed. Error below \n  {errc}')
            self.go_back(toggled_plugins)
            logger.debug(f'cURL failed: {errc}\nExiting after toggling all plugins back.')
            exit()
        except requests.exceptions.Timeout as errt:
            print (f'Timeout Error, cURL to {curl_url} failed. Error below \n  {errt}')
            self.go_back(toggled_plugins)
            logger.debug(f'cURL failed: {errt}\nExiting after toggling all plugins back.')
            exit()
        except requests.exceptions.RequestException as err:
            print (f'Oops: Something unidentified happened, cURL to {curl_url} failed. Error below \n  {err}')
            self.go_back(toggled_plugins)
            logger.debug(f'cURL failed: {err}\nExiting after toggling all plugins back.')
            exit()

    ## - Finding only custom cookies and filtering them if set to exclusion = 'custom', otherwise it will check the # of the cookies, used for sites setting more than 1 cookie at the time.
    def cookie_monster(self, exclusion='custom'):
        logger.info('Checking cookies...')
        if exclusion == 'custom':
            custom_cookies = []
            try:
                cookie_check = self.cookie_jar
            except ValueError:
                print(f'No cookies found.')
                cookie_check = None
            exclusion_list = ['PHPSESSID', 'session_start', 'start_session', 'cookie', 'setCookie']
            for cookie in cookie_check:
                if cookie not in exclusion_list:
                    custom_cookies.append(cookie)
            if not custom_cookies:
                pass
            else:
                custom_cookies_filtered = list(filter(None, custom_cookies))
                print(f'Found custom cookies(s): {", ".join(custom_cookies_filtered)}')
                return custom_cookies_filtered
        elif exclusion != 'custom':
            generic_cookies = []
            try:
                cookie_check = self.cookie_jar
            except ValueError:
                print(f'No cookies found.')
                cookie_check = None
            inclusion_list = ['PHPSESSID', 'session_start', 'start_session', 'cookie', 'setCookie']
            for cookie in cookie_check:
                if cookie in inclusion_list:
                    generic_cookies.append(cookie)
            generic_cookies_size = len(generic_cookies)
            return generic_cookies_size
    
    def plugin_toggler(self, plugin, excluded_plugins):
        if plugin not in excluded_plugins:
            print(f'Toggling {plugin}.')
            cmd = f'wp plugin toggle {plugin} --skip-themes --skip-plugins'
            stdout, stderr = run_command(cmd)
            try:
                if self.warning_re.search(stderr) or stdout is None:
                    print(f'{color.BOLD}There\'s an error after toggling {plugin}. This might be a required plugin by an add-on, you will need to check manually.{color.END}')
                    logger.debug(f'WP error: {stderr}.')
            except Exception:
                pass
def after_checker(monster, curl_url, plugin, culprit_plugin, generic_cookies_size_start, toggled_plugins, timeout, redirects):
    monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
    generic_cookies_size_after = monster.cookie_monster('generic')
    if generic_cookies_size_start > generic_cookies_size_after and generic_cookies_size_after >= 1:
        print(f'{color.BOLD}Number of cookies changed, adding {plugin} to the culprit list{color.END}')
        culprit_plugin.append(plugin)
    elif generic_cookies_size_start == generic_cookies_size_after:
        print(f'There was no change in cookie number: {", ".join(monster.cookie_jar)}. Moving to the next plugin.')
    elif generic_cookies_size_after == 0:
        print(f'{color.BOLD}Could not find cookies after disabling {plugin}.{color.END}')
        culprit_plugin.append(plugin)
        return True

def run_command(cmd):
    try:
        process = subprocess.run(cmd.split(), capture_output=True, text=True, check=True, encoding='utf-8')
        return process.stdout.strip(), process.stderr.strip()
    except subprocess.CalledProcessError as e:
       print(f'WP-CLI command failed with error:\n{e}')
       logger.debug(f'WP-CLI command failed with error:\n{e}')
       return None, 'None'
    
def file_searcher(plugins_info, excluded_plugins, directory, custom_cookies):
    try:
        custom_cookies_regex = '|'.join(custom_cookies)
        custom_cookies_search = re.compile(rf"({custom_cookies_regex})\w?\(?\)?;?")
    except TypeError:
        custom_cookies_regex = None
        logger.debug('Empty custom cookies, regex cannot be created.')

    generic_search = re.compile(r"\w?(PHPSESSID|session_start|start_session|$cookie|setCookie)\w?\(?\)?;?", re.IGNORECASE)
    for item in plugins_info:
        if item['name'] not in excluded_plugins:
            if item['type'] == 'plugin':
                directory_to_check = f'{directory}/wp-content/plugins/{item["name"]}'
            else:
                directory_to_check = f'{directory}/wp-content/themes/{item["name"]}'
            for root, dirnames, filenames in os.walk(directory_to_check):
                for php_file in filenames:
                    if php_file.endswith('.php'):
                        try:
                            with open(f'{root}/{php_file}', 'r') as file:
                                content = file.read()
                                try:
                                    if custom_cookies:
                                        matches_custom = custom_cookies_search.search(content)
                                        if matches_custom:
                                            if item['flagged_generic'] == True:
                                                item['flagged_generic'] = False
                                                item['flagged_custom'] = True
                                                break
                                            elif item['flagged_custom'] == False:
                                                item['flagged_custom'] = True
                                                break
                                except Exception:
                                    pass
                                matches_generic = generic_search.search(content)
                                if matches_generic:
                                    if item['flagged_generic'] == False and item['flagged_custom'] == False:
                                        item['flagged_generic'] = True
                                        break
                        except Exception:
                            break
    filtered_data = [item for item in plugins_info if item['flagged_custom'] or item['flagged_generic']]
    flagged_custom = []
    flagged_generic = []
    for plugin in filtered_data:
        if plugin['flagged_custom']:
            flagged_custom.append(plugin['name'])
        elif plugin['flagged_generic']:
            flagged_generic.append(plugin['name'])
    return filtered_data, flagged_custom, flagged_generic

def excluded_print(skip_plugins, excluded_list):
    if skip_plugins:
        skip_plugins_list = skip_plugins.split(',')
        print(f'Plugins to skip: {", ".join(skip_plugins_list)}')
    
    print(f'Plugins excluded by default: {", ".join(excluded_list)}')
    if not skip_plugins: # - Check if user wants to exclude anything else.
        pass
    else:
        for plugin in skip_plugins_list:
            excluded_list.append(plugin)
    return excluded_list
