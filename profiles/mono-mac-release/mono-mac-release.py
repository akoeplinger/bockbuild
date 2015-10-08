#!/usr/bin/python -B -u
import sys 
import traceback

sys.path.append('../..')

from MonoReleaseProfile import MonoReleaseProfile
from bockbuild.util.util import *

try:
	MonoReleaseProfile().build()
except Exception as e:
	exc_type, exc_value, exc_traceback = sys.exc_info()
	error ('Unhandled Exception: %s\n %s:%s @%s\n\t...%s\n\n' % (str(e),(t for t in traceback.extract_tb(exc_traceback)[-5:])))
