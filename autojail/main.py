import argparse
import sys
import logging

from .extract import BoardInfoExtractor


class AutoJail:
    """Main Class for Autojail Application"""

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self._init_argument_parser()

    def _init_argument_parser(self):
        init_parser = self.parser.add_subparsers("init")
        extract_parser = self.parser.add_subparsers("extract")
        config_parser = self.parser.add_subparsers("config")
        explore_parser = self.parser.add_subparsers("explore")
        test_parser = self.parser.add_subparsers("test")

    def _parse_arguments(self, args):
        res = self.parser.parse_args(args)
        return res

    def init(self):
        """Initialize the autojail project"""
        pass

    def extract(self):
        """Extract the board data"""
        pass

    def config(self):
        """Create the jailhouse configuration"""
        pass

    def test(self):
        """Test the jailhouse configuration"""
        pass

    def explore(self):
        """Explore configuration alternatives for the jailhouse configuration"""
        pass

    def run(self, args):
        """Main entry point for the run configuration"""
        args = self._parse_arguments(args)


def main():
    autojail = AutoJail()
    autojail.run(sys.argv)
