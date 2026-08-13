from __future__ import annotations

from dataclasses import dataclass, field
import ast
import re


class CompileError(Exception):
    pass


KEYWORDS = {
    "asm",
    "break",
    "const",
    "continue",
    "else",
    "false",
    "fn",
    "if",
    "imm",
    "let",
    "loop",
    "return",
    "static",
    "true",
    "void",
    "while",
    "zeroed",
}

TWO_CHAR = {"->", "==", "!=", "<=", ">=", "<<", ">>", "&&", "||"}
ONE_CHAR = set("{}()[],:;=+-*/&|^~<>%")


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


def compile_source(source: str) -> str:
    parser = Parser(tokenize(source))
    program = parser.parse_program()
    return Codegen(program).emit()


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    col = 1
    while i < len(source):
        ch = source[i]
        if ch in " \t\r":
            i += 1
            col += 1
            continue
        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue
        if source.startswith("//", i):
            while i < len(source) and source[i] != "\n":
                i += 1
                col += 1
            continue
        if ch == "#":
            while i < len(source) and source[i] != "\n":
                i += 1
                col += 1
            continue
        if ch == '"' or (ch == "b" and i + 1 < len(source) and source[i + 1] == '"'):
            start_i = i
            start_col = col
            if ch == "b":
                i += 1
                col += 1
            i += 1
            col += 1
            escape = False
            while i < len(source):
                c = source[i]
                i += 1
                col += 1
                if c == "\n":
                    line += 1
                    col = 1
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    break
            else:
                raise CompileError(f"line {line}: unterminated string literal")
            tokens.append(Token("string", source[start_i:i], line, start_col))
            continue
        if ch.isdigit():
            start = i
            start_col = col
            while i < len(source) and re.match(r"[A-Za-z0-9_]", source[i]):
                i += 1
                col += 1
            tokens.append(Token("number", source[start:i], line, start_col))
            continue
        if ch.isalpha() or ch == "_":
            start = i
            start_col = col
            while i < len(source) and re.match(r"[A-Za-z0-9_.$]", source[i]):
                i += 1
                col += 1
            value = source[start:i]
            tokens.append(Token("keyword" if value in KEYWORDS else "ident", value, line, start_col))
            continue
        two = source[i : i + 2]
        if two in TWO_CHAR:
            tokens.append(Token("symbol", two, line, col))
            i += 2
            col += 2
            continue
        if ch in ONE_CHAR:
            tokens.append(Token("symbol", ch, line, col))
            i += 1
            col += 1
            continue
        raise CompileError(f"line {line}, col {col}: unexpected character {ch!r}")
    tokens.append(Token("eof", "", line, col))
    return tokens


@dataclass
class Program:
    consts: list[ConstDecl] = field(default_factory=list)
    statics: list[StaticDecl] = field(default_factory=list)
    funcs: list[FuncDecl] = field(default_factory=list)


@dataclass
class ConstDecl:
    name: str
    value: int


@dataclass
class StaticDecl:
    name: str
    kind: str
    value: str | int | list[int]


@dataclass
class FuncDecl:
    name: str
    params: list[str]
    body: list[Stmt]


class Stmt:
    pass


@dataclass
class LetStmt(Stmt):
    name: str
    expr: Expr
    immutable: bool = False


@dataclass
class AssignStmt(Stmt):
    name: str
    expr: Expr


@dataclass
class ReturnStmt(Stmt):
    expr: Expr | None


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class IfStmt(Stmt):
    cond: Expr
    then_body: list[Stmt]
    else_body: list[Stmt]


@dataclass
class WhileStmt(Stmt):
    cond: Expr
    body: list[Stmt]


@dataclass
class LoopStmt(Stmt):
    body: list[Stmt]


class BreakStmt(Stmt):
    pass


class ContinueStmt(Stmt):
    pass


@dataclass
class AsmStmt(Stmt):
    lines: list[str]


class Expr:
    pass


@dataclass
class NumberExpr(Expr):
    value: int


@dataclass
class VarExpr(Expr):
    name: str


@dataclass
class UnaryExpr(Expr):
    op: str
    expr: Expr


@dataclass
class BinaryExpr(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class CallExpr(Expr):
    name: str
    args: list[Expr]


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def parse_program(self) -> Program:
        program = Program()
        while not self.check("eof"):
            if self.match_value("const"):
                program.consts.append(self.parse_const())
            elif self.match_value("static"):
                program.statics.append(self.parse_static())
            elif self.match_value("fn"):
                program.funcs.append(self.parse_func())
            else:
                self.error("expected const, static, or fn")
        return program

    def parse_const(self) -> ConstDecl:
        name = self.consume_ident()
        if self.match_value(":"):
            self.skip_type()
        self.consume_value("=")
        value = self.consume_number()
        self.consume_value(";")
        return ConstDecl(name, value)

    def parse_static(self) -> StaticDecl:
        name = self.consume_ident()
        self.consume_value(":")
        type_start = self.pos
        self.skip_type()
        type_text = "".join(tok.value for tok in self.tokens[type_start:self.pos])
        self.consume_value("=")
        if self.match_value("zeroed"):
            value: str | int = self.static_array_size_from_previous_type
            kind = "zeroed"
        elif self.check("string"):
            tok = self.consume("string")
            kind = "bytes"
            value = tok.value
        elif self.match_value("["):
            values: list[int] = []
            if not self.check_value("]"):
                while True:
                    values.append(self.consume_number())
                    if not self.match_value(","):
                        break
            self.consume_value("]")
            match = re.fullmatch(r"\[(u8|u16|u32);(\d+)\]", type_text)
            if match is None:
                self.error("numeric array requires an explicit [u8/u16/u32; N] type")
            element_type, size_text = match.groups()
            if len(values) != int(size_text):
                self.error(f"numeric array expects {size_text} values, got {len(values)}")
            kind = f"values_{element_type}"
            value = values
        elif type_text in {"u8", "u16", "u32"}:
            kind = type_text
            if self.check("number"):
                value = self.consume_number()
            else:
                value = self.consume_ident()
        else:
            self.error("expected byte string, zeroed, or scalar static initializer")
        self.consume_value(";")
        return StaticDecl(name, kind, value)

    def parse_func(self) -> FuncDecl:
        name = self.consume_ident()
        self.consume_value("(")
        params: list[str] = []
        if not self.check_value(")"):
            while True:
                params.append(self.consume_ident())
                if self.match_value(":"):
                    self.skip_type()
                if not self.match_value(","):
                    break
        self.consume_value(")")
        if self.match_value("->"):
            self.skip_type()
        body = self.parse_block()
        return FuncDecl(name, params, body)

    def parse_block(self) -> list[Stmt]:
        self.consume_value("{")
        body: list[Stmt] = []
        while not self.check_value("}"):
            body.append(self.parse_stmt())
        self.consume_value("}")
        return body

    def parse_stmt(self) -> Stmt:
        if self.match_value("let"):
            immutable = self.match_value("imm")
            name = self.consume_ident()
            if self.match_value(":"):
                self.skip_type()
            self.consume_value("=")
            expr = self.parse_expr()
            self.consume_value(";")
            return LetStmt(name, expr, immutable)
        if self.match_value("return"):
            if self.match_value(";"):
                return ReturnStmt(None)
            expr = self.parse_expr()
            self.consume_value(";")
            return ReturnStmt(expr)
        if self.match_value("if"):
            cond = self.parse_expr()
            then_body = self.parse_block()
            else_body = self.parse_block() if self.match_value("else") else []
            return IfStmt(cond, then_body, else_body)
        if self.match_value("while"):
            cond = self.parse_expr()
            return WhileStmt(cond, self.parse_block())
        if self.match_value("loop"):
            return LoopStmt(self.parse_block())
        if self.match_value("break"):
            self.consume_value(";")
            return BreakStmt()
        if self.match_value("continue"):
            self.consume_value(";")
            return ContinueStmt()
        if self.match_value("asm"):
            self.consume_value("{")
            lines: list[str] = []
            while not self.check_value("}"):
                tok = self.consume("string")
                lines.append(parse_string_token(tok.value))
            self.consume_value("}")
            return AsmStmt(lines)
        if self.check("ident") and self.peek(1).value == "=":
            name = self.consume_ident()
            self.consume_value("=")
            expr = self.parse_expr()
            self.consume_value(";")
            return AssignStmt(name, expr)
        expr = self.parse_expr()
        self.consume_value(";")
        return ExprStmt(expr)

    def parse_expr(self, min_prec: int = 0) -> Expr:
        expr = self.parse_unary()
        while True:
            tok = self.peek()
            if tok.value not in PRECEDENCE or PRECEDENCE[tok.value] < min_prec:
                break
            op = tok.value
            prec = PRECEDENCE[op]
            self.pos += 1
            right = self.parse_expr(prec + 1)
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_unary(self) -> Expr:
        if self.match_value("-"):
            return UnaryExpr("-", self.parse_unary())
        if self.match_value("~"):
            return UnaryExpr("~", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        if self.match_value("("):
            expr = self.parse_expr()
            self.consume_value(")")
            return expr
        if self.match_value("true"):
            return NumberExpr(1)
        if self.match_value("false"):
            return NumberExpr(0)
        if self.check("number"):
            return NumberExpr(self.consume_number())
        name = self.consume_ident()
        if self.match_value("("):
            args: list[Expr] = []
            if not self.check_value(")"):
                while True:
                    args.append(self.parse_expr())
                    if not self.match_value(","):
                        break
            self.consume_value(")")
            return CallExpr(name, args)
        return VarExpr(name)

    def skip_type(self) -> None:
        depth = 0
        saw_array_size: int | None = None
        while True:
            tok = self.peek()
            if depth == 0 and tok.value in {"=", ",", ")", "{", ";"}:
                break
            if tok.value == "[":
                depth += 1
            elif tok.value == "]":
                depth -= 1
            elif tok.kind == "number":
                saw_array_size = int(tok.value, 0)
            self.pos += 1
        self.static_array_size_from_previous_type = saw_array_size or 0

    def consume_number(self) -> int:
        tok = self.consume("number")
        return int(tok.value, 0)

    def consume_ident(self) -> str:
        tok = self.peek()
        if tok.kind not in {"ident", "keyword"} or tok.value in KEYWORDS - {"void"}:
            self.error("expected identifier")
        self.pos += 1
        return tok.value

    def consume(self, kind: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            self.error(f"expected {kind}")
        self.pos += 1
        return tok

    def consume_value(self, value: str) -> Token:
        tok = self.peek()
        if tok.value != value:
            self.error(f"expected {value!r}")
        self.pos += 1
        return tok

    def match_value(self, value: str) -> bool:
        if self.check_value(value):
            self.pos += 1
            return True
        return False

    def check(self, kind: str) -> bool:
        return self.peek().kind == kind

    def check_value(self, value: str) -> bool:
        return self.peek().value == value

    def peek(self, offset: int = 0) -> Token:
        return self.tokens[self.pos + offset]

    def error(self, message: str) -> None:
        tok = self.peek()
        raise CompileError(f"line {tok.line}, col {tok.col}: {message}, got {tok.value!r}")


PRECEDENCE = {
    "||": 1,
    "&&": 2,
    "|": 3,
    "^": 4,
    "&": 5,
    "==": 6,
    "!=": 6,
    "<": 7,
    "<=": 7,
    ">": 7,
    ">=": 7,
    "<<": 8,
    ">>": 8,
    "+": 9,
    "-": 9,
    "*": 10,
    "/": 10,
    "%": 10,
}


class Codegen:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.consts = {c.name: c.value for c in program.consts}
        self.statics = {s.name: s for s in program.statics}
        self.lines: list[str] = []
        self.label_id = 0
        self.locals: dict[str, str] = {}
        self.immutable: set[str] = set()
        self.free_locals = ["r7", "r8", "r9", "r10", "r11", "r12"]
        self.loop_stack: list[tuple[str, str]] = []
        self.return_label = ""

    def emit(self) -> str:
        self.lines.append("; Generated by melc 0.1.0")
        self.lines.append("jmp main")
        self.lines.append("")
        for const in self.program.consts:
            self.lines.append(f"const {const.name} = {const.value}")
        if self.program.consts:
            self.lines.append("")
        for func in self.program.funcs:
            self.emit_func(func)
        if self.program.statics:
            self.lines.append("")
            for static in self.program.statics:
                self.emit_static(static)
        return "\n".join(self.lines).rstrip() + "\n"

    def emit_func(self, func: FuncDecl) -> None:
        if len(func.params) > 6:
            raise CompileError(f"function {func.name} has more than 6 parameters")
        self.locals = {}
        self.immutable = set()
        self.free_locals = ["r7", "r8", "r9", "r10", "r11", "r12"]
        self.return_label = self.new_label(f"{func.name}_return")
        self.lines.append(f"{func.name}:")
        for index, param in enumerate(func.params):
            self.alloc_local(param)
        for name, immutable in collect_lets(func.body):
            self.alloc_local(name)
            if immutable:
                self.immutable.add(name)
        saved_regs = list(self.locals.values())
        if func.name != "main":
            for reg in saved_regs:
                self.lines.append(f"push {reg}")
        for index, param in enumerate(func.params):
            reg = self.locals[param]
            self.lines.append(f"mov {reg}, r{index + 1}")
        for stmt in func.body:
            self.emit_stmt(stmt)
        self.lines.append(f"{self.return_label}:")
        if func.name != "main":
            for reg in reversed(saved_regs):
                self.lines.append(f"pop {reg}")
        self.lines.append("ret")
        self.lines.append("")

    def emit_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetStmt):
            reg = self.require_local(stmt.name)
            value = self.emit_expr(stmt.expr, "r1")
            self.lines.append(f"mov {reg}, {value}")
        elif isinstance(stmt, AssignStmt):
            if stmt.name in self.immutable:
                raise CompileError(f"cannot assign to immutable local {stmt.name!r}")
            value = self.emit_expr(stmt.expr, "r1")
            if stmt.name in self.locals:
                self.lines.append(f"mov {self.locals[stmt.name]}, {value}")
            elif stmt.name in self.statics and self.statics[stmt.name].kind in {"u8", "u16", "u32"}:
                width = self.statics[stmt.name].kind[1:]
                address = self.next_temp(value)
                self.lines.append(f"add {address}, zr, {stmt.name}")
                self.lines.append(f"store_{width} [{address}], {value}")
            else:
                raise CompileError(f"unknown or non-scalar assignment target {stmt.name!r}")
        elif isinstance(stmt, ReturnStmt):
            if stmt.expr is not None:
                self.emit_expr(stmt.expr, "r1")
            self.lines.append(f"jmp {self.return_label}")
        elif isinstance(stmt, ExprStmt):
            self.emit_expr(stmt.expr, "r1")
        elif isinstance(stmt, IfStmt):
            else_label = self.new_label("else")
            end_label = self.new_label("endif")
            self.emit_condition_false_jump(stmt.cond, else_label)
            for inner in stmt.then_body:
                self.emit_stmt(inner)
            self.lines.append(f"jmp {end_label}")
            self.lines.append(f"{else_label}:")
            for inner in stmt.else_body:
                self.emit_stmt(inner)
            self.lines.append(f"{end_label}:")
        elif isinstance(stmt, WhileStmt):
            start = self.new_label("while")
            end = self.new_label("endwhile")
            self.loop_stack.append((start, end))
            self.lines.append(f"{start}:")
            self.emit_condition_false_jump(stmt.cond, end)
            for inner in stmt.body:
                self.emit_stmt(inner)
            self.lines.append(f"jmp {start}")
            self.lines.append(f"{end}:")
            self.loop_stack.pop()
        elif isinstance(stmt, LoopStmt):
            start = self.new_label("loop")
            end = self.new_label("endloop")
            self.loop_stack.append((start, end))
            self.lines.append(f"{start}:")
            for inner in stmt.body:
                self.emit_stmt(inner)
            self.lines.append(f"jmp {start}")
            self.lines.append(f"{end}:")
            self.loop_stack.pop()
        elif isinstance(stmt, BreakStmt):
            if not self.loop_stack:
                raise CompileError("break outside loop")
            self.lines.append(f"jmp {self.loop_stack[-1][1]}")
        elif isinstance(stmt, ContinueStmt):
            if not self.loop_stack:
                raise CompileError("continue outside loop")
            self.lines.append(f"jmp {self.loop_stack[-1][0]}")
        elif isinstance(stmt, AsmStmt):
            for line in stmt.lines:
                self.lines.append(line)
        else:
            raise CompileError(f"unsupported statement {stmt!r}")

    def emit_expr(self, expr: Expr, target: str) -> str:
        if isinstance(expr, NumberExpr):
            self.emit_immediate(target, expr.value)
            return target
        if isinstance(expr, VarExpr):
            if expr.name in self.consts:
                self.emit_immediate(target, self.consts[expr.name])
                return target
            if expr.name in self.locals:
                reg = self.locals[expr.name]
                if reg != target:
                    self.lines.append(f"mov {target}, {reg}")
                return target
            if expr.name in self.statics and self.statics[expr.name].kind in {"u8", "u16", "u32"}:
                width = self.statics[expr.name].kind[1:]
                address = self.next_temp(target)
                self.lines.append(f"add {address}, zr, {expr.name}")
                self.lines.append(f"load_{width} {target}, [{address}]")
                return target
            self.lines.append(f"add {target}, zr, {expr.name}")
            return target
        if isinstance(expr, UnaryExpr):
            src = self.emit_expr(expr.expr, target)
            if expr.op == "-":
                self.lines.append(f"neg {target}, {src}")
            elif expr.op == "~":
                self.lines.append(f"not {target}, {src}")
            else:
                raise CompileError(f"unsupported unary operator {expr.op}")
            return target
        if isinstance(expr, BinaryExpr):
            return self.emit_binary(expr, target)
        if isinstance(expr, CallExpr):
            return self.emit_call(expr, target)
        raise CompileError(f"unsupported expression {expr!r}")

    def emit_binary(self, expr: BinaryExpr, target: str) -> str:
        if expr.op in {"==", "!=", "<", "<=", ">", ">=", "&&", "||"}:
            true_label = self.new_label("bool_true")
            end_label = self.new_label("bool_end")
            self.emit_condition_true_jump(expr, true_label)
            self.lines.append(f"mov {target}, 0")
            self.lines.append(f"jmp {end_label}")
            self.lines.append(f"{true_label}:")
            self.lines.append(f"mov {target}, 1")
            self.lines.append(f"{end_label}:")
            return target
        left = self.emit_expr(expr.left, target)
        right = self.emit_expr(expr.right, self.next_temp(target))
        op_map = {
            "+": "add",
            "-": "sub",
            "&": "and",
            "|": "or",
            "^": "xor",
            "<<": "lsl",
            ">>": "lsr",
            "*": "mul",
            "/": "div",
            "%": "mod",
        }
        # if expr.op == "*":
        #     raise CompileError("'*' is reserved but multiplication is not implemented for Symphony yet")
        if expr.op not in op_map:
            raise CompileError(f"unsupported binary operator {expr.op}")
        self.lines.append(f"{op_map[expr.op]} {target}, {left}, {right}")
        return target

    def emit_call(self, expr: CallExpr, target: str) -> str:
        if len(expr.args) > 6:
            raise CompileError(f"call to {expr.name} has more than 6 arguments")
        if expr.name == "keyboard_read":
            self.require_arg_count(expr, 0)
            self.lines.append(f"keyboard {target}")
            return target
        if expr.name == "time_low":
            self.require_arg_count(expr, 0)
            self.lines.append(f"time_0 {target}")
            return target
        if expr.name == "time_high":
            self.require_arg_count(expr, 0)
            refresh = self.next_temp(target)
            self.lines.append(f"time_0 {refresh}")
            self.lines.append(f"time_1 {target}")
            return target
        if expr.name == "time_cached_high":
            self.require_arg_count(expr, 0)
            self.lines.append(f"time_1 {target}")
            return target
        if expr.name == "time_snapshot":
            self.require_arg_count(expr, 2)
            names: list[str] = []
            for arg in expr.args:
                if not isinstance(arg, VarExpr):
                    raise CompileError("time_snapshot expects two u32 static variables")
                static = self.statics.get(arg.name)
                if static is None or static.kind != "u32":
                    raise CompileError("time_snapshot expects two u32 static variables")
                names.append(arg.name)
            self.lines.append("time_0 r1")
            self.lines.append("time_1 r2")
            self.lines.append(f"add r3, zr, {names[0]}")
            self.lines.append("store_32 [r3], r2")
            self.lines.append(f"add r3, zr, {names[1]}")
            self.lines.append("store_32 [r3], r1")
            return target
        if expr.name == "counter":
            self.require_arg_count(expr, 0)
            self.lines.append(f"counter {target}")
            return target
        if expr.name == "in_read":
            self.require_arg_count(expr, 0)
            self.lines.append(f"in {target}")
            return target
        if expr.name == "screen_set":
            self.require_arg_count(expr, 2)
            a = self.emit_expr(expr.args[0], "r1")
            b = self.emit_expr(expr.args[1], "r2")
            self.lines.append(f"screen {a}, {b}")
            return target
        screen_options = {
            "screen_mode": 0,
            "screen_buffer": 1,
            "screen_foreground": 2,
            "screen_background": 3,
            "screen_font": 4,
            "screen_resolution": 2,
        }
        if expr.name in screen_options:
            self.require_arg_count(expr, 1)
            value = self.emit_expr(expr.args[0], "r2")
            self.lines.append(f"mov r1, {screen_options[expr.name]}")
            self.lines.append(f"screen r1, {value}")
            return target
        if expr.name == "out_write":
            self.require_arg_count(expr, 1)
            a = self.emit_expr(expr.args[0], "r1")
            self.lines.append(f"out {a}")
            return target
        if expr.name == "load8":
            self.require_arg_count(expr, 1)
            address = self.emit_expr(expr.args[0], target)
            self.lines.append(f"load_8 {target}, [{address}]")
            return target
        if expr.name == "store8":
            self.require_arg_count(expr, 2)
            address = self.emit_expr(expr.args[0], "r1")
            value = self.emit_expr(expr.args[1], "r2")
            self.lines.append(f"store_8 [{address}], {value}")
            return target
        if expr.name == "stack_set":
            self.require_arg_count(expr, 1)
            value = self.emit_expr(expr.args[0], "r1")
            self.lines.append(f"mov sp, {value}")
            return target
        if expr.name == "restart":
            self.require_arg_count(expr, 0)
            self.lines.append("jmp main")
            return target

        for index, arg in enumerate(expr.args, start=1):
            self.emit_expr(arg, f"r{index}")
        self.lines.append(f"call {expr.name}")
        if target != "r1":
            self.lines.append(f"mov {target}, r1")
        return target

    def emit_condition_false_jump(self, expr: Expr, label: str) -> None:
        if isinstance(expr, BinaryExpr) and expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            left = self.emit_expr(expr.left, "r1")
            right = self.emit_expr(expr.right, "r2")
            self.lines.append(f"cmp {left}, {right}")
            inverse = {"==": "jne", "!=": "je", "<": "jge", "<=": "jg", ">": "jle", ">=": "jl"}[expr.op]
            self.lines.append(f"{inverse} {label}")
            return
        self.emit_expr(expr, "r1")
        self.lines.append("cmp r1, 0")
        self.lines.append(f"je {label}")

    def emit_condition_true_jump(self, expr: Expr, label: str) -> None:
        if isinstance(expr, BinaryExpr) and expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            left = self.emit_expr(expr.left, "r1")
            right = self.emit_expr(expr.right, "r2")
            self.lines.append(f"cmp {left}, {right}")
            jump = {"==": "je", "!=": "jne", "<": "jl", "<=": "jle", ">": "jg", ">=": "jge"}[expr.op]
            self.lines.append(f"{jump} {label}")
            return
        self.emit_expr(expr, "r1")
        self.lines.append("cmp r1, 0")
        self.lines.append(f"jne {label}")

    def emit_static(self, static: StaticDecl) -> None:
        self.lines.append(f"{static.name}:")
        if static.kind == "bytes":
            literal = static.value
            assert isinstance(literal, str)
            text = literal[1:] if literal.startswith("b") else literal
            self.lines.append(text)
        elif static.kind == "zeroed":
            size = int(static.value)
            if size <= 0:
                raise CompileError(f"static {static.name} has unknown zeroed size")
            for _ in range(size):
                self.lines.append("U8 0")
        elif static.kind in {"u8", "u16", "u32"}:
            self.lines.append(f"{static.kind.upper()} {static.value}")
        elif static.kind.startswith("values_"):
            width = static.kind.removeprefix("values_").upper()
            values = static.value
            assert isinstance(values, list)
            for value in values:
                self.lines.append(f"{width} {value}")
        else:
            raise CompileError(f"unsupported static kind {static.kind}")

    def alloc_local(self, name: str) -> str:
        if name in self.locals:
            raise CompileError(f"duplicate local {name!r}")
        if not self.free_locals:
            raise CompileError("too many locals for first compiler version")
        reg = self.free_locals.pop(0)
        self.locals[name] = reg
        return reg

    def require_local(self, name: str) -> str:
        if name not in self.locals:
            raise CompileError(f"unknown local {name!r}")
        return self.locals[name]

    def new_label(self, prefix: str) -> str:
        self.label_id += 1
        return f"__mel_{prefix}_{self.label_id}"

    def next_temp(self, current: str) -> str:
        order = ["r1", "r2", "r3", "r4", "r5", "r6"]
        try:
            index = order.index(current)
        except ValueError:
            return "r1"
        if index + 1 >= len(order):
            raise CompileError("expression is too complex for temporary registers")
        return order[index + 1]

    def emit_immediate(self, target: str, value: int) -> None:
        value &= 0xFFFFFFFF
        if value <= 0xFFFF:
            self.lines.append(f"mov {target}, {value}")
            return
        high = value >> 16
        low = value & 0xFFFF
        self.lines.append(f"mov {target}, {high}")
        self.lines.append(f"lsl {target}, {target}, 16")
        if low:
            self.lines.append(f"or {target}, {target}, {low}")

    @staticmethod
    def require_arg_count(expr: CallExpr, count: int) -> None:
        if len(expr.args) != count:
            raise CompileError(f"{expr.name} expects {count} arguments, got {len(expr.args)}")


def collect_lets(body: list[Stmt]) -> list[tuple[str, bool]]:
    found: list[tuple[str, bool]] = []
    seen: set[str] = set()

    def visit(stmts: list[Stmt]) -> None:
        for stmt in stmts:
            if isinstance(stmt, LetStmt):
                if stmt.name in seen:
                    raise CompileError(f"duplicate local {stmt.name!r}")
                seen.add(stmt.name)
                found.append((stmt.name, stmt.immutable))
            elif isinstance(stmt, IfStmt):
                visit(stmt.then_body)
                visit(stmt.else_body)
            elif isinstance(stmt, WhileStmt):
                visit(stmt.body)
            elif isinstance(stmt, LoopStmt):
                visit(stmt.body)

    visit(body)
    return found


def parse_string_token(value: str) -> str:
    text = value[1:] if value.startswith("b") else value
    try:
        parsed = ast.literal_eval(text)
    except Exception as exc:
        raise CompileError(f"invalid asm string {value!r}: {exc}") from exc
    if not isinstance(parsed, str):
        raise CompileError(f"invalid asm string {value!r}")
    return parsed
