""" This module helps import from parent folder """
import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
sys.path.append('src')
