#!/usr/bin/python3
"""Installed root-owned; accepts exactly one decimal epoch, no shell invocation."""
import sys,subprocess
if len(sys.argv)!=2 or not sys.argv[1].isdigit():sys.exit(2)
epoch=int(sys.argv[1])
if not 1735689600<=epoch<=4102444800:sys.exit(2)
subprocess.run(['/usr/bin/timedatectl','set-ntp','false'],check=True,timeout=3)
subprocess.run(['/usr/bin/date','-s','@'+str(epoch)],check=True,timeout=3)
