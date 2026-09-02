from pyfront.generate.report import report
from pyfront.grammar.model import Grammar, NonTerminal, Rule, RuleValue


class LeftFactoring:
    grammar: Grammar

    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def _factor_rules(self, nt: NonTerminal, prefix: str, rules_with_prefix: list[Rule]) -> None:
        # Create a new non-terminal for the factored rules
        new_nt = self.grammar.add_nt(f"{nt.name}_alt")

        # Create a new rule for the original non-terminal with the prefix and the new non-terminal
        new_rule_terms = [self.grammar.ref_term(prefix), new_nt.term()]
        new_rule_value = RuleValue.forward("shared_value")
        self.grammar.add_rule(nt.name, new_rule_terms, new_rule_value)

        # Create rules for the new non-terminal with the remaining terms of the original rules
        for rule in rules_with_prefix:
            remaining_terms = rule.terms[1:]
            self.grammar.add_rule(new_nt.name, remaining_terms, rule.value)
            nt.remove_rule(rule)

    def nt_left_factor(self, nt: NonTerminal) -> None:
        if len(nt.rules) <= 1:
            return

        report.emit(f"## Left-factoring non-terminal {nt.name}\n")
        prefixes = {}
        for rule in nt.rules:
            if rule.terms:
                prefixes.setdefault(rule.terms[0].name, []).append(rule)

        report.emit(f"Prefixes: {prefixes}\n")

        for prefix, rules_with_prefix in prefixes.items():
            if len(rules_with_prefix) > 1:
                self._factor_rules(nt, prefix, rules_with_prefix)

    def compute(self) -> Grammar:
        """Create a new Grammar where left-factors are factored out.

            A -> X
            A -> X Y Z

        becomes

            A -> X B
            B -> Y Z
            B ->

        This is useful for LL(1) parsing.
        """
        for nt in self.grammar.non_terminals:
            self.nt_left_factor(nt)

        report.emit("# Left-factored grammar\n")
        report.emit(str(self.grammar))

        return self.grammar
