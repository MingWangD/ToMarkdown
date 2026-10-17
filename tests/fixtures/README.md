# Legacy XLS fixture

`legacy-ledger.xls` is a synthetic BIFF workbook created with xlwt 1.3.0 for tests.
It contains no user data. It exercises a merged company cell, a literal pipe and
newline, integer/decimal values, a numeric identifier formatted as `000000`, a
date, a formula with an empty cached result, a boolean, a hidden row/column and
a hidden sheet. xlwt is not a runtime or test dependency: the fixture is committed.
