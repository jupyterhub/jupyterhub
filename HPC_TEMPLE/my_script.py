""" Pyfiglet is the module that will convert regular strings in to ASCII art fonts
pyfiglet --list_fonts to chose fro the fonts
"""
import pyfiglet


class my_banner:
    def __init__(self, my_text):
        self.text = pyfiglet.print_figlet(f"{my_text}")

    def print_banner(self):
        print(f"{self.text}")
