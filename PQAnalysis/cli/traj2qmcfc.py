import argparse

from PQAnalysis.io.trajectoryWriter import TrajectoryWriter
from PQAnalysis.io.trajectoryReader import TrajectoryReader


def main():
    parser = argparse.ArgumentParser(
        description='Converts multiple trajectory files to a qmcfc trajectory.')
    parser.add_argument('trajectory_file', type=str, nargs='+',
                        help='The trajectory file(s) to be converted.')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='The output file. If not specified, the output is printed to stdout.')
    args = parser.parse_args()

    writer = TrajectoryWriter(filename=args.output, format="qmcfc")
    for filename in args.trajectory_file:
        reader = TrajectoryReader(filename)
        trajectory = reader.read()

        writer.write(trajectory)
