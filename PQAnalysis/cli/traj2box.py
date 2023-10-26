import numpy as np
import argparse
import sys

from PQAnalysis.traj.trajectory import read
from PQAnalysis.io.boxWriter import BoxWriter


def main():
    parser = argparse.ArgumentParser(
        description='Converts multiple trajectory files to a box file.')
    parser.add_argument('trajectory_file', type=str, nargs='+',
                        help='The trajectory file(s) to be converted.')
    parser.add_argument('-v', '--vmd', action='store_true',
                        help='Output in VMD format.')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='The output file. If not specified, the output is printed to stdout.')
    args = parser.parse_args()

    writer = BoxWriter(filename=args.output, format="vmd")
    for filename in args.trajectory_file:
        trajectory = read(filename)
        writer.write(trajectory)
