import logging

import pyfront.grammar.model as gm
from pyfront.generate.report import report
from pyfront.generate.stabilize import stabilize_2d, stabilizing_1d

logger = logging.getLogger(__name__)


class PopulateParseTable:
    def __init__(self, grammar: gm.Grammar):
        self.start = grammar.start
        self.rules = list(grammar.rules)
        self.is_nullable = {rule.nt: False for rule in self.rules}
        self.first_set = {rule.nt: set() for rule in self.rules}
        self.follow_set = {rule.nt: set() for rule in self.rules}

    def nt(self, ntt: gm.NonTerminalTerm) -> gm.NonTerminal:
        return ntt.nt

    def compute_nullable(self) -> None:
        """Compute the nullability of each non-terminal in the grammar."""
        for is_nullable in stabilizing_1d(self.is_nullable):
            for rule in self.rules:
                if not is_nullable[rule.nt]:
                    if all(
                        isinstance(term, gm.NonTerminalTerm) and is_nullable[self.nt(term)]
                        for term in rule.terms
                    ):
                        report.nt_info(rule.nt.name, "nullable", "yes")
                        is_nullable[rule.nt] = True

    def compute_first_sets(self) -> None:
        for first_set in stabilize_2d(self.first_set):
            for rule in self.rules:
                for term in rule.terms:
                    if isinstance(term, gm.TerminalTerm):
                        first_set[rule.nt].add(term.name)
                        break
                    elif isinstance(term, gm.NonTerminalTerm):
                        first_set[rule.nt].update(first_set[self.nt(term)])
                        if not self.is_nullable[self.nt(term)]:
                            break

        for nt, first_set in sorted(self.first_set.items(), key=lambda item: item[0].name):
            report.nt_info(nt.name, "first_set", f"{[str(t) for t in first_set]}")

    def compute_follow_sets(self) -> None:
        self.follow_set[self.start].add("_EOF")

        for follow_set in stabilize_2d(self.follow_set):
            for rule in self.rules:
                for i, term in enumerate(rule.terms):
                    if isinstance(term, gm.NonTerminalTerm):
                        nt = self.nt(term)
                        for next_term in rule.terms[i + 1 :]:
                            if isinstance(next_term, gm.TerminalTerm):
                                follow_set[nt].add(next_term.name)
                                break
                            elif isinstance(next_term, gm.NonTerminalTerm):
                                follow_set[nt].update(self.first_set[self.nt(next_term)])
                                if not self.is_nullable[self.nt(next_term)]:
                                    break
                        else:
                            follow_set[nt].update(follow_set[rule.nt])

        for nt, follow_set in sorted(self.follow_set.items(), key=lambda item: item[0].name):
            report.nt_info(nt.name, "follow_set", f"{[str(t) for t in follow_set]}")

    def compute_parsing_table(self) -> dict[gm.NonTerminal, dict[gm.Term, gm.Rule]]:
        result: dict[gm.NonTerminal, dict[gm.Term, int]] = {rule.nt: {} for rule in self.rules}
        modes: dict[gm.NonTerminal, dict[gm.Term, str]] = {rule.nt: {} for rule in self.rules}

        def add_entry(nt: gm.NonTerminal, term: str, rule_idx: int, mode: str) -> None:
            rule = self.rules[rule_idx]
            if term in result[nt] and result[nt][term] != rule_idx:
                cur_rule = self.rules[result[nt][term]]
                report.nt_info(
                    nt.name,
                    f"conflict on {str(term)}",
                    f"{modes[nt][term]} rule {result[nt][term]}: {str(cur_rule.nt.name)} vs {mode} rule {rule_idx}: {str(rule.nt.name)}",
                )
            result[nt][term] = rule_idx
            modes[nt][term] = mode

        for i, rule in enumerate(self.rules):
            for term in rule.terms:
                if isinstance(term, gm.TerminalTerm):
                    add_entry(rule.nt, term.name, i, "shift")
                    break
                elif isinstance(term, gm.NonTerminalTerm):
                    for first in self.first_set[self.nt(term)]:
                        add_entry(rule.nt, first, i, "shift")

                    if self.is_nullable[self.nt(term)]:
                        for follow in self.follow_set[rule.nt]:
                            add_entry(rule.nt, follow, i, "reduce")
                    else:
                        break
            if self.is_nullable[rule.nt] and not rule.terms:
                for follow in self.follow_set[rule.nt]:
                    add_entry(rule.nt, follow, i, "reduce")

        for nt, table in sorted(result.items(), key=lambda item: item[0].name):
            for term, rule in sorted(table.items(), key=lambda item: str(item[0])):
                report.nt_info(
                    nt.name, f"parse_table[{str(term)}]", f"{rule}: {str(self.rules[rule])}"
                )

        return result

    def compute(self) -> dict[gm.NonTerminal, dict[gm.Term, gm.Rule]]:
        self.compute_nullable()
        self.compute_first_sets()
        self.compute_follow_sets()
        return self.compute_parsing_table()
