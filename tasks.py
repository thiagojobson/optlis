from pathlib import Path
from invoke import task, Failure


import optlis
from optlis.static.problem_data import load_instance
from optlis.static.models.ils import show_stats, optimize as ils
from optlis.static.models.milp import model_1, model_2, optimize as cplex


@task
def check(c):
    """Checks all the required dependencies."""
    print("Checking gcc...", end="")
    has_gcc = c.run("which gcc", warn=True, hide=True)
    print("OK" if has_gcc else "not found")


# @task
# def build(c):
#     """Builds the c library with the gcc compiler."""
#     build_dir, lib_dir = Path("./build"), Path("./lib")
#     build_dir.mkdir(exist_ok=True)
#     lib_dir.mkdir(exist_ok=True)

#     print("Building c library with gcc...", end="")
#     try:
#         c.run(
#             "gcc -c -fPIC optlis/solvers/localsearch.c -o "
#             f"{build_dir / 'localsearch.o'}"
#         )
#         c.run(
#             f"gcc -shared -Wl,-soname,localsearch.so -o "
#             f"{lib_dir / 'localsearch.so'} {build_dir / 'localsearch.o'}"
#         )
#     except Failure as ex:
#         print(ex)
#     else:
#         print("Done")


@task(
    help={
        "export_dir": "Directory to export instances.",
        "seed": "Sets the seed for the random number generator (default 0).",
    }
)
def export_benchmark(c, export_dir, seed=0):
    """Exports the instance benchmark to disk."""
    export_to = Path(export_dir)

    # Exports static instances
    export_to_static = export_to / "static"
    export_to_static.mkdir(parents=True, exist_ok=True)
    optlis.static.instance_benchmark.generate_benchmark(export_to_static, seed)

    # Exports dynamic instances
    export_to_dynamic = export_to / "dynamic"
    export_to_dynamic.mkdir(parents=True, exist_ok=True)
    optlis.dynamic.instance_benchmark.generate_benchmark(export_to_dynamic, seed)


@task(
    help={
        "method": "Chooses the optimization method (cplex or ils).",
        "inst_dir": "Directory where instances are located.",
        "relaxation": "Sets the relaxation threshold (in range [0, 1] default 0).",
        "perturbation": "Sets the perturb. strength (ils only, in range [0, 1] default 0.5)",
        "stop": "Sets the stopping criterion. In seconds when solving with cplex, "
        "in objective function calls when solving with ils.",
        "repeat": "Sets the number of repetitions to perform (ils only, default 35).",
        "parallel": "Sets the number of parallel processes (ils only, default 4).",
        "tt-off": "Disables travel times.",
        "log_dir": "Directory to export execution logs.",
        "sol_dir": "Directory to export solutions.",
    }
)
def bulk_solve(
    c,
    method,
    inst_dir,
    relaxation=0.0,
    perturbation=0.5,
    stop=0,
    repeat=35,
    parallel=4,
    tt_off=False,
    log_dir=None,
    sol_dir=None,
):
    """Solves all instances located in the 'inst-dir' directory."""
    if method.lower() == "ils":
        _bulk_solve_ils(
            inst_dir, relaxation, perturbation, stop, repeat, parallel, tt_off
        )
    elif method.lower() == "cplex":
        _bulk_solve_cplex(inst_dir, relaxation, stop, tt_off, log_dir, sol_dir)
    else:
        raise ValueError(f"'{method}' is not a valid option, use 'cplex' or 'ils'")


def _bulk_solve_ils(inst_dir, relaxation, perturbation, stop, repeat, parallel, tt_off):
    inst_paths = sorted(Path(inst_dir).glob("hx-*.dat"))
    for i, path in enumerate(inst_paths):
        print(f"Solving instance {path} ({i} of {len(inst_paths)})...")
        instance = load_instance(path, not tt_off)
        results = ils(
            instance=instance,
            runs=repeat,
            parallel=parallel,
            perturbation_strength=_get_irace_config(tt_off, relaxation),
            relaxation_threshold=relaxation,
            evaluations=stop,
        )
        show_stats(results)
        print("")


def _bulk_solve_cplex(inst_dir, relaxation, stop, tt_off, log_dir, sol_dir):
    inst_paths = sorted(Path(inst_dir).glob("hx-*.dat"))
    model = model_1 if tt_off else model_2
    for i, path in enumerate(inst_paths):
        print(f"Solving instance {path} ({i} of {len(inst_paths)})...")
        instance = load_instance(path, not tt_off)
        results = cplex(
            instance=instance,
            make_model=model,
            relaxation_threshold=relaxation,
            time_limit=stop,
        )
        print("")


def _get_irace_config(tt_off, relaxation):
    """These values were separately generated by the irace package and are hardcoded
    here for the purpuse of repeatability of results.
    """
    if tt_off:
        if relaxation == 0:
            return 0.5
        elif relaxation == 0.5:
            return 0.56
        else:
            return 0.24
    else:
        if relaxation == 0:
            return 0.61
        elif relaxation == 0.5:
            return 0.19
        else:
            return 0.86
    return perturbation
