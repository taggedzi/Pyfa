import os
import sys

# Load variable overrides specific to distribution type
try:
    # Import all variables
    from configforced import *
    # Compose list of already defined variables and add them to forced list
    forcedvars = dir()
except ImportError:
    forcedvars = []

# Turns on debug mode
debug = False

# Version data
version = "1.0"
tag = "git"
expansionName = "Incursion"
expansionVersion = "1.1.0"

# You can adjust these paths to your needs

# The main pyfa directory which contains run.py
# Python 2.X uses ANSI by default, so we need to convert the character encoding
if not "pyfaPath" in forcedvars:
    pyfaPath = unicode(os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)),
                       sys.getfilesystemencoding())

# Where we store the saved fits etc, default is the current users home directory
if not "savePath" in forcedvars:
    savePath = unicode(os.path.expanduser(os.path.join("~", ".pyfa")),
                       sys.getfilesystemencoding())

# Static EVE Data from the staticdata repository, should be in the staticdata directory in our pyfa directory
staticPath = os.path.join(pyfaPath, "staticdata")

# The database where we store all the fits etc
saveDB = os.path.join(savePath, "saveddata.db")

# The database where the static EVE data from the datadump is kept.
# This is not the standard sqlite datadump but a modified version created by eos
# maintenance script
gameDB = os.path.join(staticPath, "eve.db")

## DON'T MODIFY ANYTHING BELOW ##
import eos.config

#Caching modifiers, disable all gamedata caching, its unneeded.
eos.config.gamedataCache = None
# saveddata db location modifier, shouldn't ever need to touch this
eos.config.saveddata_connectionstring = "sqlite:///" + saveDB + "?check_same_thread=False"
eos.config.gamedata_connectionstring = "sqlite:///" + gameDB + "?check_same_thread=False"
