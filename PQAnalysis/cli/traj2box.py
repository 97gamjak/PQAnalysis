"""
.. _cli.traj2box:

Command Line Tool for Converting Trajectory Files to Box Files
--------------------------------------------------------------

Converts multiple trajectory files to a box file.

Without the --vmd option the output is printed in a data file format.
The first column represents the step starting from 1, the second to fourth column
represent the box vectors a, b, c, the fifth to seventh column represent the box angles.

With the --vmd option the output is printed in a VMD file format. Meaning the output is
in xyz format with 8 particle entries representing the vertices of the box. The comment
line contains the information about the box dimensions a, b and c and the box angles.
"""

import argparse

from PQAnalysis.io import traj2box


def main():
    """
    Wrapper for the command line interface of traj2box.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trajectory_file', type=str, nargs='+',
                        help='The trajectory file(s) to be converted.')
    parser.add_argument('-v', '--vmd', action='store_true',
                        help='Output in VMD format.')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='The output file. If not specified, the output is printed to stdout.')
    args = parser.parse_args()

    traj2box(args.trajectory_file, args.vmd, args.output)
