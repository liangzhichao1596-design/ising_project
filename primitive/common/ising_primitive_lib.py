from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from typing import Callable

import pulp


THIS_DIR = Path(__file__).resolve().parent
CACHE_PATH = THIS_DIR / "base_gate_cache.json"
RELATION_CACHE_PATH = THIS_DIR / "relation_cache.json"
SUPPORTED_MANIFEST_PATH = THIS_DIR.parent / "supported_primitives.json"


def bit_to_spin(bit: int) -> int:
    return 1 if int(bit) else -1


def spin_to_bit(spin: int) -> int:
    return 1 if int(spin) > 0 else 0


def parse_verilog_int(value: str | int) -> int:     #输入：可以是字符串 或 整数。输出：一定是 Python 整数 int
    if isinstance(value, int):
        return value
    #如果输入本来就是整数，直接返回，不处理
    text = str(value).strip().replace("_", "")
    # str(value)：
    # 把 value 转成字符串
    # 例如 8'hAC 保持不变，数字 10 变成 "10"

    # .strip()：
    # 去掉字符串前后多余的空白字符
    # 比如 "  8'hAC  " 会变成 "8'hAC"

    # .replace("_", "")：
    # 把字符串里的下划线 _ 全部删除
    # 这样 8'h_ A_C 或 0b1010_0011 这样的写法也能正常解析
    if text.startswith(("0x", "0X")):
        return int(text, 16)
    #如果字符串以 0x 或 0X 开头，表示这是一个十六进制数，使用 int(text, 16) 把它转换成整数
    if text.startswith(("0b", "0B")):
        return int(text, 2)
    #如果字符串以 0b 或 0B 开头，表示这是一个二进制数，使用 int(text, 2) 把它转换成整数
    if "'" in text:
        _, payload = text.split("'", 1)
        base = payload[0].lower()
        digits = payload[1:]
        if base == "h":
            return int(digits, 16)
        if base == "b":
            return int(digits, 2)
        if base == "d":
            return int(digits, 10)
    #如果字符串里包含单引号 '，按照 Verilog 的格式解析
    #     按 ' 分割成两部分
    # 8'hAC → 分割后得到 hAC
    # 取第一个字符当进制类型：h=16，b=2，d=10
    # 剩下的是数字
    if text.startswith(("x\"", "X\"")) and text.endswith("\""):
        return int(text[2:-1], 16)
    #如果字符串以 x" 或 X" 开头，并以 " 结尾，表示这是 Verilog 中的另一种十六进制表示法，使用 int(text[2:-1], 16) 把它转换成整数
    return int(text, 10)


def fraction_to_str(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def sorted_monomial(vars_in_term: tuple[str, ...]) -> tuple[str, ...]:
    def sort_key(item: str) -> tuple[int, object]:
        if item.startswith("q[") and item.endswith("]"):
            return (0, int(item[2:-1]))
        return (1, item)

    return tuple(sorted(vars_in_term, key=sort_key))


@dataclass
class Polynomial:
    terms: dict[tuple[str, ...], Fraction] = field(default_factory=dict)

    def add_term(self, coeff: Fraction | int, vars_in_term: tuple[str, ...]) -> None:
        coeff = Fraction(coeff)
        vars_in_term = sorted_monomial(vars_in_term)
        if coeff == 0:
            return
        self.terms[vars_in_term] = self.terms.get(vars_in_term, Fraction(0)) + coeff
        if self.terms[vars_in_term] == 0:
            del self.terms[vars_in_term]

    def extend(self, other: "Polynomial") -> None:
        for vars_in_term, coeff in other.terms.items():
            self.add_term(coeff, vars_in_term)

    def renamed(self, mapping: dict[str, str]) -> "Polynomial":
        out = Polynomial()
        for vars_in_term, coeff in self.terms.items():
            out.add_term(coeff, tuple(mapping[name] for name in vars_in_term))
        return out

    def evaluate(self, assignment: dict[str, int]) -> Fraction:
        total = Fraction(0)
        for vars_in_term, coeff in self.terms.items():
            term_value = coeff
            for name in vars_in_term:
                term_value *= assignment[name]
            total += term_value
        return total

    def expression_string(self) -> str:
        if not self.terms:
            return "0"

        def sort_key(item: tuple[tuple[str, ...], Fraction]) -> tuple[int, tuple[int, ...]]:
            vars_in_term, _ = item
            encoded = []
            for var in vars_in_term:
                if var.startswith("q[") and var.endswith("]"):
                    encoded.append((0, int(var[2:-1])))
                else:
                    encoded.append((1, var))
            return (len(vars_in_term), tuple(encoded))

        pieces: list[tuple[str, str]] = []
        for vars_in_term, coeff in sorted(self.terms.items(), key=sort_key):
            abs_coeff = abs(coeff)
            sign = "-" if coeff < 0 else "+"
            if not vars_in_term:
                core = fraction_to_str(abs_coeff)
            else:
                var_text = "*".join(vars_in_term)
                core = var_text if abs_coeff == 1 else f"{fraction_to_str(abs_coeff)}*{var_text}"
            pieces.append((sign, core))

        first_sign, first_core = pieces[0]
        out = first_core if first_sign == "+" else f"-{first_core}"
        for sign, core in pieces[1:]:
            out += f" {sign} {core}"
        return out

    def to_jsonable(self) -> list[dict[str, object]]:
        payload = []
        for vars_in_term, coeff in sorted(self.terms.items(), key=lambda item: (len(item[0]), item[0])):
            payload.append(
                {
                    "vars": list(vars_in_term),
                    "num": coeff.numerator,
                    "den": coeff.denominator,
                }
            )
        return payload

    @classmethod
    def from_jsonable(cls, payload: list[dict[str, object]]) -> "Polynomial":
        out = cls()
        for row in payload:
            coeff = Fraction(int(row["num"]), int(row["den"]))
            out.add_term(coeff, tuple(str(item) for item in row["vars"]))
        return out


@dataclass
class RelationModel:
    name: str
    visible_ports: list[str]
    ancilla_ports: list[str]
    polynomial: Polynomial
    notes: list[str] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, object]:
        return {
            "name": self.name,
            "visible_ports": self.visible_ports,
            "ancilla_ports": self.ancilla_ports,
            "polynomial": self.polynomial.to_jsonable(),
            "notes": self.notes,
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, object]) -> "RelationModel":
        return cls(
            name=str(payload["name"]),
            visible_ports=[str(item) for item in payload["visible_ports"]],
            ancilla_ports=[str(item) for item in payload["ancilla_ports"]],
            polynomial=Polynomial.from_jsonable(list(payload["polynomial"])),
            notes=[str(item) for item in payload.get("notes", [])],
        )


def build_logic_relation(
    input_ports: list[str],
    output_ports: list[str],
    function: Callable[[dict[str, int]], dict[str, int]],
) -> list[dict[str, int]]:
    valid_assignments: list[dict[str, int]] = []
    for input_bits in product([0, 1], repeat=len(input_ports)):
        bit_map = {port: bit for port, bit in zip(input_ports, input_bits)}
        out_bits = function(bit_map)
        assignment = {name_: bit_to_spin(value) for name_, value in {**bit_map, **out_bits}.items()}
        valid_assignments.append(assignment)
    return valid_assignments


def enumerate_monomials(var_names: list[str], max_degree: int = 3) -> list[tuple[str, ...]]:
    out = [tuple()]
    for degree in range(1, max_degree + 1):
        out.extend(tuple(combo) for combo in combinations(var_names, degree))
    return out


def assignment_key(ports: list[str], assignment: dict[str, int]) -> tuple[int, ...]:
    return tuple(assignment[port] for port in ports)


def synthesize_relation(
    name: str,
    visible_ports: list[str],
    valid_assignments: list[dict[str, int]],
    max_ancilla: int = 1,
    scale_candidates: tuple[int, ...] = (1, 2),
    coeff_bounds: tuple[int, ...] = (3, 4, 6, 8),
    gap: int = 1,
    time_limit: int = 30,
) -> RelationModel:
    valid_keys = {assignment_key(visible_ports, item) for item in valid_assignments}

    for ancilla_count in range(max_ancilla + 1):
        ancilla_ports = [f"a{i}" for i in range(ancilla_count)]
        local_ports = visible_ports + ancilla_ports
        monomials = enumerate_monomials(local_ports, max_degree=3)
        ancilla_choices = list(product([-1, 1], repeat=ancilla_count))

        full_assignments: list[dict[str, int]] = []
        for visible_bits in product([-1, 1], repeat=len(visible_ports)):
            visible_map = dict(zip(visible_ports, visible_bits))
            for anc_bits in ancilla_choices or [tuple()]:
                row = dict(visible_map)
                row.update(dict(zip(ancilla_ports, anc_bits)))
                full_assignments.append(row)

        monomial_values: dict[tuple[tuple[int, ...], tuple[int, ...]], dict[tuple[str, ...], int]] = {}
        for row in full_assignments:
            vis_key = assignment_key(visible_ports, row)
            anc_key = assignment_key(ancilla_ports, row)
            values = {}
            for monomial in monomials:
                if not monomial:
                    values[monomial] = 1
                else:
                    acc = 1
                    for name_ in monomial:
                        acc *= row[name_]
                    values[monomial] = acc
            monomial_values[(vis_key, anc_key)] = values

        for scale in scale_candidates:
            for coeff_bound in coeff_bounds:
                problem = pulp.LpProblem(f"{name}_ising", pulp.LpMinimize)
                coeff_vars = {}
                abs_vars = {}
                for monomial in monomials:
                    tag = "const" if not monomial else "_".join(monomial)
                    coeff = pulp.LpVariable(
                        f"c_{tag}",
                        lowBound=-coeff_bound * scale,
                        upBound=coeff_bound * scale,
                        cat="Integer",
                    )
                    coeff_vars[monomial] = coeff
                    abs_var = pulp.LpVariable(f"abs_{tag}", lowBound=0, cat="Integer")
                    abs_vars[monomial] = abs_var
                    problem += abs_var >= coeff
                    problem += abs_var >= -coeff

                problem += pulp.lpSum(abs_vars.values())

                big_m = 4 * coeff_bound * scale * max(1, len(monomials))
                for vis_key in product([-1, 1], repeat=len(visible_ports)):
                    for anc_key in ancilla_choices or [tuple()]:
                        energy = pulp.lpSum(
                            coeff_vars[monomial] * monomial_values[(vis_key, anc_key)][monomial]
                            for monomial in monomials
                        )
                        if vis_key in valid_keys:
                            problem += energy >= 0
                        else:
                            problem += energy >= gap * scale

                for vis_key in valid_keys:
                    witnesses = []
                    for anc_key in ancilla_choices or [tuple()]:
                        witness = pulp.LpVariable(
                            f"w_{'_'.join(map(str, vis_key))}_{'_'.join(map(str, anc_key)) or 'na'}",
                            cat="Binary",
                        )
                        energy = pulp.lpSum(
                            coeff_vars[monomial] * monomial_values[(vis_key, anc_key)][monomial]
                            for monomial in monomials
                        )
                        problem += energy <= big_m * (1 - witness)
                        witnesses.append(witness)
                    problem += pulp.lpSum(witnesses) == 1

                solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit)
                result = problem.solve(solver)
                if pulp.LpStatus[result] != "Optimal":
                    continue

                polynomial = Polynomial()
                for monomial in monomials:
                    raw_value = int(round(pulp.value(coeff_vars[monomial])))
                    if raw_value:
                        polynomial.add_term(Fraction(raw_value, scale), monomial)

                if not polynomial.terms:
                    continue

                return RelationModel(
                    name=name,
                    visible_ports=visible_ports,
                    ancilla_ports=ancilla_ports,
                    polynomial=polynomial,
                    notes=[
                        f"MILP-synthesized with ancilla_count={ancilla_count}",
                        f"integer_scale=1/{scale}",
                        f"coefficient_bound={coeff_bound}",
                    ],
                )

    raise RuntimeError(f"Unable to synthesize a cubic Ising relation for {name}")


def make_base_relations() -> dict[str, RelationModel]:
    relations: dict[str, RelationModel] = {}
    relations["BUF"] = synthesize_relation(
        name="BUF",
        visible_ports=["a", "x"],
        valid_assignments=build_logic_relation(["a"], ["x"], lambda bits: {"x": bits["a"]}),
        max_ancilla=0,
    )
    relations["NOT"] = synthesize_relation(
        name="NOT",
        visible_ports=["a", "x"],
        valid_assignments=build_logic_relation(["a"], ["x"], lambda bits: {"x": 1 - bits["a"]}),
        max_ancilla=0,
    )
    relations["CONST0"] = synthesize_relation("CONST0", ["x"], [{"x": -1}], max_ancilla=0)
    relations["CONST1"] = synthesize_relation("CONST1", ["x"], [{"x": 1}], max_ancilla=0)
    relations["OR2"] = synthesize_relation(
        name="OR2",
        visible_ports=["a", "b", "x"],
        valid_assignments=build_logic_relation(["a", "b"], ["x"], lambda bits: {"x": bits["a"] | bits["b"]}),
        max_ancilla=0,
    )
    relations["XOR2"] = synthesize_relation(
        name="XOR2",
        visible_ports=["a", "b", "x"],
        valid_assignments=build_logic_relation(["a", "b"], ["x"], lambda bits: {"x": bits["a"] ^ bits["b"]}),
        max_ancilla=0,
    )
    relations["MUX2"] = synthesize_relation(
        name="MUX2",
        visible_ports=["s", "i0", "i1", "x"],
        valid_assignments=build_logic_relation(
            ["s", "i0", "i1"],
            ["x"],
            lambda bits: {"x": bits["i0"] if bits["s"] == 0 else bits["i1"]},
        ),
        max_ancilla=0,
    )
    return relations


def load_base_relations() -> dict[str, RelationModel]:
    if CACHE_PATH.exists():
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return {name: RelationModel.from_jsonable(data) for name, data in payload.items()}
    relations = make_base_relations()
    CACHE_PATH.write_text(
        json.dumps({name: model.to_jsonable() for name, model in relations.items()}, indent=2),
        encoding="utf-8",
    )
    return relations


def load_relation_cache() -> dict[str, dict[str, object]]:
    if RELATION_CACHE_PATH.exists():
        try:
            return json.loads(RELATION_CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_relation_cache(payload: dict[str, dict[str, object]]) -> None:
    RELATION_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def relation_from_cache(cache_key: str) -> RelationModel | None:
    payload = load_relation_cache()
    item = payload.get(cache_key)
    if item is None:
        return None
    return RelationModel.from_jsonable(item)


def relation_to_cache(cache_key: str, model: RelationModel) -> None:
    payload = load_relation_cache()
    payload[cache_key] = model.to_jsonable()
    save_relation_cache(payload)


@dataclass
class PrimitiveDefinition:
    name: str
    input_ports: list[str]
    output_ports: list[str]
    build: Callable[["PrimitiveBuilder", dict[str, int]], None]
    default_params: dict[str, int] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    summary: str = ""


class PrimitiveBuilder:
    def __init__(self, primitive_name: str):
        self.primitive_name = primitive_name     #primitive_name：原语名称，例如 LUT3
        self.q_count = 0     #q_count：量子比特计数器，用于生成唯一的量子比特名称
        self.port_to_q: dict[str, str] = {}   #port_to_q：端口到量子比特的映射
        self.var_map: dict[str, str] = {}   #var_map：量子比特名称到描述的映射
        self.polynomial = Polynomial()   #polynomial：Ising 模型的多项式表示
        self.base_relations = load_base_relations() #base_relations：预定义的基本关系模型，例如 BUF、NOT、OR2、XOR2、MUX2 等
        self.const_cache: dict[int, str] = {}   #const_cache：常量量子比特缓存，用于存储已构建的常量量子比特
        self.internal_counter = 0   #internal_counter：内部量子比特计数器，用于生成唯一的内部量子比特名称

    def add_input(self, port: str) -> str:
        return self._add_qubit(port, f"[INPUT] {port}")
    #add_input：添加输入端口，返回对应的量子比特名称

    def add_output(self, port: str) -> str:
        return self._add_qubit(port, f"[OUTPUT] {port}")
    #add_output：添加输出端口，返回对应的量子比特名称

    def add_internal(self, name: str) -> str:
        self.internal_counter += 1
        return self._add_qubit(f"__internal__{self.internal_counter}", f"[ANCILLA] {name}")
    #add_internal：添加内部量子比特，返回对应的量子比特名称

    def _add_qubit(self, port: str, description: str) -> str:
        q_name = f"q[{self.q_count}]"
        self.q_count += 1
        self.port_to_q[port] = q_name
        self.var_map[q_name] = description
        return q_name
    #_add_qubit：添加量子比特，返回对应的量子比特名称

    def q(self, port: str) -> str:
        return self.port_to_q[port]
    #q：获取端口对应的量子比特名称

    def add_relation(self, relation_name: str, bindings: dict[str, str], label: str) -> list[str]:
        model = self.base_relations[relation_name]
        return self.add_model(model, bindings, label)
    #add_relation：添加关系模型，返回对应的量子量子比特名称列表

    def add_model(self, model: RelationModel, bindings: dict[str, str], label: str) -> list[str]:
        rename_map = dict(bindings)
        ancilla_qubits: list[str] = []
        for ancilla_name in model.ancilla_ports:
            q_name = self.add_internal(f"{label}:{model.name}:{ancilla_name}")
            rename_map[ancilla_name] = q_name
            ancilla_qubits.append(q_name)
        self.polynomial.extend(model.polynomial.renamed(rename_map))
        return ancilla_qubits
    #add_model：添加关系模型，返回对应的量子量子比特名称列表

    def const_qubit(self, bit: int) -> str:
        if bit not in self.const_cache:
            q_name = self.add_internal(f"{self.primitive_name}:CONST{bit}")
            self.add_relation(f"CONST{bit}", {"x": q_name}, f"{self.primitive_name}_CONST{bit}")
            self.const_cache[bit] = q_name
        return self.const_cache[bit]
    #const_qubit：添加常量量子比特，返回对应的量子比特名称


def default_lut_init(width: int) -> int:
    return 1 << ((1 << width) - 1)


def default_lut62_init() -> int:
    return (1 << 31) | (1 << 63)


def shannon_build(
    builder: PrimitiveBuilder,
    input_ports: list[str],
    truth_bits: tuple[int, ...],
    target_q: str,
    label: str,
) -> str:
    memo: dict[tuple[tuple[int, ...], int], str] = {}
    variable_order = list(reversed(input_ports))

    def recurse(bits: tuple[int, ...], depth: int) -> str:
        if all(bit == 0 for bit in bits):
            return builder.const_qubit(0)
        if all(bit == 1 for bit in bits):
            return builder.const_qubit(1)
        key = (bits, depth)
        if key in memo:
            return memo[key]

        selector = variable_order[depth]
        half = len(bits) // 2
        low_q = recurse(bits[:half], depth + 1)
        high_q = recurse(bits[half:], depth + 1)
        if low_q == high_q:
            memo[key] = low_q
            return low_q

        node_q = target_q if depth == 0 else builder.add_internal(f"{label}:node{depth}:{selector}")
        builder.add_relation(
            "MUX2",
            {"s": builder.q(selector), "i0": low_q, "i1": high_q, "x": node_q},
            f"{label}:{selector}",
        )
        memo[key] = node_q
        return node_q

    return recurse(truth_bits, 0)


def build_lut_primitive(builder: PrimitiveBuilder, params: dict[str, int], width: int, output_port: str) -> None:
    init_value = int(params["init"])
    visible_ports = [f"I{i}" for i in range(width)] + [output_port]
    valid_assignments = build_logic_relation(
        [f"I{i}" for i in range(width)],
        [output_port],
        lambda bits: {output_port: (init_value >> sum(bits[f"I{i}"] << i for i in range(width))) & 1},
    )
    cache_key = f"{builder.primitive_name}:{output_port}:init={init_value}"
    model = relation_from_cache(cache_key)
    if model is None:
        try:
            max_ancilla = 0 if width <= 3 else 1
            model = synthesize_relation(
                name=f"{builder.primitive_name}_{output_port}",
                visible_ports=visible_ports,
                valid_assignments=valid_assignments,
                max_ancilla=max_ancilla,
            )
            model.notes.append("direct visible-port solve (minimal ancilla search before decomposition)")
        except RuntimeError:
            truth_bits = tuple((init_value >> idx) & 1 for idx in range(1 << width))
            out_q = builder.q(output_port)
            produced_q = shannon_build(builder, [f"I{i}" for i in range(width)], truth_bits, out_q, f"{builder.primitive_name}:{output_port}")
            if produced_q != out_q:
                builder.add_relation("BUF", {"a": produced_q, "x": out_q}, f"{builder.primitive_name}:{output_port}:buf")
            return
        relation_to_cache(cache_key, model)

    bindings = {port: builder.q(port) for port in visible_ports}
    builder.add_model(model, bindings, f"{builder.primitive_name}:{output_port}:direct")


def build_lut62(builder: PrimitiveBuilder, params: dict[str, int]) -> None:
    init_value = int(params["init"])
    input_ports = [f"I{i}" for i in range(6)]
    visible_ports = input_ports + ["O5", "O6"]
    valid_assignments = []
    for input_bits in product([0, 1], repeat=6):
        ins = dict(zip(input_ports, input_bits))
        idx6 = sum(ins[f"I{i}"] << i for i in range(6))
        idx5 = sum(ins[f"I{i}"] << i for i in range(5))
        valid_assignments.append(
            {
                **{name: bit_to_spin(value) for name, value in ins.items()},
                "O5": bit_to_spin((init_value >> idx5) & 1),
                "O6": bit_to_spin((init_value >> idx6) & 1),
            }
        )

    cache_key = f"{builder.primitive_name}:init={init_value}"
    model = relation_from_cache(cache_key)
    if model is None:
        try:
            model = synthesize_relation(
                name=builder.primitive_name,
                visible_ports=visible_ports,
                valid_assignments=valid_assignments,
                max_ancilla=1,
            )
            model.notes.append("direct visible-port solve (minimal ancilla search before decomposition)")
            relation_to_cache(cache_key, model)
        except RuntimeError:
            o6_bits = tuple((init_value >> idx) & 1 for idx in range(64))
            o5_bits = tuple((init_value >> idx) & 1 for idx in range(32))
            out_o6 = builder.q("O6")
            produced_o6 = shannon_build(builder, [f"I{i}" for i in range(6)], o6_bits, out_o6, f"{builder.primitive_name}:O6")
            if produced_o6 != out_o6:
                builder.add_relation("BUF", {"a": produced_o6, "x": out_o6}, f"{builder.primitive_name}:O6:buf")
            out_o5 = builder.q("O5")
            produced_o5 = shannon_build(builder, [f"I{i}" for i in range(5)], o5_bits, out_o5, f"{builder.primitive_name}:O5")
            if produced_o5 != out_o5:
                builder.add_relation("BUF", {"a": produced_o5, "x": out_o5}, f"{builder.primitive_name}:O5:buf")
            return

    bindings = {port: builder.q(port) for port in visible_ports}
    builder.add_model(model, bindings, f"{builder.primitive_name}:direct")


def build_buf_family(input_port: str, output_port: str) -> Callable[[PrimitiveBuilder, dict[str, int]], None]:
    #Callable[[PrimitiveBuilder, dict[str, int]], None]：返回一个可调用对象，该对象接收 PrimitiveBuilder 和参数字典，返回 None
    def _builder(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
        builder.add_relation("BUF", {"a": builder.q(input_port), "x": builder.q(output_port)}, f"{builder.primitive_name}:{output_port}")
        #"a" 绑定到 builder.q(input_port)（输入端口的量子比特）
        #"x" 绑定到 builder.q(output_port)（输出端口的量子比特）
    return _builder


def build_mux_family(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation(
        "MUX2",
        {"s": builder.q("S"), "i0": builder.q("I0"), "i1": builder.q("I1"), "x": builder.q("O")},
        f"{builder.primitive_name}:MUX",
    )


def build_ce_zero(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation(
        "MUX2",
        {"s": builder.q("CE"), "i0": builder.const_qubit(0), "i1": builder.q("I"), "x": builder.q("O")},
        f"{builder.primitive_name}:CE",
    )


def build_ce_one(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation(
        "MUX2",
        {"s": builder.q("CE"), "i0": builder.const_qubit(1), "i1": builder.q("I"), "x": builder.q("O")},
        f"{builder.primitive_name}:CE",
    )


def build_pulldown(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation("CONST0", {"x": builder.q("O")}, f"{builder.primitive_name}:O")


def build_pullup(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation("CONST1", {"x": builder.q("O")}, f"{builder.primitive_name}:O")


def build_ibufds(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation("NOT", {"a": builder.q("I"), "x": builder.q("IB")}, f"{builder.primitive_name}:diff")
    builder.add_relation("BUF", {"a": builder.q("I"), "x": builder.q("O")}, f"{builder.primitive_name}:buf")


def build_ibufds_diff_out(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation("NOT", {"a": builder.q("I"), "x": builder.q("IB")}, f"{builder.primitive_name}:diff")
    builder.add_relation("BUF", {"a": builder.q("I"), "x": builder.q("O")}, f"{builder.primitive_name}:obuf")
    builder.add_relation("BUF", {"a": builder.q("IB"), "x": builder.q("OB")}, f"{builder.primitive_name}:obbuf")


def build_obufds(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    builder.add_relation("BUF", {"a": builder.q("I"), "x": builder.q("O")}, f"{builder.primitive_name}:obuf")
    builder.add_relation("NOT", {"a": builder.q("I"), "x": builder.q("OB")}, f"{builder.primitive_name}:ob")


def build_carry4(builder: PrimitiveBuilder, _params: dict[str, int]) -> None:
    cin0 = builder.add_internal(f"{builder.primitive_name}:carry_in0")
    builder.add_relation("OR2", {"a": builder.q("CI"), "b": builder.q("CYINIT"), "x": cin0}, f"{builder.primitive_name}:cin0")

    carry_in = cin0
    for idx in range(4):
        co_q = builder.q(f"CO{idx}")
        o_q = builder.q(f"O{idx}")
        s_q = builder.q(f"S{idx}")
        di_q = builder.q(f"DI{idx}")
        builder.add_relation("MUX2", {"s": s_q, "i0": di_q, "i1": carry_in, "x": co_q}, f"{builder.primitive_name}:co{idx}")
        builder.add_relation("XOR2", {"a": s_q, "b": carry_in, "x": o_q}, f"{builder.primitive_name}:o{idx}")
        carry_in = co_q


def direct_only_builder(max_ancilla: int, fallback: Callable[[PrimitiveBuilder, dict[str, int]], None] | None = None):
    def _builder(builder: PrimitiveBuilder, params: dict[str, int]) -> None:
        definition = PRIMITIVES[builder.primitive_name]
        build_via_direct_truth_table(builder, definition, params, max_ancilla=max_ancilla, fallback=fallback)

    return _builder


def direct_cache_key(definition: PrimitiveDefinition, params: dict[str, int]) -> str:
    if not params:
        return f"{definition.name}:direct"
    return f"{definition.name}:direct:" + ",".join(f"{key}={params[key]}" for key in sorted(params))


def build_via_direct_truth_table(
    builder: PrimitiveBuilder,
    definition: PrimitiveDefinition,
    params: dict[str, int],
    max_ancilla: int,
    fallback: Callable[[PrimitiveBuilder, dict[str, int]], None] | None = None,
) -> None:
    visible_ports = definition.input_ports + definition.output_ports
    valid_assignments = [
        {port: bit_to_spin(row[port]) for port in visible_ports}
        for row in truth_table_rows(definition, params)
    ]
    cache_key = direct_cache_key(definition, params)
    model = relation_from_cache(cache_key)
    if model is None:
        try:
            model = synthesize_relation(
                name=definition.name,
                visible_ports=visible_ports,
                valid_assignments=valid_assignments,
                max_ancilla=max_ancilla,
            )
            model.notes.append("direct visible-port solve (minimal ancilla search)")
            relation_to_cache(cache_key, model)
        except RuntimeError:
            if fallback is None:
                raise
            fallback(builder, params)
            return
    bindings = {port: builder.q(port) for port in visible_ports}
    builder.add_model(model, bindings, f"{builder.primitive_name}:direct")


PRIMITIVES: dict[str, PrimitiveDefinition] = {
    "BUFG": PrimitiveDefinition("BUFG", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="Global clock simple buffer."),
    "BUFGCE": PrimitiveDefinition(
        "BUFGCE",
        ["I", "CE"],
        ["O"],
        direct_only_builder(0, build_ce_zero),
        summary="Clock-enable buffer, modeled as O=0 when CE=0 else O=I.",
    ),
    "BUFGCE_1": PrimitiveDefinition(
        "BUFGCE_1",
        ["I", "CE"],
        ["O"],
        direct_only_builder(0, build_ce_one),
        summary="Clock-enable buffer, modeled as O=1 when CE=0 else O=I.",
    ),
    "BUFGMUX": PrimitiveDefinition("BUFGMUX", ["I0", "I1", "S"], ["O"], direct_only_builder(0, build_mux_family), summary="2:1 clock mux."),
    "BUFGMUX_1": PrimitiveDefinition(
        "BUFGMUX_1",
        ["I0", "I1", "S"],
        ["O"],
        direct_only_builder(0, build_mux_family),
        assumptions=["Only steady-state mux behavior is modeled; clock-switch transient output-state-1 behavior is ignored."],
        summary="2:1 clock mux, steady-state behavior only.",
    ),
    "BUFGMUX_CTRL": PrimitiveDefinition("BUFGMUX_CTRL", ["I0", "I1", "S"], ["O"], direct_only_builder(0, build_mux_family), summary="2:1 global clock mux."),
    "BUFH": PrimitiveDefinition("BUFH", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="Regional clock buffer."),
    "BUFIO": PrimitiveDefinition("BUFIO", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="I/O clock buffer."),
    "BUFMR": PrimitiveDefinition("BUFMR", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="Multi-region clock buffer."),
    "CARRY4": PrimitiveDefinition(
        "CARRY4",
        ["CI", "CYINIT", "DI0", "DI1", "DI2", "DI3", "S0", "S1", "S2", "S3"],
        ["CO0", "CO1", "CO2", "CO3", "O0", "O1", "O2", "O3"],
        build_carry4,
        assumptions=["The initial carry is modeled as CI OR CYINIT, which matches the steady-state logical carry seed."],
        summary="Fast carry chain, built compositionally from verified cubic OR/MUX/XOR constraints.",
    ),
    "IBUF": PrimitiveDefinition("IBUF", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="Input buffer."),
    "IBUFDS": PrimitiveDefinition(
        "IBUFDS",
        ["I", "IB"],
        ["O"],
        direct_only_builder(0, build_ibufds),
        assumptions=["Ideal differential-input assumption: IB = NOT(I). The UG953 'No Change' common-mode states are excluded."],
        summary="Differential input buffer under ideal complementary drive.",
    ),
    "IBUFDS_DIFF_OUT": PrimitiveDefinition(
        "IBUFDS_DIFF_OUT",
        ["I", "IB"],
        ["O", "OB"],
        direct_only_builder(0, build_ibufds_diff_out),
        assumptions=["Ideal differential-input assumption: IB = NOT(I). The UG953 'No Change' common-mode states are excluded."],
        summary="Differential input buffer with both phases exposed internally.",
    ),
    "LUT1": PrimitiveDefinition(
        "LUT1",
        ["I0"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 1, "O"),
        default_params={"init": default_lut_init(1)},
        summary="Parameterized 1-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT2": PrimitiveDefinition(
        "LUT2",
        ["I0", "I1"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 2, "O"),
        default_params={"init": default_lut_init(2)},
        summary="Parameterized 2-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT3": PrimitiveDefinition(
        "LUT3",
        ["I0", "I1", "I2"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 3, "O"),
        default_params={"init": default_lut_init(3)},
        summary="Parameterized 3-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT4": PrimitiveDefinition(
        "LUT4",
        ["I0", "I1", "I2", "I3"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 4, "O"),
        default_params={"init": default_lut_init(4)},
        summary="Parameterized 4-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT5": PrimitiveDefinition(
        "LUT5",
        ["I0", "I1", "I2", "I3", "I4"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 5, "O"),
        default_params={"init": default_lut_init(5)},
        summary="Parameterized 5-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT6": PrimitiveDefinition(
        "LUT6",
        ["I0", "I1", "I2", "I3", "I4", "I5"],
        ["O"],
        lambda builder, params: build_lut_primitive(builder, params, 6, "O"),
        default_params={"init": default_lut_init(6)},
        summary="Parameterized 6-input LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "LUT6_2": PrimitiveDefinition(
        "LUT6_2",
        ["I0", "I1", "I2", "I3", "I4", "I5"],
        ["O5", "O6"],
        build_lut62,
        default_params={"init": default_lut62_init()},
        summary="Parameterized dual-output LUT. Prefer direct cubic solve with minimal ancilla, fallback to decomposition.",
    ),
    "MUXF7": PrimitiveDefinition("MUXF7", ["I0", "I1", "S"], ["O"], direct_only_builder(0, build_mux_family), summary="2:1 LUT mux."),
    "MUXF8": PrimitiveDefinition("MUXF8", ["I0", "I1", "S"], ["O"], direct_only_builder(0, build_mux_family), summary="2:1 LUT mux."),
    "OBUF": PrimitiveDefinition("OBUF", ["I"], ["O"], direct_only_builder(0, build_buf_family("I", "O")), summary="Output buffer."),
    "OBUFDS": PrimitiveDefinition("OBUFDS", ["I"], ["O", "OB"], direct_only_builder(0, build_obufds), summary="Differential output buffer."),
    "PULLDOWN": PrimitiveDefinition("PULLDOWN", [], ["O"], direct_only_builder(0, build_pulldown), summary="Weak pull-down source."),
    "PULLUP": PrimitiveDefinition("PULLUP", [], ["O"], direct_only_builder(0, build_pullup), summary="Weak pull-up source."),
}


def build_primitive(primitive_name: str, params: dict[str, int] | None = None) -> tuple[PrimitiveBuilder, PrimitiveDefinition, dict[str, int]]:
    definition = PRIMITIVES[primitive_name]
    resolved_params = dict(definition.default_params)
    if params:
        resolved_params.update(params)

    builder = PrimitiveBuilder(primitive_name)
    for port in definition.input_ports:
        builder.add_input(port)
    for port in definition.output_ports:
        builder.add_output(port)
    definition.build(builder, resolved_params)
    return builder, definition, resolved_params


def format_params(params: dict[str, int]) -> list[str]:
    return [f"{key} = 0x{params[key]:X} ({params[key]})" for key in sorted(params)]


def truth_table_rows(definition: PrimitiveDefinition, params: dict[str, int]) -> list[dict[str, int]]:
    name = definition.name

    def rows_from_function(func: Callable[[dict[str, int]], dict[str, int]]) -> list[dict[str, int]]:
        rows = []
        for input_bits in product([0, 1], repeat=len(definition.input_ports)):
            ins = dict(zip(definition.input_ports, input_bits))
            outs = func(ins)
            rows.append({**ins, **outs})
        return rows

    if name in {"BUFG", "BUFH", "BUFIO", "BUFMR", "IBUF", "OBUF"}:
        return rows_from_function(lambda ins: {"O": ins["I"]})
    if name == "BUFGCE":
        return rows_from_function(lambda ins: {"O": ins["I"] if ins["CE"] else 0})
    if name == "BUFGCE_1":
        return rows_from_function(lambda ins: {"O": ins["I"] if ins["CE"] else 1})
    if name in {"BUFGMUX", "BUFGMUX_1", "BUFGMUX_CTRL", "MUXF7", "MUXF8"}:
        return rows_from_function(lambda ins: {"O": ins["I0"] if ins["S"] == 0 else ins["I1"]})
    if name == "PULLDOWN":
        return [{"O": 0}]
    if name == "PULLUP":
        return [{"O": 1}]
    if name == "OBUFDS":
        return rows_from_function(lambda ins: {"O": ins["I"], "OB": 1 - ins["I"]})
    if name == "IBUFDS":
        return [
            {"I": 0, "IB": 1, "O": 0},
            {"I": 1, "IB": 0, "O": 1},
        ]
    if name == "IBUFDS_DIFF_OUT":
        return [
            {"I": 0, "IB": 1, "O": 0, "OB": 1},
            {"I": 1, "IB": 0, "O": 1, "OB": 0},
        ]
    if name.startswith("LUT") and name != "LUT6_2":
        width = len(definition.input_ports)
        init_value = int(params["init"])
        rows = []
        for input_bits in product([0, 1], repeat=width):
            index = sum(bit << idx for idx, bit in enumerate(input_bits))
            rows.append({**dict(zip(definition.input_ports, input_bits)), "O": (init_value >> index) & 1})
        return rows
    if name == "LUT6_2":
        init_value = int(params["init"])
        rows = []
        for input_bits in product([0, 1], repeat=6):
            index6 = sum(bit << idx for idx, bit in enumerate(input_bits))
            index5 = sum(bit << idx for idx, bit in enumerate(input_bits[:5]))
            rows.append(
                {
                    **dict(zip(definition.input_ports, input_bits)),
                    "O5": (init_value >> index5) & 1,
                    "O6": (init_value >> index6) & 1,
                }
            )
        return rows
    if name == "CARRY4":
        rows = []
        for bits in product([0, 1], repeat=len(definition.input_ports)):
            ins = dict(zip(definition.input_ports, bits))
            carry = 1 if ins["CI"] or ins["CYINIT"] else 0
            outs: dict[str, int] = {}
            for idx in range(4):
                s = ins[f"S{idx}"]
                di = ins[f"DI{idx}"]
                co = carry if s else di
                o = s ^ carry
                outs[f"CO{idx}"] = co
                outs[f"O{idx}"] = o
                carry = co
            rows.append({**ins, **outs})
        return rows
    raise ValueError(f"No truth-table generator for {name}")


def format_truth_table(definition: PrimitiveDefinition, params: dict[str, int]) -> list[str]:
    headers = definition.input_ports + definition.output_ports
    rows = truth_table_rows(definition, params)
    if not rows:
        return ["<empty>"]
    widths = {header: max(len(header), 1) for header in headers}
    header_line = " | ".join(header.ljust(widths[header]) for header in headers)
    sep_line = "-+-".join("-" * widths[header] for header in headers)
    row_lines = [" | ".join(str(row[header]).ljust(widths[header]) for header in headers) for row in rows]
    return [header_line, sep_line, *row_lines]


def q_order(builder: PrimitiveBuilder) -> list[str]:
    return sorted(builder.var_map, key=lambda item: int(item[2:-1]))


def enumerate_qubit_assignments(builder: PrimitiveBuilder):
    ordered_qs = q_order(builder)
    for spins in product([-1, 1], repeat=len(ordered_qs)):
        yield ordered_qs, dict(zip(ordered_qs, spins))


def visible_headers(definition: PrimitiveDefinition) -> list[str]:
    return definition.input_ports + definition.output_ports


def visible_spin_key(builder: PrimitiveBuilder, definition: PrimitiveDefinition, assignment: dict[str, int]) -> tuple[int, ...]:
    return tuple(assignment[builder.q(port)] for port in visible_headers(definition))


def valid_visible_spin_keys(definition: PrimitiveDefinition, params: dict[str, int]) -> set[tuple[int, ...]]:
    out = set()
    for row in truth_table_rows(definition, params):
        out.add(tuple(bit_to_spin(row[port]) for port in visible_headers(definition)))
    return out


def collect_visible_min_energies(
    builder: PrimitiveBuilder,
    definition: PrimitiveDefinition,
    params: dict[str, int],
) -> dict[tuple[int, ...], Fraction]:
    visible_min: dict[tuple[int, ...], Fraction] = {}
    for _, assignment in enumerate_qubit_assignments(builder):
        key = visible_spin_key(builder, definition, assignment)
        energy = builder.polynomial.evaluate(assignment)
        current = visible_min.get(key)
        if current is None or energy < current:
            visible_min[key] = energy
    return visible_min


def verification_summary_lines(
    builder: PrimitiveBuilder,
    definition: PrimitiveDefinition,
    params: dict[str, int],
    visible_min: dict[tuple[int, ...], Fraction],
) -> list[str]:
    valid_keys = valid_visible_spin_keys(definition, params)
    all_visible = list(product([-1, 1], repeat=len(visible_headers(definition))))
    valid_ok = all(visible_min[key] == 0 for key in all_visible if key in valid_keys)
    invalid_ok = all(visible_min[key] > 0 for key in all_visible if key not in valid_keys)
    return [
        f"valid_visible_assignments = {sum(1 for key in all_visible if key in valid_keys)}",
        f"invalid_visible_assignments = {sum(1 for key in all_visible if key not in valid_keys)}",
        f"all_valid_states_have_min_energy_0 = {valid_ok}",
        f"all_invalid_states_have_min_energy_gt_0 = {invalid_ok}",
        f"verification_passed = {valid_ok and invalid_ok}",
    ]


def write_log(
    primitive_name: str,
    output_dir: Path,
    builder: PrimitiveBuilder,
    definition: PrimitiveDefinition,
    params: dict[str, int],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{primitive_name}.log"
    ordered_qs = q_order(builder)
    visible_min = collect_visible_min_energies(builder, definition, params)
    valid_visible = valid_visible_spin_keys(definition, params)

    def write_lines(handle, lines: list[str]) -> None:
        handle.write("\n".join(lines))
        handle.write("\n")

    with log_path.open("w", encoding="utf-8") as handle:
        write_lines(
            handle,
            [
                "=" * 88,
                f"Primitive: {primitive_name}",
                "=" * 88,
                f"Summary: {definition.summary}",
                "",
                "[1] Ising Function",
                builder.polynomial.expression_string(),
                "",
                "[2] Qubit Count",
                str(builder.q_count),
                "",
                "[3] Qubit <-> Primitive Port Mapping",
                *[f"{q_name} : {description}" for q_name, description in sorted(builder.var_map.items(), key=lambda item: int(item[0][2:-1]))],
                "",
                "[4] Primitive Truth Table",
                *format_truth_table(definition, params),
                "",
                "[5] Ising Truth Table (All Qubit Combinations)",
            ],
        )

        headers = ordered_qs + ["energy", "logic_valid", "visible_min_energy", "is_visible_ground"]
        widths = {header: max(len(header), 1) for header in headers}
        header_line = " | ".join(header.ljust(widths[header]) for header in headers)
        sep_line = "-+-".join("-" * widths[header] for header in headers)
        write_lines(handle, [header_line, sep_line])

        for _, assignment in enumerate_qubit_assignments(builder):
            energy = builder.polynomial.evaluate(assignment)
            visible_key = visible_spin_key(builder, definition, assignment)
            logic_valid = 1 if visible_key in valid_visible else 0
            visible_ground = 1 if energy == visible_min[visible_key] else 0
            row = {q_name: assignment[q_name] for q_name in ordered_qs}
            row["energy"] = fraction_to_str(energy)
            row["logic_valid"] = logic_valid
            row["visible_min_energy"] = fraction_to_str(visible_min[visible_key])
            row["is_visible_ground"] = visible_ground
            handle.write(" | ".join(str(row[header]).ljust(widths[header]) for header in headers))
            handle.write("\n")

        write_lines(handle, ["", "[6] Minimum Energy", "0"])

        if params:
            write_lines(handle, ["", "[7] Parameters", *format_params(params)])

        if definition.assumptions:
            write_lines(handle, ["", "[8] Assumptions", *definition.assumptions])

        write_lines(handle, ["", "[9] Verification Summary", *verification_summary_lines(builder, definition, params, visible_min)])

        base_notes = [f"{base_name}: {', '.join(model.notes)}" for base_name, model in sorted(builder.base_relations.items())]
        write_lines(handle, ["", "[10] Base Relation Synthesis Notes", *base_notes, ""])

    return log_path



# run_named_primitive
# 读取对应原语（primitive）的定义
# 解析可选参数，比如 --init
# 构建该原语对应的 Ising 模型
# 把结果写成日志文件并返回文件路径
#输入格式：run_named_primitive("LUT3", Path("./output"))
def run_named_primitive(primitive_name: str, output_dir: Path, argv: list[str] | None = None) -> Path:
    definition = PRIMITIVES[primitive_name]
    # 从全局字典 PRIMITIVES 中取出这个 primitive 的定义，例如 LUT3 的输入端口、输出端口、构建函数、默认 init 值等
    parser = argparse.ArgumentParser(description=f"Generate Ising report for {primitive_name}")
    if "init" in definition.default_params:
        parser.add_argument("--init", default=f"0x{definition.default_params['init']:X}")
    args = parser.parse_args(argv)

    params: dict[str, int] = {}
    if hasattr(args, "init"):
        params["init"] = parse_verilog_int(args.init)
    #检查 args 对象是否有 init 属性，调用 parse_verilog_int 函数，将用户输入的 init 值（可能是字符串，如 "0xA5"）解析为整数，赋值给 params["init"] 键
    builder, definition, resolved_params = build_primitive(primitive_name, params)
    #调用 build_primitive 函数，构建 Ising 模型：Builder 对象包含了原语的 qubit 定义、约束关系等；Definition 是原语的定义对象；resolved_params 是解析后的参数字典
    return write_log(primitive_name, output_dir, builder, definition, resolved_params)


def unsupported_reason(title: str) -> str:
    tri_state = {
        "IOBUF",
        "IOBUF_DCIEN",
        "IOBUF_INTERMDISABLE",
        "IOBUFDS",
        "IOBUFDS_DCIEN",
        "IOBUFDS_DIFF_OUT",
        "IOBUFDS_DIFF_OUT_DCIEN",
        "IOBUFDS_DIFF_OUT_INTERMDISABLE",
        "IOBUFDS_INTERMDISABLE",
        "OBUFT",
        "OBUFTDS",
    }
    sequential = {"FDCE", "FDPE", "FDRE", "FDSE", "IDDR", "IDDR_2CLK", "LDCE", "LDPE", "ODDR", "SRL16E", "SRLC32E"}
    analog = {"MMCME2_ADV", "MMCME2_BASE", "PLLE2_ADV", "PLLE2_BASE", "XADC", "IDELAYCTRL", "IDELAYE2", "ODELAYE2", "IBUFDS_GTE2"}
    serdes = {"ISERDESE2", "OSERDESE2", "IN_FIFO", "OUT_FIFO"}
    device = {"BSCANE2", "CAPTUREE2", "DCIRESET", "DNA_PORT", "EFUSE_USR", "FRAME_ECCE2", "ICAPE2", "STARTUPE2", "USR_ACCESSE2"}
    memories = {
        "FIFO18E1",
        "FIFO36E1",
        "RAM128X1D",
        "RAM128X1S",
        "RAM256X1S",
        "RAM32M",
        "RAM32X1D",
        "RAM32X1S",
        "RAM32X1S_1",
        "RAM32X2S",
        "RAM64M",
        "RAM64X1D",
        "RAM64X1S",
        "RAM64X1S_1",
        "RAMB18E1",
        "RAMB36E1",
        "ROM128X1",
        "ROM256X1",
        "ROM32X1",
        "ROM64X1",
    }
    complex_clock = {"BUFGCTRL", "BUFHCE", "BUFMRCE", "BUFR"}
    disabled_diff = {
        "IBUF_IBUFDISABLE",
        "IBUF_INTERMDISABLE",
        "IBUFDS_IBUFDISABLE",
        "IBUFDS_INTERMDISABLE",
        "IBUFDS_DIFF_OUT_IBUFDISABLE",
        "IBUFDS_DIFF_OUT_INTERMDISABLE",
    }
    misc_complex = {"CFGLUT5", "DSP48E1", "KEEPER"}

    if title in tri_state:
        return "unsupported: requires a third electrical state (Z/high-impedance), which is outside binary Ising qubits"
    if title in sequential:
        return "unsupported: requires temporal state/current-vs-next-state modeling rather than a static input-output relation"
    if title in analog:
        return "unsupported: analog, delay, or clock-management behavior is not representable as a static binary Ising relation"
    if title in serdes:
        return "unsupported: serialized/clocked data movement primitive, not a static combinational relation"
    if title in device:
        return "unsupported: device-configuration or silicon-service primitive rather than logic functionality"
    if title in memories:
        return "unsupported: memory primitive would need explicit stored-state/address modeling beyond this static flow"
    if title in complex_clock:
        return "unsupported: steady-state approximation is possible, but divider/hold/init semantics are not fully captured yet"
    if title in disabled_diff:
        return "unsupported: contains disable/'No Change' semantics that need explicit state retention variables"
    if title in misc_complex:
        return "unsupported: not yet decomposed into a stable cubic binary model in this pass"
    return "unsupported: not implemented in this pass"


def load_chapter5_titles(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    pdf = PdfReader(str(pdf_path))
    def walk(items: list[object]) -> list[str] | None:
        for idx, item in enumerate(items):
            if isinstance(item, dict) and item.get("/Title") == "Ch. 5: Design Elements":
                if idx + 1 < len(items) and isinstance(items[idx + 1], list):
                    return [child["/Title"] for child in items[idx + 1] if isinstance(child, dict) and child.get("/Title")]
            if isinstance(item, list):
                result = walk(item)
                if result is not None:
                    return result
        return None

    return walk(list(pdf.outline)) or []


def write_supported_manifest(root_dir: Path, pdf_path: Path) -> None:
    chapter_titles = load_chapter5_titles(pdf_path)
    payload = []
    for title in chapter_titles:
        if title in PRIMITIVES:
            payload.append({"primitive": title, "status": "supported", "reason": PRIMITIVES[title].summary})
        else:
            payload.append({"primitive": title, "status": "unsupported", "reason": unsupported_reason(title)})
    SUPPORTED_MANIFEST_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def wrapper_script_text(primitive_name: str) -> str:
    return f"""from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

from ising_primitive_lib import run_named_primitive


if __name__ == "__main__":
    run_named_primitive("{primitive_name}", Path(__file__).resolve().parent)
"""
