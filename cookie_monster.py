print("""              .---. .---. 
             :     : o   :    me want cookie!
         _..-:   o :     :-.._    /
     .-''  '  `---' `---' "   ``-.    
   .'   "   '  "  .    "  . '  "  `.  
  :   '.---.,,.,...,.,.,.,..---.  ' ;
  `. " `.                     .' " .'
   `.  '`.                   .' ' .'
    `.    `-._           _.-' "  .'  .----.
      `. "    '"--...--"'  . ' .'  .'  o   `.
      .'`-._'    " .     " _.-'`. :       o  :
    .'      ```--.....--'''    ' `:_ o       :
  .'    "     '         "     "   ; `.;";";";'
 ;         '       "       '     . ; .' ; ; ;
;     '         '       '   "    .'      .-'
'  "     "   '      "           "    _.-'""")

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

import os
import re
import subprocess
import requests
import argparse
import sys

class Assets():
    def __init__(self, type, status, flagged, culprit=False):
        self.type = type
        self.status = status
        self.flagged = flagged
        self.culprit = culprit
    
    def file_searcher(self):
        ...

class Site():
    def __init__(self, siteurl, plugins, theme):
        self.siteurl = siteurl
        self.plugins = plugins
        self.theme = theme
    
    def get_siteurl(self):
        ...

def folder_check(directory_is_filtered):

   if len(directory_is_filtered) <= 2:
      print(f'This script cannot be run on the user directory or lower. Current path is {directory}\nBye!')
      exit()
   elif len(directory_is_filtered) > 3:
      move_backwards = ''
      directory_size = len(directory_is_filtered) - 3
      for size in range(directory_size):
         move_backwards = move_backwards + '../'
#      print(f'Moving to directory root')
      os.chdir(move_backwards)
      directory = os.getcwd()
      return directory

warning_re = re.compile(r'\w?(Error|Warning:)\w?\(?\)?;?', re.IGNORECASE)

def run_command(cmd):
    try:
        process = subprocess.run(cmd.split(), capture_output=True, text=True, check=True, encoding='utf-8')
        return process.stdout.strip(), process.stderr.strip()
    except subprocess.CalledProcessError as e:
       print(f'WP-CLI command failed with error:\n{e}')
       return None, 'None'

def get_url(warning_re, directory_is, url_mod):
    cmd = 'wp option get siteurl --skip-themes --skip-plugins'
    stdout, stderr = run_command(cmd)
    if warning_re.search(stderr) or stdout is None:
        print('SiteURL CLI failed, falling back to getting the domain name based on the domain directory')
        curl_url = f'https://{directory_is[3]}'
    else:
        curl_url = stdout
    if url_mod:
        if url_mod.startswith('/'):
            url_mod = url_mod
        else:
            url_mod = f'/{url_mod}'
        curl_url = curl_url + url_mod
        return curl_url
    else:
        return curl_url
    
## - To allow it to fail gracefully. Any plugin that causes a 4xx/5xx will trigger the request Exception and activate anything that had been toggled.
def go_back(toggled_plugins):
	if toggled_plugins:
		print(f'cURL failed after plugins had been toggled, Re-activating. \nYou can use the flag --skip_plugins to skip this (Run python3 cookie_monster.py --h for more info).')
		for plugin in toggled_plugins:
			plugin_toggler(plugin)

## - Function to cURL to the site, used multiple times on the script.
def curling_not_the_sport(curl_url, toggled_plugins):
   try:
      curl_site = requests.get(curl_url, timeout=30, allow_redirects=False)
      curl_site.raise_for_status()
      cookies = curl_site.cookies
      headers = curl_site.headers
      cookie_jar = cookies.get_dict().keys()
      return headers, cookie_jar
   except requests.exceptions.HTTPError as errh:
       print (f'HTTP error, cURL to {curl_url} failed. Error below \n  {errh}')
       go_back(toggled_plugins)
       exit()
   except requests.exceptions.ConnectionError as errc:
       print (f'Error connecting, cURL to {curl_url} failed. Error below \n  {errc}')
       go_back(toggled_plugins)
       exit()
   except requests.exceptions.Timeout as errt:
       print (f'Timeout Error, cURL to {curl_url} failed. Error below \n  {errt}')
       go_back(toggled_plugins)
       exit()
   except requests.exceptions.RequestException as err:
       print (f'Oops: Something unidentified happened, cURL to {curl_url} failed. Error below \n  {err}')
       go_back(toggled_plugins)
       exit()

## - Finding only custom cookies and filtering them if set to exclusion = 'custom', otherwise it will check the # of the cookies, used for sites setting more than 1 cookie at the time.
def cookie_monster(cookie_jar, exclusion='custom'):
    if exclusion == 'custom':
        custom_cookies = []
        try:
            cookie_check = cookie_jar
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
            cookie_check = cookie_jar
        except ValueError:
            print(f'No cookies found.')
            cookie_check = None
        inclusion_list = ['PHPSESSID', 'session_start', 'start_session', 'cookie', 'setCookie']
        for cookie in cookie_check:
            if cookie in inclusion_list:
                generic_cookies.append(cookie)
        generic_cookies_size = len(generic_cookies)
        return generic_cookies_size
   

def active_plugins_and_themes(mode):
    if mode == 'plugins':
        cmd = 'wp plugin list --status=active --field=name --skip-themes --skip-plugins'
    else:
        cmd = 'wp theme list --status=active,parent --field=name --skip-themes --skip-plugins'
    stdout, stderr  = run_command(cmd)
    if warning_re.search(stderr) or stdout is None:
        print(f'Active plugins/themes cannot be listed.')
        sys.exit()
    else:
        return stdout

def file_searcher(active_plugins_names, excluded_plugins, directory, custom_cookies, mode, active_theme=None):
    flagged_generic = []
    flagged_custom = []
    try:
        custom_cookies_regex = '|'.join(custom_cookies)
        custom_cookies_search = re.compile(rf"({custom_cookies_regex})\w?\(?\)?;?")
    except TypeError:
        custom_cookies_regex = None
    generic_search = re.compile(r"\w?(PHPSESSID|session_start|start_session|$cookie|setCookie)\w?\(?\)?;?", re.IGNORECASE)
    if mode == 'plugins':
        list_to_check = active_plugins_names.split()
    else:
        list_to_check = active_theme.split()
    for item in list_to_check:
        if item not in excluded_plugins:
            if mode == 'plugins':
                directory_to_check = f'{directory}/wp-content/plugins/{item}'
            else:
                directory_to_check = f'{directory}/wp-content/themes/{item}'
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
    #                                        print(f'{item} matches at {matches_custom.group()}')
                                            if item in flagged_generic:
                                                flagged_generic.remove(item)
                                                flagged_custom.append(item)
                                                list_to_check.remove(item)
                                            if item not in flagged_custom and item not in flagged_generic:
                                                flagged_custom.append(item)
                                                list_to_check.remove(item)
                                except Exception:
                                    pass
                                matches_generic = generic_search.search(content)
                                if matches_generic:
    #                                print(f'{item} matches at {matches_generic.group()}')
                                    if item not in flagged_generic and item not in flagged_custom:
                                        flagged_generic.append(item)
                        except Exception:
                            break
    return flagged_generic, flagged_custom

## - Toggle function, will exclude some plugins that might have add-ons and are not know for conflicting with Varnish/NGINX:
def plugin_toggler(plugin, excluded_plugins, warning_re):
    if plugin not in excluded_plugins:
        print(f'Toggling {plugin}.')
        cmd = f'wp plugin toggle {plugin} --skip-themes --skip-plugins'
        stdout, stderr = run_command(cmd)
        try:
            if warning_re.search(stderr) or stdout is None:
                print(f'{color.BOLD}There\'s an error after toggling {plugin}. This might be a required plugin by an add-on, you will need to check manually.{color.END}')
        except Exception:
            pass
    

## - Checking headers, # of cookies and re-enabling all plugins if Nginx responds with a HIT:

def after_checker(curl_url, plugin, culprit_plugin, generic_cookies_size_start, toggled_plugins):
    headers, cookie_jar = curling_not_the_sport(curl_url, toggled_plugins)
    generic_cookies_size_after = cookie_monster(cookie_jar, exclusion='generic')
    if generic_cookies_size_start > generic_cookies_size_after and generic_cookies_size_after >= 1:
        print(f'{color.BOLD}Number of cookies changed, adding {plugin} to the culprit list{color.END}')
        culprit_plugin.append(plugin)
    elif generic_cookies_size_start == generic_cookies_size_after:
        print(f'There was no change in cookie number: {", ".join(cookie_jar)}. Moving to the next plugin.')
    elif generic_cookies_size_after == 0:
        print(f'{color.BOLD}Could not find cookies after disabling {plugin}.{color.END}')
        culprit_plugin.append(plugin)
        return True


def main():
    ## - Skipping plugins? Will need to be added as plugin1,plugin2 - no space with comma.
    parser =  argparse.ArgumentParser(description='Checking cookies that bypass Varnish/NGINX')
    parser.add_argument('--skip_plugins', help='Adding plugins to exclude. Ex. python3 cookie_monster.py --skip-plugins plugin1,plugin2')
    parser.add_argument('--url_mod', help='Specify the URL to cURL if anything other than the homepage is required. Ex. python3 cookie_monster.py --url_mod /new/url.')
    args = parser.parse_args()
    skip_plugins = args.skip_plugins
    url_mod = args.url_mod
    toggled_plugins = []
    ## - Getting domain name and paths for later use.
    directory = os.getcwd()
    directory_is = directory.split('/')
    directory_is_filtered = list(filter(None, directory_is))
    directory = folder_check(directory_is_filtered)
    curl_url = get_url(warning_re, directory_is, url_mod)
    print(f'Inspecting cookies at: {curl_url}')
    headers, cookie_jar = curling_not_the_sport(curl_url, toggled_plugins)

    ## - Investigating the headers info:
    try:
        headers['Cache-Control']
        print('Cache-Control found. You might need to check the .htaccess.')
    except KeyError:
        print('Cache-Control is not found.')
    try:
        headers['Set-Cookie']
        if cookie_jar:
           cookies = ', '.join(cookie_jar)
           print(f'Cookies found: {cookies}')
    except KeyError:
        print('No cookies found. Why are you running this?\nNginx should cache this site, bye!')
        sys.exit() 

    if skip_plugins:
        skip_plugins_list = skip_plugins.split(',')
        print(f'Plugins to skip: {", ".join(skip_plugins_list)}')

    ## - Not needed to check ALL plugins:
    excluded_plugins = ['woocommerce', 'elementor', 'nginx-helper', 'dreamhost-panel-login', 'redis-cache'] ## - This list can be expanded.
    print(f'Plugins excluded by default: {", ".join(excluded_plugins)}')
    if not skip_plugins: # - Check if user wants to exclude anything else.
        pass
    else:
        for plugin in skip_plugins_list:
            excluded_plugins.append(plugin)

    custom_cookies = cookie_monster(cookie_jar, exclusion='custom')
#    generic_cookies_size = cookie_monster(cookie_jar, exclusion='generic')
    active_plugins_names = active_plugins_and_themes('plugins')
    flagged_plugins, flagged_plugins_custom = file_searcher(active_plugins_names, excluded_plugins, directory, custom_cookies, 'plugins')
    active_theme = active_plugins_and_themes('themes')
    flagged_theme = file_searcher(active_plugins_names, excluded_plugins, directory, custom_cookies, 'theme', active_theme)

    ## - Based on the PHP results it will show only what we need:
    flagged_both = flagged_plugins + flagged_plugins_custom
    if flagged_both:
        print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_both)}{color.END}')
    if flagged_theme is not None and len(flagged_theme[0]) >0:
        print(f'{color.BOLD}Flagged theme: {", ".join(flagged_theme[0])}{color.END}.')
        print(flagged_theme)

    toggled_plugins = []
    culprit_plugin = []
    # - Toggling plugins with custom cookies first.
    if flagged_plugins_custom:
        print('Plugins with custom cookies will be toggled, we\'ve already identified that they conflict with Varnish/NGINX')
        for plugin in flagged_plugins_custom:
            plugin_toggler(plugin, excluded_plugins, warning_re)
            toggled_plugins.append(plugin)
            culprit_plugin.append(plugin)

    # - Toggling plugins with generic cookies second.
    headers, cookie_jar = curling_not_the_sport(curl_url, toggled_plugins)
    generic_cookies_size = cookie_monster(cookie_jar, exclusion='generic')
    if flagged_plugins and generic_cookies_size != 0:
        print('Checking for the generic cookies.')
        for plugin in flagged_plugins:
            try:
                headers, cookie_jar = curling_not_the_sport(curl_url, toggled_plugins)
                generic_cookies_size_start = cookie_monster(cookie_jar, exclusion='generic')
            except KeyError:
                pass
            plugin_toggler(plugin, excluded_plugins, warning_re)
            toggled_plugins.append(plugin)
            if generic_cookies_size_start != 0:
                after_generic = after_checker(curl_url, plugin, culprit_plugin, generic_cookies_size_start, toggled_plugins)
                if after_generic == True:
                    break
    else:
        print('No generic cookies found!')


    ## - Last step, going back if nothing has been found.
    print('\nRe-enabling all plugins after checks.')

    for plugin in toggled_plugins:
        plugin_toggler(plugin, excluded_plugins, warning_re)

    if not culprit_plugin:
        print(f'{color.BOLD}Could not find anything. Have you checked must-use plugins?{color.END}')   
    else:
        print(f'{color.BOLD}Plugin(s) bypassing cache: {", ".join(culprit_plugin)}.{color.END}')

if __name__ == '__main__':
   main()
