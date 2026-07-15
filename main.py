"""OpenCode Helper — One-click OpenCode installer and configurator."""
import sys
import os

# Ensure src/ is on path for both source and frozen runs
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if os.path.isdir(_src):
    sys.path.insert(0, _src)

# In PyInstaller --onefile, modules are in the frozen archive;
# PyInstaller resolves them via its own FrozenImporter, bypassing sys.path.
# We pass --paths src so PyInstaller scans src/ during analysis.

from app import App
import tkinter as tk

def main():
    root = tk.Tk()
    app = App(root)
    app.run()

if __name__ == '__main__':
    main()
