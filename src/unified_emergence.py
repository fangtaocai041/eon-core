"""Re-export from infrastructure — canonical source."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'infrastructure'))
from unified_emergence import *
