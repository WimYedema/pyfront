from pyfront.generate.report import report
from pyfront.grammar.model import Grammar, NonTerminal, NonTerminalTerm, Rule, Term


class WalkGrammar:
    def pre_nt(self, nt: NonTerminal) -> None:
        """Override this method to perform an action on each non-terminal."""
        pass

    def post_nt(self, nt: NonTerminal) -> None:
        """Override this method to perform an action after visiting each non-terminal."""
        pass

    def pre_rule(self, rule: Rule) -> None:
        """Override this method to perform an action on each rule."""
        pass

    def post_rule(self, rule: Rule) -> None:
        """Override this method to perform an action after visiting each rule."""
        pass

    def pre_term(self, term: Term) -> None:
        """Override this method to perform an action on each term."""
        pass

    def post_term(self, term: Term) -> None:
        """Override this method to perform an action after visiting each term."""
        pass

    def walk(self, grammar: Grammar) -> None:
        self.visited = set()
        self.walk_nt(grammar.start)

    def walk_nt(self, nt: NonTerminal) -> None:
        if nt.name in self.visited:
            return
        self.visited.add(nt.name)
        self.pre_nt(nt)
        for rule in nt.rules:
            self.walk_rule(rule)
        self.post_nt(nt)

    def walk_rule(self, rule: Rule) -> None:
        self.pre_rule(rule)
        for term in rule.terms:
            self.pre_term(term)
            if isinstance(term, NonTerminalTerm):
                self.walk_nt(term.nt)
            self.post_term(term)
        self.post_rule(rule)


class FindRecursiveRules(WalkGrammar):
    def __init__(self):
        self.nt_stack = []
        self.recursive_nts = set()

    def pre_nt(self, nt: NonTerminal) -> None:
        self.nt_stack.append(nt.name)

    def post_nt(self, nt: NonTerminal) -> None:
        self.nt_stack.pop()

    def pre_term(self, term: Term) -> None:
        if isinstance(term, NonTerminalTerm):
            if term.name in self.nt_stack:
                self.recursive_nts.add(term.name)


def rule_has_nt(rule: Rule, nt_name: str) -> bool:
    """Check if a rule contains a specific non-terminal."""
    return any(isinstance(term, NonTerminalTerm) and term.name == nt_name for term in rule.terms)


class Inlining:
    grammar: Grammar

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.recursive_nts = set()
        self.used_by_graph = {}
        self.uses_graph = {}

    def expand_rules(self, src_nt: NonTerminal, dst_rule: Rule) -> None:
        dst_nt = dst_rule.nt
        for src_rule in src_nt.rules:
            new_terms = []
            for term in dst_rule.terms:
                if isinstance(term, NonTerminalTerm) and term.name == src_nt.name:
                    new_terms.extend(src_rule.terms)
                    if not src_rule.value.is_none():
                        build_nt = self.grammar.add_nt(f"make_{src_nt.name}")
                        build_nt.add_rule([], src_rule.value, src_rule.produce_count)
                        new_terms.append(build_nt.term().set_label(term.label or src_nt.name))
                else:
                    new_terms.append(term)
            dst_nt.add_rule(new_terms, dst_rule.value, dst_rule.produce_count)
        dst_nt.remove_rule(dst_rule)

    def expand_nt(self, src_name: str):
        if src_name in self.recursive_nts:
            return
        src_nt = self.grammar.get_nt(src_name)
        used_in = self.used_by_graph.get(src_name, set())
        if not used_in:
            return
        for dst_name in used_in:
            dst_nt = self.grammar.get_nt(dst_name)
            for dst_rule in [*dst_nt.rules]:
                if rule_has_nt(dst_rule, src_name):
                    self.expand_rules(src_nt, dst_rule)

        self.grammar.remove_nt(src_name)
        del self.used_by_graph[src_name]
        del self.uses_graph[src_name]

    def order_nts(self) -> list[str]:
        ordered_nts = []
        visited = set()

        def visit(dst: str):
            if dst in visited:
                return
            visited.add(dst)
            for src in self.uses_graph.get(dst, set()):
                visit(src)
            ordered_nts.append(dst)

        for dst in self.uses_graph.keys():
            visit(dst)

        return ordered_nts

    def compute_graph(self) -> None:
        for nt in self.grammar.non_terminals:
            self.used_by_graph.setdefault(nt.name, set())
            self.uses_graph.setdefault(nt.name, set())
            for rule in nt.rules:
                for term in rule.terms:
                    if isinstance(term, NonTerminalTerm):
                        self.used_by_graph.setdefault(term.name, set()).add(nt.name)
                        self.uses_graph.setdefault(nt.name, set()).add(term.name)

    def compute(self) -> Grammar:
        br = FindRecursiveRules()
        br.walk(self.grammar)
        self.compute_graph()
        self.recursive_nts = br.recursive_nts

        for nt in self.order_nts():
            self.expand_nt(nt)

        report.emit("# Inlined grammar\n")
        report.emit(str(self.grammar))
        return self.grammar
