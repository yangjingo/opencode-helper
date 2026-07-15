"""OpenCode Helper — One-click OpenCode installer and configurator."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import App
import tkinter as tk

def main():
    root = tk.Tk()
    app = App(root)
    app.run()

if __name__ == '__main__':
    main()
