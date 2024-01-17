"""
A package containing classes and functions to handle molecular topologies.

The topology package contains the following submodules:
    
        - residue
        - selection
        - topology
        
The topology package contains the following classes:
        
        - Residue
        - QMResidue
        - Selection
        - Topology
                
The topology package contains the following type hints:

        - SelectionCompatible
        - Residues
                
The topology package contains the following exceptions:
    
        - ResidueError
"""

from .exceptions import TopologyError

from .selection import Selection, SelectionCompatible
from .topology import Topology
# TODO: partially circular --- from .shakeTopology import ShakeTopologyGenerator
