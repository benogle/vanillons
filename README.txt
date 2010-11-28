===============================================================================
Vanillons
===============================================================================

Vanillons is a pylons app that can be used as the basis of other web
applications. It will provide as a scaffold for rapidly building apps. I am
tired of repeating myself!

http://iamzed.com/2009/05/07/a-primer-on-virtualenv/

Above this dir is a bin dir. It has an activate binary. You need to run it with
virtual env:

source bin/activate

Installation and Setup
======================

Install ``vanillons`` using easy_install::

    easy_install vanillons

Make a config file as follows::

    paster make-config vanillons config.ini

Tweak the config file as appropriate and then setup the application::

    paster setup-app config.ini

Then you are ready to go.
