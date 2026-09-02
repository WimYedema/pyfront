# LL(1) Grammar notes

## FIRST/FIRST Conflict

Example:

```
S ::= A b
S ::= A c
A ::= x
```

Solution:

```
S ::= A B
A ::= x
B ::= b
B ::= c
```

Example:

```
S ::= A b
S ::= B c
A ::= C y
B ::= x z
C ::= x
```

Inline:

```
S ::= x [C] y [A] b
S ::= x z [B] c
```
non-recursive rules can always be inlined

Example:

```
S ::= A b
S ::= B c
A ::= C y
B ::= x z
B ::= p q
C ::= x
```

Inline:

```
S ::= x [C] y [A] b
S ::= x z [B] c
S ::= p q [B] c
```
