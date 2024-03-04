# cookie_monster
If Varnish/Nginx is bypassed toggles plugin and checks header response searching for cookies. 

This tool is used when sites are using PHPSESSID|session_start|start_session|$cookie|setCookie (generic cookie) on the HTTP headers, it will:

-Check for cache-control. 

-Get a list of active plugins, flagging them if PHPSESSID|session_start|start_session|$cookie|setCookie is found.

-Toggle them one by one cURLing searching for cookies.

-If all cookies are gone and Varnish/Nginx can return a HIT, it will revert all disabled plugins back to active.

You should still know the “normal” process/logic to testing the cache, this is a tool to make that process faster.

## Usage:

-Get a database backup: wp db export ~/backup`date +"%m-%d-%Y-%T"`.sql (ALWAYS)

-Copy the repository: git clone https://github.com/cvzero89/cookie_monster.git

-Run: python3 cookie_monster/cookie_monster.py

or

-Run: python3 cookie_monster/cookie_monster.py --url_mod /test (Testing specific pages).

### Possible issues:

-The script disables a required plugin for an add-on and breaks. Ex. plugin_1 is required by plugin_2 to work, the script toggles plugin_1. You can exclude plugins using --skip_plugins flag or expanding the config.yml excluded_list with the proper syntax.
```
from:
['woocommerce', 'elementor', 'nginx-helper', 'dreamhost-panel-login', 'redis-cache']
to:
['woocommerce', 'elementor', 'nginx-helper', 'dreamhost-panel-login', 'redis-cache', 'added_plugin']
```

-Cookie Monster says there are no cookies but your cURL shows them. This is a problem with redirects (I think), some sites will show cookies on 301 redirects but not on the final hop, why? I have no idea. Try setting the follow_redirects parameter on the config.yml to False.
```
curl:
    timeout: 30
    follow_redirects: False
```

-The site takes longer than 1 minutes to load. Increase the timeout on the config.yml:
```
curl:
    timeout: 90
    follow_redirects: True
```

-Site is not public or behind HTTPauth.

-Python version is lower than 3.6 (Should not happen unless cx has a custom version).

-The plugin is must-use (there’s no easy way to toggle this, they would need to be removed from the mu-plugins folder).

## Examples:

```
username@server:~/domain.com$ python3 cookie_monster/cookie_monster.py
Cache-Control found. You might need to check the .htaccess.
Getting active plugin list.

Searching cookies on plugins and themes:
Flagged plugins: contact-form-7, opal-estate, js_composer, real-estate-listing-realtyna-wpl-pro, wpopal-core-features, pbrthemer, wp-real-estate, security-manager
Toggling contact-form-7.
There are still cookies: PHPSESSID=2b6ee6368bc3f7d23c5e51abdc5bb65d; path=/. Moving to the next plugin.
Toggling opal-estate.
There are still cookies: PHPSESSID=c5fe46fc1be146074c9c1bdfeec38563; path=/. Moving to the next plugin.
….cont…
Toggling security-manager.
Could not find cookies after disabling security-manager. Varnish reports X-Cacheable: YES:Forced
Enabling plugins after checks.
Toggling contact-form-7.
Toggling opal-estate.
Toggling js_composer.
Toggling real-estate-listing-realtyna-wpl-pro.
Toggling wpopal-core-features.
Toggling pbrthemer.
Toggling wp-real-estate.
Toggling security-manager.
Plugin(s) bypassing cache: security-manager.
```

“Custom/named” cookies are also considered and toggled first if they exist:

```
username@server:~/domain.com$ python3 cookie_monster/cookie_monster.py
Cache-Control is not found.
Found custom cookie(s): wpml_referer, _icl_current, _icl_current.
Getting active plugin list.

Searching cookies on plugins and themes:
Flagged plugins: contact-form-7, better-wp-security, wpforo, wp-inventory-manager, wordpress-seo - sitepress-multilingual-cms
Plugins with custom cookies will be toggled, we've already identified that they conflict with Varnish
Toggling sitepress-multilingual-cms.
Could not find cookies after disabling sitepress-multilingual-cms. Varnish reports X-Cacheable: YES:Forced
Enabling plugins after checks.
Toggling sitepress-multilingual-cms.
Plugin(s) bypassing cache: sitepress-multilingual-cms.
```

Any issues? Check the logs on the ./src folder. cookieCrumbs.log is informational, monster-debug.log will contain a more verbose log.
