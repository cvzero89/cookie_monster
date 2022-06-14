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
## - Getting domain name and paths for later use.
directory = os.getcwd()
directory_is = directory.split('/')
directory_is_filtered = list(filter(None, directory_is))

if len(directory_is_filtered) <= 2:
	print(f'This script cannot be run on the user directory or lower. Current path is {directory}\nBye!')
	exit()
elif len(directory_is_filtered) > 3:
	move_backwards = ''
	directory_size = len(directory_is_filtered) - 3
	for size in range(directory_size):
		move_backwards = move_backwards + '../'
	print(f'Moving to directory root')
	os.chdir(move_backwards)
	directory = os.getcwd()

import requests

url_is = directory_is[3]
curl_url = f'http://{url_is}'
## - Function to cURL to the site, used multiple times on the script.
def curling_not_the_sport(curl_url):
	try:
		curl_site = requests.get(curl_url, timeout=30, allow_redirects=False)
		curl_site.raise_for_status()
		headers = curl_site.headers
		return headers
	except requests.exceptions.HTTPError as errh:
	    print (f'HTTP error, cURL to {url_is} failed. Error below \n  {errh}')
	    exit()
	except requests.exceptions.ConnectionError as errc:
	    print (f'Error connecting, cURL to {url_is} failed. Error below \n  {errc}')
	    exit()
	except requests.exceptions.Timeout as errt:
	    print (f'Timeout Error, cURL to {url_is} failed. Error below \n  {errt}')
	    exit()
	except requests.exceptions.RequestException as err:
	    print (f'Oops: Something unidentified happened, cURL to {url_is} failed. Error below \n  {err}')
	    exit()
headers = curling_not_the_sport(curl_url)

## - Investigating the headers info:
try:
	headers['Cache-Control']
	print('Cache-Control found. You might need to check the .htaccess.')
except KeyError:
	print('Cache-Control is not found.')

try:
	headers['X-Powered-By']
except KeyError:
	print('Not a DreamPress server.')
try:
	headers['Set-Cookie']
except KeyError:
	print('No cookies found. Why are you running this?\nVarnish should run OK, bye!')
	exit()	


## - Finding only custom cookies and filtering them if set to exclusion = 'custom', otherwise it will check the # of the cookies, used for sites setting more than 1 cookie at the time.
exclusion = 'custom'
def cookie_monster(headers, exclusion='custom'):
	if exclusion == 'custom':
		custom_cookies = []
		custom_cookies_filtered = []

		cookie_check = headers['Set-Cookie'].split()
		finding = re.findall(r'\w*?=', str(cookie_check))
		exclusion_list = ['path=', 'path=/;', 'expires=', 'Age=', 'PHPSESSID=', 'SameSite=', 'samesite=', 'secure', 'httponly', 'domain=']
		for element in finding:
			if element not in exclusion_list:
				if re.match(r'[a-zA-Z0-9]*=', element):
					custom_cookies.append(re.sub('=', '', element))
					finding.remove(element)
			if element not in exclusion_list:
				## - Regex to match and replace random added strings if any:
				pattern = r'_?[a-zA-Z0-9]*='
				if element not in custom_cookies:
					custom_cookies.append(re.sub(pattern, '', element))
		if not custom_cookies:
			pass
		else:
			custom_cookies_filtered = list(filter(None, custom_cookies)) ## - If any item is blank it will be stripped.
			print(f'Found custom cookie(s): {", ".join(custom_cookies_filtered)}.')
			return custom_cookies_filtered

	elif exclusion != 'custom':
		generic_cookies = []
		cookie_check = headers['Set-Cookie'].split()
		finding = re.findall(r'\w*?=', str(cookie_check))
		exclusion_list = ['path=', 'path=/;', 'expires=', 'Age=', 'SameSite=', 'samesite=', 'secure', 'httponly', 'domain=']
		for element in finding:
			if element not in exclusion_list:
				if re.match(r'[a-zA-Z0-9]*=', element):
					generic_cookies.append(re.sub('=', '', element))
					finding.remove(element)
			if element not in exclusion_list:
				## - Regex to match and replace random added strings if any:
				pattern = r'_?[a-zA-Z0-9]*='
				if element not in generic_cookies:
					generic_cookies.append(re.sub(pattern, '', element))
		generic_cookies_size = len(generic_cookies)
		return generic_cookies_size


try:
	custom_cookies_filtered = cookie_monster(headers)
except KeyError:
	pass

## - Regex for generic named cookies, it will append some common characters at the begginning and end.
import subprocess
generic_cookies_regex = re.compile(r"\w?(PHPSESSID|session_start|start_session|$cookie|setCookie)\w?\(?\)?;?", re.IGNORECASE)

## - Creating the Regex if 'custom' cookies are found:
try:
	custom_cookies_regex = '|'.join(custom_cookies_filtered)
	custom_cookies_search = re.compile(rf"({custom_cookies_regex})\w?\(?\)?;?")
except Exception:
	pass

print('Getting active plugin list.\n')

get_active_plugins = subprocess.Popen(['wp', 'plugin', 'list', '--status=active', '--field=name', '--skip-themes', '--skip-plugins'], stdout=subprocess.PIPE)
active_plugins = get_active_plugins.communicate()[0].decode('utf-8').strip()
get_active_plugins.stdout.close()

## - Not needed to check ALL plugins:
excluded_plugins = ['varnish-http-purge', 'dreamhost-panel-login'] ## - This list can be expanded.
flagged_plugins = []
flagged_plugins_custom = []

print('Searching cookies on plugins and themes:')

## - Looking for only PHP files on active plugins. First it will flag anything on 'custom' cookies if there are any, it will then proceed with generic:
for plugin in active_plugins.split():
	if plugin not in excluded_plugins:
		directory_plugin = f'{directory}/wp-content/plugins/{plugin}'
		for root, dirnames, filenames in os.walk(directory_plugin):
			for php_file in filenames:
				if php_file.endswith('.php'):
					try:
						with open(f'{root}/{php_file}', 'r') as file:
							content = file.read()
							try:
								if custom_cookies_filtered:
									if custom_cookies_search.search(content):
										if plugin not in flagged_plugins_custom: 
											if plugin not in flagged_plugins:
												flagged_plugins_custom.append(plugin)
									else:
										pass
								else:
									pass
							except Exception:
								pass	
							if generic_cookies_regex.search(content):

								if plugin not in flagged_plugins:
									if plugin not in flagged_plugins_custom:
										flagged_plugins.append(plugin)	
							else:
								pass
					except Exception:
						break
				else:
					pass

## - Getting active theme and parent (if any):

get_active_theme = subprocess.Popen(['wp', 'theme', 'list', '--status=active, parent', '--field=name', '--skip-themes', '--skip-plugins'], stdout=subprocess.PIPE)
active_theme = get_active_theme.communicate()[0].decode('utf-8').strip()
get_active_theme.stdout.close()

## - Searching PHP files on active theme and parent (if any):

flagged_theme = []
for theme in active_theme.split():
	directory_theme = f'{directory}/wp-content/themes/{theme}'
	for root, dirnames, filenames in os.walk(directory_theme):
		for php_file in filenames:
			if php_file.endswith('.php'):
				try:
					with open(f'{root}/{php_file}', 'r') as file:
						content = file.read()
						try:
							if custom_cookies_filtered:
								if custom_cookies_search.search(content):
									if theme not in flagged_theme: 
										flagged_theme.append(theme)
								else:
									pass
							else:
								pass
						except Exception:
							pass	
						if generic_cookies_regex.search(content):
							if theme not in flagged_theme:
									flagged_theme.append(theme)	
						else:
							pass
				except Exception:
					break
			else:
				pass

## - Based on the PHP results it will show only what we need:

if flagged_plugins and flagged_plugins_custom and flagged_theme:
	print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_plugins)} - {", ".join(flagged_plugins_custom)} - and theme: {", ".join(flagged_theme)}{color.END}')	
elif flagged_plugins and flagged_plugins_custom and not flagged_theme:
	print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_plugins)} - {", ".join(flagged_plugins_custom)}{color.END}')
elif flagged_plugins and not flagged_plugins_custom and flagged_theme:
	print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_plugins)} - - and theme: {", ".join(flagged_theme)}{color.END}')
elif flagged_plugins and not flagged_plugins_custom and not flagged_theme:
	print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_plugins)}{color.END}')

## - Toggle function, will exclude some plugins that might have add-ons and are not know for conflicting with Varnish:

warning_re = re.compile(r'\w?(Error|Warning:)\w?\(?\)?;?', re.IGNORECASE)
toggled_plugins = []
def plugin_toggler(plugin):
	exclude_toggle = ['woocommerce', 'elementor', 'jetpack', 'wp-mail-smtp', 'varnish-http-purge', 'dreamhost-panel-login']
	if plugin not in exclude_toggle:
		print(f'Toggling {plugin}.')
		toggle_plugin = subprocess.Popen(['wp', 'plugin', 'toggle', plugin, '--skip-themes', '--skip-plugins'], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
		try:
			toggle_message = toggle_plugin.communicate()[1].decode("utf-8").strip()
			if warning_re.search(toggle_message):
				print(f'{color.BOLD}There\'s an error after toggling {plugin}. This might be a required plugin by an add-on, you will need to check manually.{color.END}')
			toggle_plugin.stdout.close()
		except Exception:
			pass
	else:
		pass

culprit_plugin = []

## - Checking headers, # of cookies and re-enabling all plugins if Varnish responds with a HIT:

def after_checker(curl_url, plugin, exclusion='generic'):
	headers = curling_not_the_sport(curl_url)
	try:
		generic_cookies_size_after = cookie_monster(headers, exclusion='generic')
		if generic_cookies_size_start > generic_cookies_size_after:
			print(f'{color.BOLD}Number of cookies changed, adding {plugin} to the culprit list{color.END}')
			culprit_plugin.append(plugin)
		elif generic_cookies_size_start == generic_cookies_size_after:
			print(f"There are still cookies: {headers['Set-Cookie']}. Moving to the next plugin.")
	except KeyError:
		print(f'{color.BOLD}Could not find cookies after disabling {plugin}. Varnish reports X-Cacheable: {headers["X-Cacheable"]}{color.END}')
		culprit_plugin.append(plugin)
		print('Enabling plugins after checks.')
		for plugin in toggled_plugins:
			plugin_toggler(plugin)

		culprit_plugin_string = ', '.join(culprit_plugin)
		print(f'{color.BOLD}Plugin(s) bypassing cache: {culprit_plugin_string}.{color.END}')
		exit()

if flagged_plugins_custom:
	print('Plugins with custom cookies will be toggled, we\'ve already identified that they conflict with Varnish')
	for plugin in flagged_plugins_custom:
		try:
			generic_cookies_size_start = cookie_monster(headers, exclusion='generic')
		except KeyError:
			pass
		plugin_toggler(plugin)
		toggled_plugins.append(plugin)
		after_checker(curl_url, plugin, exclusion='generic')	
else:
	pass


for plugin in flagged_plugins:
	try:
		generic_cookies_size_start = cookie_monster(headers, exclusion='generic')
	except KeyError:
		pass
	plugin_toggler(plugin)
	toggled_plugins.append(plugin)
	after_checker(curl_url, plugin, exclusion='generic')

if flagged_theme:
	import time
	print('\nSwitching to a default theme:')
	get_active_theme = subprocess.Popen(['wp', 'theme', 'list', '--status=active', '--field=name', '--skip-themes', '--skip-plugins'], stdout=subprocess.PIPE)
	active_theme = get_active_theme.communicate()[0].decode('utf-8').strip()
	time.sleep(2)
	## Making sure default theme is installed:
	install_theme = subprocess.Popen(['wp', 'theme', 'install', 'twentytwentytwo', '--skip-themes', '--skip-plugins'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	time.sleep(2)
	change_theme = subprocess.Popen(['wp', 'theme', 'activate', 'twentytwentytwo', '--skip-themes', '--skip-plugins'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	time.sleep(2)
	headers = curling_not_the_sport(curl_url)
	try:
		print(f'There are still cookies: {headers["Set-Cookie"]}. Reactivating the theme.')
		change_theme = subprocess.Popen(['wp', 'theme', 'activate', active_theme, '--skip-themes', '--skip-plugins'], stdout=subprocess.DEVNULL)
	except KeyError:
		print(f'{color.BOLD}Could not find cookies after setting a default theme. Varnish reports X-Cacheable: {headers["X-Cacheable"]}{color.END}')
		culprit_plugin.append(active_theme)
		change_theme = subprocess.Popen(['wp', 'theme', 'activate', active_theme, '--skip-themes', '--skip-plugins'], stdout=subprocess.DEVNULL)
	get_active_theme.stdout.close()
else:
	pass

print('\nRe-enabling all plugins after checks.')

for plugin in toggled_plugins:
	plugin_toggler(plugin)

if not culprit_plugin:
	print(f'{color.BOLD}Could not find anything. Have you checked must-use plugins?{color.END}')
else:
	culprit_plugin_string = ', '.join(culprit_plugin)
	print(f'{color.BOLD}Plugin(s) bypassing cache: {culprit_plugin_string}.{color.END}')

