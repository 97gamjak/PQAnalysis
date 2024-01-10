"""
A module containing the RDF class. The RDF class is used to calculate the radial distribution of a reference selection to a target selection. The radial distribution function (RDF) is a measure of the probability density of finding a particle at a distance r from another particle. 
"""

from __future__ import annotations

import numpy as np
import warnings

from beartype.typing import Tuple, List
from tqdm.auto import tqdm

import PQAnalysis.config as config

from .exceptions import RDFError, RDFWarning
from ...types import Np1DNumberArray, PositiveInt, PositiveReal
from ...core import distance, Cell
from ...traj import Trajectory
from ...traj.trajectory import check_trajectory_PBC, check_trajectory_vacuum
from ...topology import Selection, SelectionCompatible
from ...utils import timeit_in_class
from ...io import TrajectoryReader


class RDF:
    """
    A class for calculating the radial distribution of a reference selection to a target selection. The radial distribution function (RDF) is a measure of the probability density of finding a particle at a distance r from another particle. 
    """

    _use_full_atom_default = False
    _no_intra_molecular_default = False
    _r_min_default = 0.0

    def __init__(self,
                 traj: Trajectory | TrajectoryReader,
                 reference_species: SelectionCompatible,
                 target_species: SelectionCompatible,
                 use_full_atom_info: bool = False,
                 no_intra_molecular: bool = False,
                 n_bins: PositiveInt | None = None,
                 delta_r: PositiveReal | None = None,
                 r_max: PositiveReal | None = None,
                 r_min: PositiveReal | None = 0.0,
                 ):
        """
        Parameters
        ----------
        traj : Trajectory | TrajectoryReader
            The trajectory to analyze. If a TrajectoryReader is provided, the trajectory frame by frame via a frame_generator
        reference_species : SelectionCompatible
            The reference species of the RDF analysis.
        target_species : SelectionCompatible
            The target species of the RDF analysis.
        use_full_atom_info : bool, optional
            Whether to use the full atom information of the trajectory or not, by default None (False).
        no_intra_molecular : bool, optional
            Whether to exclude intra-molecular distances or not, by default None (False).
        n_bins : PositiveInt | None, optional
            number of bins, by default None
        delta_r : PositiveReal | None, optional
            delta r between bins, by default None
        r_max : PositiveReal | None, optional
            maximum radius from reference species of the RDF analysis, by default None
        r_min : PositiveReal, optional
            minimum (starting) radius from reference species of the RDF analysis, by default 0.0 (equals to None)

        Raises
        ------
        RDFError
            If the trajectory is not fully periodic or fully in vacuum. Meaning that some frames are in vacuum and others are periodic.
        RDFError
            If the trajectory is empty.
        RDFError
            If n_bins and delta_r are both not specified.
        RDFError
            If n_bins, delta_r and r_max are all specified. This would lead to ambiguous results.

        Notes
        -----
        To initialize the RDF analysis object at least one of the parameters n_bins or delta_r must be specified. If n_bins and delta_r are both specified, r_max is calculated from these parameters. If n_bins and r_max are both specified, delta_r is calculated from these parameters. If delta_r and r_max are both specified, n_bins is calculated from these parameters.

        It is not possible to specify all of n_bins, delta_r and r_max in the same RDF analysis as this would lead to ambiguous results.

        It is also possible to initialize a non-vacuum trajectory by only using n_bins or delta_r. In this case, r_max is calculated from the provided parameters and the box vectors of the trajectory. If the trajectory is in vacuum, an RDFError is raised as the maximum radius cannot be inferred from the box vectors.

        See Also
        --------
        :py:class:`~PQAnalysis.traj.trajectory.Trajectory`
        :py:class:`~PQAnalysis.topology.selection.Selection`
        """

        if use_full_atom_info is None:
            self.use_full_atom_info = self._use_full_atom_default
        else:
            self.use_full_atom_info = use_full_atom_info

        if no_intra_molecular is None:
            self.no_intra_molecular = self._no_intra_molecular_default
        else:
            self.no_intra_molecular = no_intra_molecular

        if r_min is None:
            self.r_min = self._r_min_default
        else:
            self.r_min = r_min

        self.reference_species = reference_species
        self.target_species = target_species

        self.reference_selection = Selection(reference_species)
        self.target_selection = Selection(target_species)

        self.cells = traj.cells

        if isinstance(traj, TrajectoryReader):
            self.frame_generator = traj.frame_generator()
            self.first_frame = next(self.frame_generator)
        elif len(traj) == 0:
            raise RDFError("Trajectory cannot be of length 0.")
        else:
            self.frame_generator = iter(traj)
            self.first_frame = next(self.frame_generator)

        self.topology = self.first_frame.topology

        self.setup_bins(n_bins=n_bins, delta_r=delta_r,
                        r_max=r_max, r_min=self.r_min)

        self.reference_indices = self.reference_selection.select(
            self.topology, self.use_full_atom_info)
        self.target_indices = self.target_selection.select(
            self.topology, self.use_full_atom_info)

    def setup_bins(self,
                   n_bins: PositiveInt | None = None,
                   delta_r: PositiveReal | None = None,
                   r_max: PositiveReal | None = None,
                   r_min: PositiveReal = 0.0
                   ):
        """
        Sets up the bins of the RDF analysis.

        This method is called by the __init__ method of the RDF class, but can also be called manually to re-initialize the bins of the RDF analysis. It sets up the bins of the RDF analysis based on the provided parameters. If n_bins and delta_r are both specified, r_max is calculated from these parameters. If n_bins and r_max are both specified, delta_r is calculated from these parameters. If delta_r and r_max are both specified, n_bins is calculated from these parameters.

        Parameters
        ----------
        n_bins : PositiveInt | None, optional
            number of bins, by default None
        delta_r : PositiveReal | None, optional
            delta r between bins, by default None
        r_max : PositiveReal | None, optional
            maximum radius of the RDF analysis, by default None
        r_min : PositiveReal, optional
            minimum (starting) radius of the RDF analysis, by default 0.0

        Raises
        ------
        RDFError
            If the trajectory is not fully periodic or fully in vacuum. Meaning that some frames are in vacuum and others are periodic.
        RDFError
            If n_bins and delta_r are both not specified.
        RDFError
            If n_bins, delta_r and r_max are all specified. This would lead to ambiguous results.
        """

        self.r_min = r_min

        # check if the trajectory is fully periodic or fully in vacuum
        if not check_trajectory_PBC(self.cells) and not check_trajectory_vacuum(self.cells):
            raise RDFError(
                "The provided trajectory is not fully periodic or in vacuum, meaning that some frames are in vacuum and others are periodic. This is not supported by the RDF analysis.")

        # check if n_bins and delta_r are both not specified
        if n_bins is None and delta_r is None:
            raise RDFError(
                "Either n_bins or delta_r must be specified.")

        # check if n_bins, delta_r and r_max are all specified
        elif n_bins is not None and delta_r is not None and r_max is not None:
            raise RDFError(
                "It is not possible to specify all of n_bins, delta_r and r_max in the same RDF analysis as this would lead to ambiguous results.")

        # set r_max based on the provided parameters n_bins and delta_r
        elif n_bins is not None and delta_r is not None:
            self.n_bins = n_bins
            self.delta_r = delta_r
            self.r_max = _calculate_r_max(n_bins, delta_r, r_min, self.cells)
            self.n_bins, self.r_max = _calculate_n_bins(
                delta_r, self.r_max, r_min)

        else:
            self.r_max = r_max

            if r_max is None:
                self.r_max = _infer_r_max(self.cells)

            self.r_max = _check_r_max(self.r_max, self.cells)

            if n_bins is None:
                self.delta_r = delta_r
                self.n_bins, self.r_max = _calculate_n_bins(
                    delta_r, self.r_max, r_min)

            else:
                self.n_bins = n_bins
                self.delta_r = (self.r_max - self.r_min) / self.n_bins

        self.bin_middle_points = _setup_bin_middle_points(
            self.n_bins, self.r_min, self.r_max, self.delta_r)
        self.bins = np.zeros(self.n_bins)

    @property
    def average_volume(self) -> PositiveReal:
        """PositiveReal: The average volume of the trajectory."""
        return np.mean([cell.volume for cell in self.cells])

    @timeit_in_class
    def run(self) -> Tuple[Np1DNumberArray, Np1DNumberArray, Np1DNumberArray, Np1DNumberArray, Np1DNumberArray]:
        """
        Runs the RDF analysis.

        This method runs the RDF analysis and returns the middle points of the bins of the RDF analysis, the normalized bins of the RDF analysis based on the spherical shell model, the integrated bins of the RDF analysis, the normalized bins of the RDF analysis based on the number of atoms in the system and the differential bins of the RDF analysis based on the spherical shell model.

        This method will display a progress bar by default. This can be disabled by setting with_progress_bar to False.

        Returns
        -------
        bin_middle_points : Np1DNumberArray
            The middle points of the bins of the RDF analysis.
        normalized_bins : Np1DNumberArray
            The normalized bins of the RDF analysis based on the spherical shell model.
        integrated_bins : Np1DNumberArray
            The integrated bins of the RDF analysis.
        normalized_bins2 : Np1DNumberArray
            The normalized bins of the RDF analysis based on the number of atoms in the system.
        differential_bins : Np1DNumberArray
            The differential bins of the RDF analysis based on the spherical shell model.
        """
        self._average_volume = self.average_volume
        self._reference_density = len(
            self.reference_indices) / self._average_volume

        # ATTENTION works only with constant topology!!!
        target_index_combinations = []
        for reference_index in self.reference_indices:

            if self.no_intra_molecular:
                residue_indices = self.topology.residue_atom_indices[reference_index]
                target_index_combinations.append(
                    np.setdiff1d(self.target_indices, residue_indices))

        for frame in tqdm(self.frame_generator, total=self.n_frames, disable=not config.with_progress_bar):

            for i, reference_index in enumerate(self.reference_indices):

                if self.no_intra_molecular:
                    target_indices = target_index_combinations[i]

                else:
                    target_indices = self.target_indices

                reference_position = frame.pos[reference_index]
                target_positions = frame.pos[target_indices]

                distances = distance(reference_position,
                                     target_positions, frame.cell)

                self.bins += _add_to_bins(distances, self.r_min,
                                          self.delta_r, self.n_bins)

        if self.no_intra_molecular:
            target_density = (len(self.target_indices) - 1) / \
                self._average_volume
        else:
            target_density = len(self.target_indices) / self._average_volume

        norm = _norm(self.n_bins, self.delta_r, target_density,
                     len(self.reference_indices), self.n_frames)

        normalized_bins = self.bins / norm
        integrated_bins = _integration(self.bins, len(
            self.reference_indices), self.n_frames)
        normalized_bins2 = self.bins / target_density / \
            len(self.reference_indices) / self.n_frames
        differential_bins = self.bins - norm

        return self.bin_middle_points, normalized_bins, integrated_bins, normalized_bins2, differential_bins

    @property
    def n_frames(self) -> int:
        """int: The number of frames of the RDF analysis."""
        return len(self.cells)

    @property
    def n_atoms(self) -> int:
        """int: The number of atoms of the RDF analysis."""
        return self.topology.n_atoms


def _add_to_bins(distances: Np1DNumberArray, r_min: PositiveReal, delta_r: PositiveReal, n_bins: PositiveInt) -> Np1DNumberArray:
    """
    Returns the bins of the RDF analysis based on the provided distances.

    Parameters
    ----------
    distances : Np1DNumberArray
        The distances to add to the bins of the RDF analysis.
    r_min : PositiveReal
        minimum (starting) radius of the RDF analysis
    delta_r : PositiveReal
        spacing between bins
    n_bins : PositiveInt
        number of bins

    Returns
    -------
    Np1DNumberArray
        The bins of the RDF analysis.
    """
    distances = np.floor_divide(
        distances - r_min, delta_r).astype(int)

    distances = distances[(distances < n_bins) & (distances >= 0)]

    return np.bincount(distances, minlength=n_bins)


def _setup_bin_middle_points(n_bins: PositiveInt, r_min: PositiveReal, r_max: PositiveReal, delta_r: PositiveReal) -> Np1DNumberArray:
    """
    Sets up the middle points of the bins of the RDF analysis for outputting the RDF analysis.

    Parameters
    ----------
    n_bins : PositiveInt
        number of bins
    r_min : PositiveReal
        minimum (starting) radius of the RDF analysis
    r_max : PositiveReal
        maximum radius of the RDF analysis
    delta_r : PositiveReal
        spacing between bins

    Returns
    -------
    Np1DNumberArray
        The middle points of the bins of the RDF analysis.
    """
    bin_middle_points = np.arange(r_min + delta_r / 2, r_max, delta_r)

    assert len(bin_middle_points) == n_bins

    return bin_middle_points


def _calculate_r_max(n_bins: PositiveInt, delta_r: PositiveReal, r_min: PositiveReal, traj: Trajectory) -> PositiveReal:
    """
    Calculates the maximum radius of the RDF analysis from the provided parameters.

    Parameters
    ----------
    n_bins : PositiveInt
        number of bins
    delta_r : PositiveReal
        spacing between bins
    r_min : PositiveReal
        minimum (starting) radius of the RDF analysis
    traj : Trajectory
        The trajectory to check the maximum radius of the RDF analysis against.

    Returns
    -------
    PositiveReal
        maximum radius of the RDF analysis
    """
    r_max = delta_r * n_bins + r_min
    r_max = _check_r_max(r_max, traj)

    return r_max


def _check_r_max(r_max: PositiveReal, cells: List[Cell]) -> PositiveReal:
    """
    Checks if the provided maximum radius is larger than the maximum allowed radius according to the box vectors of the trajectory.

    Parameters
    ----------
    r_max : PositiveReal
        maximum radius of the RDF analysis
    traj : Trajectory
        The trajectory to check the maximum radius of the RDF analysis against.

    Returns
    -------
    PositiveReal
        maximum radius of the RDF analysis if it is smaller than the maximum allowed radius
        according to the box vectors of the trajectory, than the maximum allowed radius according to the box vectors of the trajectory.
    Raises
    ------
    RDFWarning
        If the calculated r_max is larger than the maximum allowed radius according to the box vectors of the trajectory.
    """
    if check_trajectory_PBC(cells) and r_max > _infer_r_max(cells):
        warnings.warn(
            f"The calculated r_max {r_max} is larger than the maximum allowed radius \
according to the box vectors of the trajectory {_infer_r_max(cells)}. \
r_max will be set to the maximum allowed radius.", RDFWarning)

        r_max = _infer_r_max(cells)

    return r_max


def _calculate_n_bins(delta_r: PositiveReal, r_max: PositiveReal, r_min: PositiveReal) -> Tuple[PositiveInt, PositiveReal]:
    """
    Calculates the number of bins of the RDF analysis from the provided parameters.

    The number of bins is calculated as the number of bins that fit in the range between r_min and r_max.
    The maximum radius is re-calculated from the number of bins and delta_r to ensure that the maximum radius is a multiple of delta_r.

    Parameters
    ----------
    delta_r : PositiveReal
        spacing between bins
    r_max : PositiveReal
        maximum radius of the RDF analysis
    r_min : PositiveReal
        minimum (starting) radius of the RDF analysis

    Returns
    -------
    PositiveInt
        number of bins of the RDF analysis
    PositiveReal
        maximum radius of the RDF analysis
    """
    n_bins = int((r_max - r_min) / delta_r)
    r_max = delta_r * n_bins + r_min

    return n_bins, r_max


def _infer_r_max(cells: List[Cell]) -> PositiveReal:
    """
    Infers the maximum radius of the RDF analysis from the box vectors of the trajectory.

    If the trajectory is in vacuum, an RDFError is raised as the maximum radius cannot be inferred from the box vectors.

    Parameters
    ----------
    traj : Trajectory
        The trajectory to infer the maximum radius of the RDF analysis from.

    Returns
    -------
    r_max: PositiveReal
        The maximum radius of the RDF analysis.

    Raises
    ------
    RDFError
        If the trajectory is in vacuum.
    """
    if not check_trajectory_PBC(cells):
        raise RDFError(
            "To infer r_max of the RDF analysis, the trajectory cannot be a vacuum trajectory. Please specify r_max manually or use the combination n_bins and delta_r.")

    return np.min([cell.box_lengths for cell in cells]) / 2.0


def _norm(n_bins: int, delta_r: PositiveReal, target_density: PositiveReal, n_reference_indices: int, n_frames: int) -> Np1DNumberArray:
    """
    Calculates the normalization of the RDF analysis based on a spherical shell model.

    Parameters
    ----------
    n_bins : int
        The number of bins of the RDF analysis.
    delta_r : PositiveReal
        The spacing between bins of the RDF analysis.
    target_density : PositiveReal
        The target density of the RDF analysis.
    n_reference_indices : int
        The number of reference indices of the RDF analysis.
    n_frames : int
        The number of frames of the RDF analysis.

    Returns
    -------
    Np1DNumberArray
        The normalization of the RDF analysis.
    """

    volume = 4.0 / 3.0 * np.pi * \
        (np.arange(1, n_bins + 1)**3 -
            np.arange(0, n_bins) ** 3) * delta_r ** 3

    return volume * target_density * n_reference_indices * n_frames


def _integration(bins: Np1DNumberArray, n_reference_indices: int, n_frames: int) -> Np1DNumberArray:
    """
    Calculates the integrated RDF analysis. The integral is calculated using a cumulative sum.

    Parameters
    ----------
    bins : Np1DNumberArray
        The bins of the RDF analysis.
    n_reference_indices : int
        The number of reference indices of the RDF analysis.
    n_frames : int
        The number of frames of the RDF analysis.

    Returns
    -------
    Np1DNumberArray
        The integrated RDF analysis.
    """

    return np.cumsum(bins) / (n_reference_indices * n_frames)
