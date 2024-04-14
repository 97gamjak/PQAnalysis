from PQAnalysis.types import PositiveInt, PositiveReal


class Bond:
    def __init__(self,
                 index1: PositiveInt,
                 index2: PositiveInt,
                 equilibrium_distance: PositiveReal | None = None,
                 bond_type: PositiveInt | None = None,
                 is_linker: bool = False,
                 is_shake: bool = False,
                 ) -> None:

        self.index1 = index1
        self.index2 = index2
        self.equilibrium_distance = equilibrium_distance
        self.bond_type = bond_type
        self.is_linker = is_linker
        self.is_shake = is_shake

    def copy(self):
        return Bond(
            index1=self.index1,
            index2=self.index2,
            equilibrium_distance=self.equilibrium_distance,
            bond_type=self.bond_type,
            is_linker=self.is_linker,
            is_shake=self.is_shake,
        )
