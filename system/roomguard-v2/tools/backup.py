#!/usr/bin/env python3
"""SQLite consistent online backup, including committed WAL content."""
import argparse,sqlite3
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
with sqlite3.connect(a.source) as src,sqlite3.connect(a.destination) as dst:src.backup(dst)
print('Backup complete:',a.destination)
