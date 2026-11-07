"""Session 02 logging to standard output."""
import logging
import sys


def setup_logging(level="INFO"):
    logging.basicConfig(level=level, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
