from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
NETLIST_TO_ISING_DIR = THIS_DIR.parent

if str(NETLIST_TO_ISING_DIR) not in sys.path:
    sys.path.append(str(NETLIST_TO_ISING_DIR))

from generate_netlist_ising import (  # type: ignore
    Polynomial,
    build_netlist_polynomial,
    fraction_to_str,
    write_report,
)


def bit_to_spin(bit: int) -> int:
    return 1 if int(bit) else -1


def spin_to_bit(spin: int) -> int:
    return 1 if int(spin) > 0 else 0


def add_pin_constraint(poly: Polynomial, q_name: str, spin: int) -> None:
    # Penalty = 1 - s*q. It is 0 when q == s and 2 otherwise.
    poly.add_term(1, tuple())
    poly.add_term(-spin, (q_name,))


def copy_polynomial(poly: Polynomial) -> Polynomial:
    out = Polynomial()
    out.extend(poly)
    return out


def solve_min_energy(poly: Polynomial, qubit_names: list[str]) -> tuple[Fraction, list[dict[str, int]]]:
    best: Fraction | None = None
    best_assignments: list[dict[str, int]] = []
    for spins in product([-1, 1], repeat=len(qubit_names)):
        assignment = dict(zip(qubit_names, spins))
        energy = poly.evaluate(assignment)
        if best is None or energy < best:
            best = energy
            best_assignments = [assignment]
        elif energy == best:
            best_assignments.append(assignment)
    if best is None:
        raise RuntimeError("No assignments evaluated.")
    return best, best_assignments


def get_named_qubits(qubit_descriptions: dict[str, str]) -> dict[str, str]:
    wanted = {"in1", "in2", "sel", "out"}
    named: dict[str, str] = {}
    for q_name, description in qubit_descriptions.items():
        for signal_name in wanted:
            if description.startswith(f"[INPUT] {signal_name}") or description.startswith(f"[OUTPUT] {signal_name}"):
                named[signal_name] = q_name
    missing = sorted(wanted - named.keys())
    if missing:
        raise ValueError(f"Failed to locate named qubits for: {', '.join(missing)}")
    return named


@dataclass
class CaseResult:
    bits: tuple[int, int, int]
    expected_out: int
    free_energy: Fraction
    observed_outs: list[int]
    correct_energy: Fraction
    wrong_energy: Fraction


def analyze_case(
    total_poly: Polynomial,
    qubit_names: list[str],
    named_qubits: dict[str, str],
    in1: int,
    in2: int,
    sel: int,
) -> CaseResult:
    # This sample follows the source RTL used to generate the Vivado netlist:
    #   sel=0 -> out=in2
    #   sel=1 -> out=in1
    expected_out = in2 if sel == 0 else in1
    input_pins = {
        named_qubits["in1"]: bit_to_spin(in1),
        named_qubits["in2"]: bit_to_spin(in2),
        named_qubits["sel"]: bit_to_spin(sel),
    }

    free_model = copy_polynomial(total_poly)
    for q_name, spin in input_pins.items():
        add_pin_constraint(free_model, q_name, spin)
    free_energy, free_solutions = solve_min_energy(free_model, qubit_names)

    observed_outs = sorted({spin_to_bit(solution[named_qubits["out"]]) for solution in free_solutions})

    correct_model = copy_polynomial(free_model)
    add_pin_constraint(correct_model, named_qubits["out"], bit_to_spin(expected_out))
    correct_energy, _ = solve_min_energy(correct_model, qubit_names)

    wrong_model = copy_polynomial(free_model)
    add_pin_constraint(wrong_model, named_qubits["out"], bit_to_spin(1 - expected_out))
    wrong_energy, _ = solve_min_energy(wrong_model, qubit_names)

    return CaseResult(
        bits=(in1, in2, sel),
        expected_out=expected_out,
        free_energy=free_energy,
        observed_outs=observed_outs,
        correct_energy=correct_energy,
        wrong_energy=wrong_energy,
    )


def build_summary_lines(results: list[CaseResult], report_path: Path, netlist_path: Path) -> list[str]:
    lines = [
        "=" * 88,
        " MUX2_1 FORMAL-LIKE ISING EXAMPLE",
        "=" * 88,
        f"Source Netlist: {netlist_path}",
        f"Generated Ising Report: {report_path}",
        "",
        "Interpretation:",
        "1. Fix primary inputs in1/in2/sel.",
        "2. Minimize the netlist Ising Hamiltonian.",
        "3. Read the output value from the minimum-energy states.",
        "4. Force the wrong output and check that the minimum energy rises.",
        "",
        "Case Table:",
        "in1 in2 sel | expected | minE(free) | outputs@minE | minE(correct) | minE(wrong)",
        "-" * 88,
    ]

    for result in results:
        outputs_text = ",".join(str(bit) for bit in result.observed_outs)
        lines.append(
            f" {result.bits[0]}   {result.bits[1]}   {result.bits[2]}  |"
            f"    {result.expected_out}     |"
            f"    {fraction_to_str(result.free_energy).rjust(3)}     |"
            f"     {outputs_text:<8} |"
            f"      {fraction_to_str(result.correct_energy).rjust(3)}      |"
            f"     {fraction_to_str(result.wrong_energy).rjust(3)}"
        )

    all_good = all(
        result.observed_outs == [result.expected_out]
        and result.correct_energy == result.free_energy
        and result.wrong_energy > result.free_energy
        for result in results
    )
    lines.extend(
        [
            "",
            "Conclusion:",
            (
                "All 8 input patterns passed: the minimum-energy state matches the golden mux behavior, "
                "and forcing the wrong output raises the energy."
                if all_good
                else "At least one pattern failed; inspect the table above."
            ),
            "=" * 88,
        ]
    )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and validate a mux2_1 netlist-to-Ising example.")
    parser.add_argument("--netlist", default=str(THIS_DIR / "mux2_1.v"))
    parser.add_argument("--report", default=str(THIS_DIR / "mux2_1_ising_example.log"))
    parser.add_argument("--summary", default=str(THIS_DIR / "mux2_1_formal_summary.txt"))
    args = parser.parse_args()

    netlist_path = Path(args.netlist).resolve()
    report_path = Path(args.report).resolve()
    summary_path = Path(args.summary).resolve()

    module_name, instances, total_poly, qubit_descriptions, net_connections = build_netlist_polynomial(netlist_path)
    write_report(netlist_path, report_path, module_name, instances, total_poly, qubit_descriptions, net_connections)

    qubit_names = sorted(qubit_descriptions, key=lambda item: int(item[2:-1]))
    named_qubits = get_named_qubits(qubit_descriptions)

    results = [
        analyze_case(total_poly, qubit_names, named_qubits, in1, in2, sel)
        for in1, in2, sel in product([0, 1], repeat=3)
    ]

    summary_lines = build_summary_lines(results, report_path, netlist_path)
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print(report_path)
    print(summary_path)


if __name__ == "__main__":
    main()
