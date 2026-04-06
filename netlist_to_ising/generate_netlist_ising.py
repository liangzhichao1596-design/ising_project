from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PRIMITIVE_COMMON_DIR = THIS_DIR.parent / "primitive" / "common"
sys.path.append(str(PRIMITIVE_COMMON_DIR))

from ising_primitive_lib import (  # type: ignore
    Polynomial,
    build_primitive,
    fraction_to_str,
    parse_verilog_int,
)


@dataclass
class Instance:
    primitive: str
    name: str
    params: dict[str, int]
    connections: dict[str, str]


def parse_signal_names(declaration_body: str) -> list[str]:
    text = re.sub(r"\[[^\]]+\]", " ", declaration_body)
    text = re.sub(r"\b(?:wire|reg|logic|signed|unsigned)\b", " ", text)
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_declarations(text: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    pattern = re.compile(r"(?m)^\s*(input|output|wire)\s+([^;]+);")
    for kind, body in pattern.findall(text):
        for name in parse_signal_names(body):
            declarations.setdefault(name, kind.upper())
    return declarations


def parse_instances(text: str) -> list[Instance]:
    pattern = re.compile(
        r"(?ms)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"(?:#\s*\((.*?)\))?\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"\((.*?)\)\s*;"
    )
    instances: list[Instance] = []
    for primitive, param_block, instance_name, connection_block in pattern.findall(text):
        if primitive == "module":
            continue
        params: dict[str, int] = {}
        if param_block:
            for param_name, param_value in re.findall(r"\.(\w+)\s*\(\s*([^)]+?)\s*\)", param_block, flags=re.S):
                params[param_name] = parse_verilog_int(param_value.strip())
        connections: dict[str, str] = {}
        for port_name, signal_name in re.findall(r"\.(\w+)\s*\(\s*([^)]+?)\s*\)", connection_block, flags=re.S):
            connections[port_name] = signal_name.strip()
        instances.append(Instance(primitive=primitive, name=instance_name, params=params, connections=connections))
    return instances


def monomial_sort_key(vars_in_term: tuple[str, ...]) -> tuple[int, tuple[int, ...]]:
    encoded = []
    for var in vars_in_term:
        encoded.append(int(var[2:-1]))
    return (len(vars_in_term), tuple(encoded))


def single_term_string(coeff: Fraction, vars_in_term: tuple[str, ...]) -> str:
    if not vars_in_term:
        return fraction_to_str(coeff)
    var_text = "*".join(vars_in_term)
    if coeff == 1:
        return var_text
    if coeff == -1:
        return f"-{var_text}"
    return f"{fraction_to_str(coeff)}*{var_text}"


def split_polynomial(poly: Polynomial) -> tuple[Polynomial, Polynomial]:
    quadratic = Polynomial()
    cubic = Polynomial()
    for vars_in_term, coeff in poly.terms.items():
        if len(vars_in_term) == 3:
            cubic.add_term(coeff, vars_in_term)
        else:
            quadratic.add_term(coeff, vars_in_term)
    return quadratic, cubic


def compute_min_energy(poly: Polynomial, qubit_names: list[str]) -> Fraction:
    best: Fraction | None = None
    for spins in product([-1, 1], repeat=len(qubit_names)):
        assignment = dict(zip(qubit_names, spins))
        energy = poly.evaluate(assignment)
        if best is None or energy < best:
            best = energy
    if best is None:
        return Fraction(0)
    return best


def format_mapping_lines(qubit_descriptions: dict[str, str], net_connections: dict[str, list[str]]) -> list[str]:
    lines = ["Index      | Description", "-" * 72]
    for q_name in sorted(qubit_descriptions, key=lambda item: int(item[2:-1])):
        base = qubit_descriptions[q_name]
        suffix = ""
        if q_name in net_connections:
            suffix = f" | connections: {', '.join(net_connections[q_name])}"
        lines.append(f"{q_name.ljust(10)} : {base}{suffix}")
    return lines


def build_netlist_polynomial(netlist_path: Path) -> tuple[str, list[Instance], Polynomial, dict[str, str], dict[str, list[str]]]:
    text = netlist_path.read_text(encoding="utf-8")
    module_match = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\b", text)
    if not module_match:
        raise ValueError(f"Could not find module declaration in {netlist_path}")
    module_name = module_match.group(1)
    declarations = parse_declarations(text)
    instances = parse_instances(text)
    if not instances:
        raise ValueError(f"No primitive instances found in {netlist_path}")

    total_poly = Polynomial()
    net_to_global_q: dict[str, str] = {}
    qubit_descriptions: dict[str, str] = {}
    net_connections: dict[str, list[str]] = {}
    next_q_index = 0

    def alloc_qubit(description: str) -> str:
        nonlocal next_q_index
        q_name = f"q[{next_q_index}]"
        next_q_index += 1
        qubit_descriptions[q_name] = description
        return q_name

    def ensure_net_qubit(net_name: str) -> str:
        if net_name not in net_to_global_q:
            net_kind = declarations.get(net_name, "WIRE")
            net_to_global_q[net_name] = alloc_qubit(f"[{net_kind}] {net_name}")
        return net_to_global_q[net_name]

    for instance in instances:
        builder, definition, resolved_params = build_primitive(instance.primitive, instance.params)
        local_to_global: dict[str, str] = {}
        port_q_to_name = {q_name: port for port, q_name in builder.port_to_q.items()}

        for port_name in definition.input_ports + definition.output_ports:
            if port_name not in instance.connections:
                raise ValueError(f"Missing connection for {instance.name}.{port_name}")
            net_name = instance.connections[port_name]
            global_q = ensure_net_qubit(net_name)
            local_q = builder.q(port_name)
            local_to_global[local_q] = global_q
            net_connections.setdefault(global_q, [])
            endpoint = f"{instance.name}.{port_name}"
            if endpoint not in net_connections[global_q]:
                net_connections[global_q].append(endpoint)

        for local_q, local_desc in sorted(builder.var_map.items(), key=lambda item: int(item[0][2:-1])):
            if local_q in local_to_global:
                continue
            local_to_global[local_q] = alloc_qubit(f"{instance.name} {local_desc}")

        total_poly.extend(builder.polynomial.renamed(local_to_global))

    return module_name, instances, total_poly, qubit_descriptions, net_connections


def write_report(
    netlist_path: Path,
    report_path: Path,
    module_name: str,
    instances: list[Instance],
    total_poly: Polynomial,
    qubit_descriptions: dict[str, str],
    net_connections: dict[str, list[str]],
) -> None:
    quadratic_poly, cubic_poly = split_polynomial(total_poly)
    qubit_names = sorted(qubit_descriptions, key=lambda item: int(item[2:-1]))
    min_energy = compute_min_energy(total_poly, qubit_names)

    cubic_lines = ["cubic_terms_list = ["]
    cubic_terms_sorted = sorted(cubic_poly.terms.items(), key=lambda item: monomial_sort_key(item[0]))
    for vars_in_term, coeff in cubic_terms_sorted:
        cubic_lines.append(f"    '{single_term_string(coeff, vars_in_term)}',")
    cubic_lines.append("]")

    mapping_lines = format_mapping_lines(qubit_descriptions, net_connections)

    instance_lines = ["Instance    | Primitive | Parameters | Connections", "-" * 100]
    for instance in instances:
        param_text = ", ".join(f"{key}=0x{value:X}" for key, value in sorted(instance.params.items())) or "-"
        conn_text = ", ".join(f".{port}({net})" for port, net in sorted(instance.connections.items()))
        instance_lines.append(
            f"{instance.name.ljust(11)} | {instance.primitive.ljust(9)} | {param_text.ljust(10)} | {conn_text}"
        )

    lines = [
        "=" * 88,
        f" NETLIST TO ISING REPORT ({module_name})",
        "=" * 88,
        f"Source Netlist: {netlist_path}",
        f"Primitive Instance Count: {len(instances)}",
        f"Total Qubits: {len(qubit_names)}",
        f"Total Minimum Energy: {fraction_to_str(min_energy)}",
        "-" * 88,
        "",
        "[1. CUBIC TERMS LIST (With Coefficients)]",
        *cubic_lines,
        "",
        "-" * 88,
        "[2. F_QUADRATIC (Linear + Quadratic terms only)]",
        quadratic_poly.expression_string(),
        "",
        "-" * 88,
        "[3. F_TOTAL (Full Hamiltonian including Cubic)]",
        total_poly.expression_string(),
        "",
        "-" * 88,
        "[4. FULL VARIABLE MAPPING]",
        *mapping_lines,
        "",
        "-" * 88,
        "[5. INSTANCE SUMMARY]",
        *instance_lines,
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def default_report_path(netlist_path: Path) -> Path:
    return netlist_path.with_name(f"{netlist_path.stem}_ising.log")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose primitive Ising models from a Vivado structural netlist.")
    parser.add_argument("netlist", nargs="?", default=str(THIS_DIR / "mux2_1.v"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    netlist_path = Path(args.netlist).resolve()
    report_path = Path(args.output).resolve() if args.output else default_report_path(netlist_path)

    module_name, instances, total_poly, qubit_descriptions, net_connections = build_netlist_polynomial(netlist_path)
    write_report(netlist_path, report_path, module_name, instances, total_poly, qubit_descriptions, net_connections)
    print(report_path)


if __name__ == "__main__":
    main()
