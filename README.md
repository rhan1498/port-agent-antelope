port-agent-antelope
===================

Port Agent For Antelope


Deployment
----------

These are suggested instructions using virtualenv. Virtualenv is not required,
it's just convenient.

The antelope python packages ship with, and require the use of, the antelope
python distribution. This normally lives somewhere like
`/opt/antelope/python2.7.2`. So create the virtual environment something like
this:

    virtualenv --python=/opt/antelope/5.3pre/bin/python ve

The antelope library bindings python packages don't live under the antelope
python interpreter, but rather somewhere like
`/opt/antelope/5.3pre/data/python`. Somehow you have to get that on your python
path. I like to add a `.pth` file to `ve/lib/python2.7/site-packages` which
points to the antelope python package dir. Something like:

	echo /opt/antelope/5.3pre/data/python > ve/lib/python2.7/site-packages/antelope5.3pre.pth

Before activating the virtual environment, source the Antelope environment set
up script. This sets up a bunch of important environment variables. E.g.:

    . /opt/antelope/5.3pre/setup.sh

Now activate the VE and install the other dependencies. Note that building
gevent from source requires cython; you might want to pip install that if it's
not already on your system.

    . ve/bin/activate
    pip install python-daemon
    pip install git+git://github.com/ooici/utilities.git#egg=Package
    pip install git+git://github.com/surfly/gevent.git@1.0rc2#egg=Package

Before running the port agent, you must set the `ANTELOPE_PYTHON_GILRELEASE`
variable in your environment. E.g.:

    export ANTELOPE_PYTHON_GILRELEASE=1

Now it should be possible to run the port agent.

    port_agent_antelope -c config_test -v -s

You can test it by sending it a command from another shell:

    port_agent_antelope -c config_test -v -s -C ping

You should see a reply packet with the port agent version number.

Dependencies
------------

These are the versions I developed against. They may not be critical.

gevent is the only dependency that I know requires a particular version, 1.0rc2
from github. Newer version may work as well. Older versions most likely will
not as they lack the threadpool module.

### core deps

gevent==1.0dev (really 1.0rc2)
greenlet==0.4.0
lockfile==0.9.1
python-daemon==1.6
antelope 5.3

### from ooi utilities

utilities==2013.05.01
PyYAML==3.10
graypy==0.2.8

