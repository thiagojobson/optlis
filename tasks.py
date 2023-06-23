from pathlib import Path
from invoke import task, Failure


import optlis
from optlis import static, dynamic


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
        "solver": "Chooses the optimization method (cplex or ils)",
        "inst_dir": "Directory where instances are located",
        "dynamic": "Sets the problem type to dynamic",
        "relaxation": "Sets the relaxation threshold (in range [0, 1] default 0)",
        "perturbation": "Sets the perturb. strength (ils only, in range [0, 1] default 0.5)",
        "stop": "Sets the stopping criterion. In seconds when solving with cplex, "
        "in objective function calls when solving with ils",
        "repeat": "Sets the number of repetitions to perform (ils only, default 35)",
        "parallel": "Sets the number of parallel processes (ils only, default 4)",
        "tt-off": "Disables travel times",
        "log_dir": "Directory to export execution logs",
        "sol_dir": "Directory to export solutions",
    }
)
def bulk_solve(
    c,
    solver,
    inst_dir,
    dynamic=False,
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
    if solver.lower() == "ils":
        if dynamic:
            raise NotImplementedError
        else:
            _bulk_solve_static_ils(
                inst_dir, relaxation, perturbation, stop, repeat, parallel, tt_off
            )
    elif solver.lower() == "cplex":
        if dynamic:
            _bulk_solve_dynamic_cplex(inst_dir, stop, log_dir, sol_dir)
        else:
            _bulk_solve_static_cplex(
                inst_dir, relaxation, stop, tt_off, log_dir, sol_dir
            )
    else:
        raise ValueError(f"'{solver}' is not a valid option, use 'cplex' or 'ils'")


def _bulk_solve_static_ils(
    inst_dir, relaxation, perturbation, stop, repeat, parallel, tt_off
):
    inst_paths = sorted(Path(inst_dir).glob("hx-*.dat"))
    for i, path in enumerate(inst_paths):
        print(f"Solving instance {path} ({i} of {len(inst_paths)})...")
        instance = static.problem_data.load_instance(path, not tt_off)
        results = static.models.ils.optimize(
            instance=instance,
            runs=repeat,
            parallel=parallel,
            perturbation_strength=_get_irace_static_config(tt_off, relaxation),
            relaxation_threshold=relaxation,
            evaluations=stop,
        )
        static.models.ils.show_stats(results)
        print("")


def _bulk_solve_static_cplex(
    inst_dir, relaxation, time_limit, tt_off, log_dir, sol_dir
):

    if tt_off:
        model = static.models.milp
    else:
        model = static.models.milp.model_2

    inst_paths = sorted(Path(inst_dir).glob("hx-*.dat"))
    for i, path in enumerate(inst_paths):
        print(f"Solving instance {path} ({i} of {len(inst_paths)})...")
        instance = static.problem_data.load_instance(path, not tt_off)

        if sol_dir:
            sol_path = Path(sol_dir) / f"{path.stem}.sol"
        else:
            sol_path = None

        if log_dir:
            log_path = Path(log_dir) / f"{path.stem}.log"
        else:
            log_path = None

        results = static.models.milp.optimize(
            instance=instance,
            make_model=model,
            relaxation_threshold=relaxation,
            time_limit=time_limit,
            log_path=log_path,
            sol_path=sol_path,
        )
        print("")


def _bulk_solve_dynamic_cplex(inst_dir, time_limit, log_dir, sol_dir):

    inst_paths = sorted(Path(inst_dir).glob("hx-*.dat"))
    for i, path in enumerate(inst_paths):
        print(f"Solving instance {path} ({i} of {len(inst_paths)})...")
        instance = dynamic.problem_data.load_instance(path)

        if sol_dir:
            sol_path = Path(sol_dir) / f"{path.stem}.sol"
        else:
            sol_path = None

        if log_dir:
            log_path = Path(log_dir) / f"{path.stem}.log"
        else:
            log_path = None

        results = dynamic.models.milp.optimize(
            instance=instance,
            time_limit=time_limit,
            log_path=log_path,
            sol_path=sol_path,
        )
        print("")


def _get_irace_static_config(tt_off, relaxation):
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
