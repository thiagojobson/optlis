from typing import Union, Tuple, Dict, Any

from pathlib import Path

import numpy as np
import networkx as nx  # type: ignore

from optlis.dynamic.problem_data import Instance, export_instance


def _graph(size: Tuple[int, int] = (1, 1), res: Tuple[int, int] = (1, 1)) -> Instance:
    """Generates a problem instance."""
    lattice = nx.triangular_lattice_graph(size[0], size[1])
    g = nx.convert_node_labels_to_integers(lattice)

    # Set default attributes for all nodes
    nx.set_node_attributes(g, values=1, name="type")
    nx.set_node_attributes(g, values=0, name="D")
    nx.set_node_attributes(g, values=0, name="Qn")
    nx.set_node_attributes(g, values=0, name="Qc")

    # Updates the depot's attributes
    g.nodes[0]["type"] = 0
    g.nodes[0]["Qn"] = res[0]
    g.nodes[0]["Qc"] = res[1]

    return g


def two_species_instance(size, res, zero_degradation_rate=False, random_seed=0):
    """Generates a random two species model instance."""
    g = _graph(size, res)

    nnodes = len(g.nodes)
    ntasks = len([n for n in g.nodes if g.nodes[n]["type"] == 1])
    rng = np.random.default_rng(random_seed)

    nproducts = 3
    products = (0, 1, 2)
    risk = rng.uniform(0.1, 1, nproducts)
    risk[0] = 0

    # Generates `|V|` random initial concentration for each product specie
    initial_concentration = rng.normal(0.5, 0.5, (nnodes, nproducts))
    for i in range(nnodes):
        for j in range(nproducts):
            if j == 0:
                initial_concentration[i][j] = 0

            elif initial_concentration[i][j] < 0:
                initial_concentration[i][j] = 0

    if zero_degradation_rate:
        degradation_rate = np.zeros(nproducts)
    else:
        degradation_rate = rng.uniform(0.01, 0.05, nproducts)

    metabolization_map = {(products[1], products[2]): rng.uniform(0.01, 0.05)}

    return Instance(
        g.nodes(data=True),
        risk,
        degradation_rate,
        metabolization_map,
        initial_concentration,
    )


def generate_benchmark(export_dir: Union[str, Path] = "", random_seed: int = 0) -> None:
    """Generate the instance benchmark."""
    # Generates graphs with n = 9, 17, 33 (1 depot + n-1 tasks)
    for size in [(5, 1), (2, 9), (4, 11)]:
        # Gets the amount of nodes generated by the `size` of the hex grid
        # which should be n = 9, 17, 33 (1 depot + n-1 tasks)
        instance = two_species_instance(size, res=(0, 1), random_seed=random_seed)
        n = len(instance.nodes)
        export_instance(instance, Path(f"{export_dir}/hx-n{n-1}-pu-ru-q{1}.dat"))

        # Generates instances with 2^0, 2^1, ..., 2^log_2(n-1) teams
        for q in [2**i for i in range(1, 10) if 2**i < n] + [n - 1]:
            export_instance(
                two_species_instance(size, res=(0, q), random_seed=random_seed),
                Path(f"{export_dir}/hx-n{n-1}-pu-ru-q{q}.dat"),
            )


def from_command_line(args: Dict[str, Any]) -> None:
    generate_benchmark(args["export-dir"], args["seed"])
