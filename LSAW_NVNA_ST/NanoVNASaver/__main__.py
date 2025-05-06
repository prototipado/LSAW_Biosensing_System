
import argparse
import logging
import sys

from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.About import VERSION, INFO
from NanoVNASaver.NanoVNASaverNEW import NanoVNASaver
from NanoVNASaver.Touchstone import Touchstone



def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Set loglevel to debug")
    parser.add_argument("-D", "--debug-file",
                        help="File to write debug logging output to")
    parser.add_argument("-f", "--file",
                        help="Touchstone file to load as sweep for off"
                        " device usage")
    parser.add_argument("-r", "--ref-file",
                        help="Touchstone file to load as reference for off"
                        " device usage")
    parser.add_argument("--version", action="version",
                        version=f"NanoVNASaver {VERSION}")
    args = parser.parse_args()

    console_log_level = logging.WARNING
    file_log_level = logging.DEBUG

    #print(INFO)

    if args.debug:
        console_log_level = logging.DEBUG

    logger = logging.getLogger("NanoVNASaver")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(console_log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if args.debug_file:
        fh = logging.FileHandler(args.debug_file)
        fh.setLevel(file_log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("Startup...")

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling,
                                        True)
    app = QtWidgets.QApplication(sys.argv)
    window = NanoVNASaver()
    window.show()

    if args.file:
        t = Touchstone(args.file)
        t.load()
        window.saveData(t.s11, t.s21, args.file)
        window.dataUpdated()
    if args.ref_file:
        t = Touchstone(args.ref_file)
        t.load()
        window.setReference(t.s11, t.s21, args.ref_file)
        window.dataUpdated()
    try:
        app.exec_()
    except BaseException as exc:
        logger.exception("%s", exc)
        raise exc


if __name__ == '__main__':
    main()
