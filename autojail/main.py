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
        subparsers = self.parser.add_subparsers(help="Subcommands")
        init_parser = subparsers.add_parser("init")
        extract_parser = subparsers.add_parser("extract")
        config_parser = subparsers.add_parser("config")
        explore_parser = subparsers.add_parser("explore")
        test_parser = subparsers.add_parser("test")

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
