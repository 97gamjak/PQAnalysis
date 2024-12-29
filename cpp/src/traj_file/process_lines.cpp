#include "process_lines.hpp"

#include <sstream>

std::pair<std::vector<std::string>, std::vector<float>> process_lines_with_atoms(
    const std::vector<std::string>& input,
    int                             n_atoms
)
{
    std::vector<std::string> atoms(n_atoms);
    std::vector<float>       xyz(n_atoms * 3);

    for (int i = 0; i < n_atoms; i++)
    {
        std::istringstream iss(input[i]);
        std::string        atom;
        float              x, y, z;

        if (!(iss >> atom >> x >> y >> z))
        {
            throw std::runtime_error("Could not parse line");
        }

        atoms[i]         = atom;
        xyz[(i * 3) + 0] = x;
        xyz[(i * 3) + 1] = y;
        xyz[(i * 3) + 2] = z;
    }

    // Return atoms and xyz coordinates
    return {atoms, xyz};
}