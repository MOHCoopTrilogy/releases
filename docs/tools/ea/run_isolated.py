#!/usr/bin/env python3
"""Run a tool from this folder under `python -I` (no cwd / env on sys.path) while still seeing the
user's site-packages (numpy for flvis). usage: python -I run_isolated.py <tool.py> args..."""
import os, runpy, site, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [here]
sys.path.append(site.getusersitepackages())
tool = os.path.join(here, os.path.basename(sys.argv[1]))
sys.argv = [tool] + sys.argv[2:]
runpy.run_path(tool, run_name="__main__")
