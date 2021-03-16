from itertools import groupby

import networkx as nx


class Graph(nx.Graph):
    """Subclass of nx.Graph class with some utility properties."""
    
    @property
    def origins(self):
        """Returns the list of origins."""
        # Note: is there a better way to do this?
        return [n for n in self.nodes if self.nodes[n]["type"] == 0]

    @property 
    def destinations(self):
        """Returns the list of destinations."""
        return [n for n in self.nodes if self.nodes[n]["type"] == 1]

    @property
    def time_periods(self):
        """Returns a list of time periods from 1 to T with T being
           an upper bound i.e. the sum of all p_i miltiplied by 2
           to try to accomodate the distance between nodes.

           NOTE: This increases significantly the number of variables
                 in the linear model. Might need a smarter way for 
                 guessing T.
           NOTE: If we are to consider the distance for crossing nodes
                 it's even more difficult to guess an upper bound.
        """
        T = sum(self.nodes[n]["p"] for n in self.nodes())*2
        return list(range(1, T+1))

    @property
    def precedencies(self):
        """Returns a list of precedence represented by tuples
          (i, j) where i must start before j i.e. r_i > r_j.
          The precedencies must form an acyclic graph.
        """
        r = nx.get_node_attributes(self, "r")
        # Create a dict sorted by the r attr desc
        sortedr = {i: ri for i, ri in sorted(r.items(), key=lambda x: x[1],
                                             reverse=True)}
        aggr = {ri: list(li) for ri, li in groupby(sortedr.items(),
                                                   key=lambda x: x[1])}
        rvalues = list(aggr.keys())
        for li, lj in zip(rvalues, rvalues[1:]):
            for i, ri in aggr[li]:
                for j, rj in aggr[lj]:
                    # Last check: exclude origins from precedence
                    if j not in self.origins:
                        yield (i, j)


def loads(path):
    """Loads an instance from a file."""
    nodes = []
    edges = []
    with open(path, "r") as f:
        nb_nodes = int(f.readline())
        for _ in range(nb_nodes):
            id, type, p, q, r = f.readline().split()
            nodes.append((int(id), {
                "type": int(type),
                "p": int(p),
                "q": int(q),
                "r": float(r),
            }))

        nb_edges = int(f.readline())
        for _ in range(nb_edges):
            i, j = [int(u) for u in f.readline().split()]
            edges.append((i, j))
    
    G = Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G


def save(G, path):
    """Saves an instance to a file."""
    nb_nodes = len(G.nodes)
    nb_edges = len(G.edges)
    with open(path, "w") as f:
        f.write(f"{nb_nodes}\n")        
        for (id, data) in G.nodes(data=True):
            type, p, q, r = (data["type"],
                             data["p"],
                             data["q"],
                             data["r"])
            f.write(f"{id} {type} {p} {q} {r:.2f}\n")
        f.write(f"{nb_edges}\n")
        for (i, j) in G.edges():
            f.write(f"{i} {j}\n")
