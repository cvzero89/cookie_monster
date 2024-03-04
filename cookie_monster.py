import re
import yaml
import argparse
import logging.config
import logging
from src.CookieDough import CookieMonster, color, Site, after_checker, run_command, file_searcher, excluded_print
import sys
import os

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
 
     
def main():
    '''
    Config file to change the script execution.
    It includes changing the theme to use, the timeout on the curl and the plugins to exclude by default.
    '''
    script_path = os.path.abspath(os.path.dirname(__file__))
    os.chdir(script_path)
    with open(f'{script_path}/config.yml', 'r') as file:
            config = yaml.safe_load(file)
    excluded_list = config['excluded_list']
    config_theme = config['theme']
    timeout = config['curl']['timeout']
    redirects = config['curl']['follow_redirects']
    logger_config = config['logger']


    '''
    Initializing all of the script setup and needed variables.
    '''
    logging.config.dictConfig(logger_config)
    logger = logging.getLogger('cookieMonster')
    logger.info('Cookie check starting...')
    parser =  argparse.ArgumentParser(description='Checking cookies that bypass Varnish/NGINX')
    parser.add_argument('--skip_plugins', help='Adding plugins to exclude. Ex. python3 cookie_monster.py --skip-plugins plugin1,plugin2')
    parser.add_argument('--url_mod', help='Specify the URL to cURL if anything other than the homepage is required. Ex. python3 cookie_monster.py --url_mod /new/url.')
    args = parser.parse_args()
    skip_plugins = args.skip_plugins
    url_mod = args.url_mod
    warning_re = re.compile(r'\w?(Error|Warning:)\w?\(?\)?;?', re.IGNORECASE)

    '''
    Getting site details and creating a dictionary with the information.

    '''
    site = Site(warning_re)
    site.get_wordpress_info(url_mod)
    directory = site.folder_check()
    wordpress_info = site.wordpress_info
    logger.info(f'Site URL loaded as: {wordpress_info["site_url"]}')
    print(f'Inspecting cookies at: {wordpress_info["site_url"]}')
    curl_url = wordpress_info['site_url']
    plugins_info, themes_info = site.active_plugins_and_themes()
    monster = CookieMonster(warning_re)
    toggled_plugins = []
    culprit_plugin = []
   
    '''
    Inspect the headers early and exit if it is not needed to cURL the site.
    Only if it finds cookies the script will continue.
    '''
    monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
    try:
        monster.headers['Cache-Control']
        print(f'Cache-Control found. Review the headers: {monster.headers["Cache-Control"]}')
    except KeyError:
        print('Cache-Control is not found.')
    try:
        monster.headers['Set-Cookie']
        if monster.cookie_jar:
           cookies = ', '.join(monster.cookie_jar)
           print(f'Cookies found: {cookies}')
           logger.info(f'Cookies found at first cURL: {", ".join(monster.cookie_jar)}')
    except KeyError:
        print('No cookies found. Why are you running this?\nNginx should cache this site, bye!')
        logger.info(f'There were no cookies found: {monster.headers}')
        sys.exit() 
    custom_cookies = monster.cookie_monster('custom')
    
    '''
    Print excluded plugins, can be expanded via --skip_plugins and config.yml.
    Searching on all of the active plugins/theme files for info on the generic and custom cookies.
    Returns the raw dictionary and the names of the plugins/theme. The function removes any plugin that was not flagged to speed up the process moving forward.
    '''
    excluded_plugins = excluded_print(skip_plugins, excluded_list)
    plugins_info, flagged_custom, flagged_generic = file_searcher(plugins_info, excluded_plugins, directory, custom_cookies)
    themes_info, flagged_theme_custom, flagged_theme_generic = file_searcher(themes_info, excluded_plugins, directory, custom_cookies)
    if flagged_generic or flagged_custom:
        print(f'{color.BOLD}Flagged plugins: {", ".join(flagged_custom + flagged_generic)}{color.END}')
        logger.info(f'Flagged plugins: {plugins_info}')
    if flagged_theme_custom or flagged_theme_generic:
        active_theme = themes_info[0]['name']
        print(f'{color.BOLD}Flagged theme: {active_theme}{color.END}')
        logger.info(f'Flagged themes: {themes_info}')
    
    '''
    "Custom" cookies are flagged first since they are easier to find. The name of the cookie will be on the plugin/theme files and we can get rid of it easier.
    Plugins are immediately added to the culprit list.
    '''
    if flagged_custom:
        print('Plugins with custom cookies will be toggled, we\'ve already identified that they conflict with Varnish/NGINX')
        logger.info('Toggling plugins with custom cookies:')
        for plugin in flagged_custom:
            monster.plugin_toggler(plugin, excluded_plugins)
            logger.info(f'Toggled plugin: {plugin}')
            toggled_plugins.append(plugin)
            culprit_plugin.append(plugin)      

    '''
    After toggling the custom cookies we fire up a new cURL, if there are generic cookies and something was flagged plugins are toggled one by one.
    
    '''
    monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
    generic_cookies_size = monster.cookie_monster('generic')
    if flagged_generic and generic_cookies_size != 0:
        print('Checking for the generic cookies.')
        logger.info('Checking for the generic cookies.')
        for plugin in flagged_generic:
            try:
                monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
                generic_cookies_size_start = monster.cookie_monster(exclusion='generic')
                logger.info(f'Checking: {plugin} - # of cookies:{generic_cookies_size_start}')
            except KeyError:
                pass
            monster.plugin_toggler(plugin, excluded_plugins)
            logger.info(f'Toggled plugin: {plugin}')
            toggled_plugins.append(plugin)
            if generic_cookies_size_start != 0:
                after_generic = after_checker(monster, curl_url, plugin, culprit_plugin, generic_cookies_size_start, toggled_plugins, timeout, redirects)
                if after_generic == True:
                    break

    '''
    Lastly, if a theme was flagged it is checked for both type of cookies.
    Anecdotally, it feels like themes are not often a problem, which is why it is on the last part of the process.
    The theme to be installed is set on the config.yml, I often use the current default WordPress theme, eg. twentytwentyfour. 
    '''
    generic_cookies_size = monster.cookie_monster('generic')
    if flagged_theme_generic and generic_cookies_size != 0:
        monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
        generic_cookies_size_start = monster.cookie_monster('generic')
        logger.info('Checking for the generic cookies on the theme.')
        print('\nSwitching to a default theme:')
        run_command(f'wp theme install {config_theme} --skip-themes --skip-plugins')
        run_command(f'wp theme activate {config_theme} --skip-themes --skip-plugins')
        logger.info(f'Setting up {config_theme}.')
        monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
        generic_cookies_size_after = monster.cookie_monster('generic')
        if generic_cookies_size_start > generic_cookies_size_after and generic_cookies_size_after >= 1:
            print(f'{color.BOLD}Number of cookies changed, adding {active_theme} to the culprit list{color.END}')
            logger.info(f'# of cookies after theme change: {generic_cookies_size_after}.')
            culprit_plugin.append(active_theme)
            run_command(f'wp theme activate {active_theme}')
        elif generic_cookies_size_after == 0:
            print(f'{color.BOLD}Could not find cookies after disabling {active_theme}.{color.END}')
            logger.info(f'# of cookies after theme change: {generic_cookies_size_after}.')
            culprit_plugin.append(active_theme)
            run_command(f'wp theme activate {active_theme}')
    elif flagged_theme_custom:
        print('\nSwitching to a default theme:')
        run_command(f'wp theme install {config_theme} --skip-themes --skip-plugins')
        run_command(f'wp theme activate {config_theme} --skip-themes --skip-plugins')
        logger.info(f'Setting up {config_theme}.')
        monster.curling_not_the_sport(curl_url, toggled_plugins, timeout, redirects)
        if not monster.cookie_jar:
            culprit_plugin.append(active_theme)
            run_command(f'wp theme activate {active_theme}')
            print(f'{color.BOLD}Could not find cookies after disabling {active_theme}.{color.END}')
            logger.info(f'# of cookies after theme change: {generic_cookies_size_after}.')

    '''
    Last step, leave the site as we found it.
    '''
    print('\nRe-enabling all plugins after checks.')

    for plugin in toggled_plugins:
        monster.plugin_toggler(plugin, excluded_plugins)

    if not culprit_plugin:
        print(f'{color.BOLD}Could not find anything. Have you checked must-use plugins?{color.END}')   
    else:
        print(f'{color.BOLD}Plugin(s)/Theme bypassing cache: {", ".join(culprit_plugin)}.{color.END}')


if __name__ == '__main__':
   main()
