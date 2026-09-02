from enum import Enum, auto

from .model import (
    Expression,
    FalseExpr,
    Field,
    FloatExpr,
    Front,
    GroupSymbol,
    IdExpr,
    IntExpr,
    KeywordSymbol,
    LabeledSymbol,
    NoneExpr,
    Rule,
    ScanRule,
    SeparatedSymbol,
    StringExpr,
    StringSymbol,
    Symbol,
    SymbolSequence,
    TrueExpr,
)
from .parser import Parser


class TokenType(Enum):
    # Keywords
    ROOT = auto()
    SCAN = auto()
    FIELD = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    # Operators
    DEFINES = auto()
    EQUALS = auto()
    LESS_THAN = auto()
    GREATER_THAN = auto()
    PLUS = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    RBRACE_PLUS = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    SEMICOLON = auto()
    COLON = auto()
    OR = auto()
    SLASH = auto()
    # Valued tokens
    IDENT = auto()
    INT = auto()
    STRING = auto()
    FLOAT = auto()

    _EOF = auto()  # End of file token


class Tokenizer:
    TokenRegex = {
        # Keywords
        TokenType.ROOT: r"ROOT(?![a-zA-Z0-9_])",
        TokenType.SCAN: r"SCAN(?![a-zA-Z0-9_])",
        TokenType.FIELD: r"FIELD(?![a-zA-Z0-9_])",
        TokenType.TRUE: r"True(?![a-zA-Z0-9_])",
        TokenType.FALSE: r"False(?![a-zA-Z0-9_])",
        TokenType.NONE: r"None(?![a-zA-Z0-9_])",
        # Operators
        TokenType.DEFINES: r"::=",
        TokenType.EQUALS: r"=",
        TokenType.LESS_THAN: r"<",
        TokenType.GREATER_THAN: r">",
        TokenType.PLUS: r"\+",
        TokenType.LPAREN: r"\(",
        TokenType.RPAREN: r"\)",
        TokenType.LBRACE: r"\{",
        TokenType.RBRACE: r"\}",
        TokenType.RBRACE_PLUS: r"\}+",
        TokenType.LBRACKET: r"\[",
        TokenType.RBRACKET: r"\]",
        TokenType.SEMICOLON: r";",
        TokenType.COLON: r":",
        TokenType.OR: r"\|",
        TokenType.SLASH: r"/",
        # Valued tokens
        TokenType.IDENT: r"[a-zA-Z_][a-zA-Z0-9_]*",
        TokenType.FLOAT: r"\d+\.\d+",
        TokenType.INT: r"\d+",
        TokenType.STRING: r'"(?:[^"\\]|\\.)*"',
    }

    WhitespaceRegexs = {
        r"\s+": "whitespace",
        r"//.*": "single-line comment",
        r"/\*[\s\S]*?\*/": "multi-line comment",
    }


def parse_symbol(parser: Parser[TokenType]) -> Symbol:
    """Parse a symbol from the lexer."""
    token = parser.next_token
    match token.type:
        case TokenType.IDENT:
            parser.advance()
            if parser.match(TokenType.COLON):
                label = token.value
                symbol = parse_symbol(parser)
                return LabeledSymbol(label=label, symbol=symbol)
            return KeywordSymbol(keyword=token.value)
        case TokenType.STRING:
            parser.advance()
            return StringSymbol(value=token.value)
        case TokenType.LPAREN:
            parser.advance()
            with parser.terminator(TokenType.RPAREN):
                symbols = parse_symbol_sequence(parser)
            return GroupSymbol(symbols=symbols)
        case TokenType.LBRACKET:
            parser.advance()
            with parser.terminator(TokenType.RBRACKET):
                symbols = parse_symbol_sequence(parser)
            return GroupSymbol(symbols=symbols, optional=True)
        case TokenType.LBRACE:
            parser.advance()
            with parser.terminator(TokenType.RBRACE):
                symbols = parse_symbol_sequence(parser)
            optional = not parser.match(TokenType.PLUS)
            return GroupSymbol(symbols=symbols, multiple=True, optional=optional)
        case _:
            raise SyntaxError(f"Unexpected token: {token}")


def parse_separated_symbol(parser: Parser[TokenType]) -> Symbol:
    symbol = parse_symbol(parser)
    if parser.match(TokenType.SLASH):
        separator = parser.expect(TokenType.STRING)
        return SeparatedSymbol(symbol=symbol, separator=separator)
    else:
        return symbol


def parse_expression(parser: Parser[TokenType]) -> Expression:
    """Parse an expression from the lexer."""
    token = parser.next_token
    match token.type:
        case TokenType.IDENT:
            parser.advance()
            return IdExpr(id=token.value)
        case TokenType.STRING:
            parser.advance()
            return StringExpr(value=token.value)
        case TokenType.INT:
            parser.advance()
            return IntExpr(value=int(token.value))
        case TokenType.FLOAT:
            parser.advance()
            return FloatExpr(value=float(token.value))
        case TokenType.TRUE:
            parser.advance()
            return TrueExpr()
        case TokenType.FALSE:
            parser.advance()
            return FalseExpr()
        case TokenType.NONE:
            parser.advance()
            return NoneExpr()
        case _:
            raise SyntaxError(f"Unexpected token: {token}")


def parse_field(parser: Parser[TokenType]) -> Field:
    """Parse a field from the lexer."""
    name = parser.expect(TokenType.IDENT)
    parser.expect(TokenType.COLON)
    symbol = parse_symbol(parser)
    value = None
    if parser.match(TokenType.EQUALS):
        value = parse_expression(parser)
    return Field(name=name, type=symbol, value=value)


def parse_symbol_sequence(parser: Parser[TokenType]) -> SymbolSequence:
    """Parse a sequence of symbols from the lexer."""
    symbols = [parse_separated_symbol(parser) for _ in parser.multiple()]
    return SymbolSequence(symbols=symbols)


def parse_subrule(parser: Parser[TokenType]) -> Rule:
    """Parse a single rule from the lexer."""
    name = parser.expect(TokenType.IDENT)
    if not parser.match(TokenType.DEFINES):
        return Rule(
            is_root=False,
            name=name,
            super_type=None,
            fields=[],
            terms=SymbolSequence(symbols=[]),
            alts=None,
            is_ref=True,
        )

    fields = []
    while parser.match(TokenType.FIELD):
        fields.append(parse_field(parser))

    parser.push_terminator(TokenType.GREATER_THAN, TokenType.OR)
    symbols = parse_symbol_sequence(parser)
    parser.pop_terminator(TokenType.GREATER_THAN, TokenType.OR)
    return Rule(
        is_root=False,
        name=name,
        super_type=None,
        fields=fields,
        terms=symbols,
        alts=None,
    )


def parse_rule(parser: Parser[TokenType]) -> Rule:
    """Parse a single rule from the lexer."""
    name = parser.expect(TokenType.IDENT)
    is_root = parser.match(TokenType.ROOT)
    super_type = None
    if parser.match(TokenType.LESS_THAN):
        super_type = parser.expect(TokenType.IDENT)
    parser.expect(TokenType.DEFINES)
    fields = []
    while parser.match(TokenType.FIELD):
        fields.append(parse_field(parser))

    with parser.terminator(TokenType.SEMICOLON, TokenType.LESS_THAN):
        symbols = parse_symbol_sequence(parser)

    if parser.last_token.type == TokenType.LESS_THAN:
        with parser.terminator(TokenType.GREATER_THAN):
            alternatives = [parse_subrule(parser) for _ in parser.multiple(separator=TokenType.OR)]
        parser.expect(TokenType.SEMICOLON)
    else:
        alternatives = None

    return Rule(
        is_root=is_root,
        name=name,
        super_type=super_type,
        fields=fields,
        terms=symbols,
        alts=alternatives,
    )


def parse_scan_rule(parser: Parser[TokenType]) -> ScanRule:
    """Parse a scan rule from the lexer."""
    parser.expect(TokenType.SCAN)
    name = parser.expect(TokenType.IDENT)
    parser.expect(TokenType.COLON)
    type_ = parser.expect(TokenType.IDENT)
    parser.expect(TokenType.DEFINES)
    pattern = parser.expect(TokenType.STRING)
    parser.expect(TokenType.SEMICOLON)
    return ScanRule(name=name, type=type_, pattern=pattern)


def parse_front(parser: Parser[TokenType]) -> Front:
    """Parse a .front file using the provided lexer."""
    parser.push_terminator(TokenType._EOF, TokenType.SCAN)
    rules = [parse_rule(parser) for _ in parser.multiple()]
    parser.pop_terminator(TokenType._EOF, TokenType.SCAN)
    if parser.next_token and parser.next_token.type == TokenType.SCAN:
        with parser.terminator(TokenType._EOF):
            scan_rules = [parse_scan_rule(parser) for _ in parser.multiple()]
    else:
        scan_rules = []
    return Front(rules=rules, scan_rules=scan_rules)
