"""rpart.py for the iron-sight G43 (registers its lane-local sight row first): same arguments."""
import sys, os, runpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g43pose
g43pose.register()
sys.argv[0] = os.path.join(HERE, 'rpart.py')
runpy.run_path(sys.argv[0], run_name='__main__')
