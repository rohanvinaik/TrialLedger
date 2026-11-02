"""semantic_source — code as its syntax tree, docstrings and comments aside.

Positive: comments, docstrings (of a module, a class, a function, a method), blank lines, layout inside
brackets and the indentation of a whole block (a method's source as inspect gives it) leave the text
unchanged; a body that held only a docstring reads as `pass`.
Negative: any change the interpreter would execute differently changes the text: a constant, a name, an
operator, an argument default, a statement's order, a string that is not the first statement of its body, and
a docstring turned into code.
"""

import pytest

from TrialLedger.warrants import semantic_source

BASE = 'def f(x, y=2):\n    """Add."""\n    total = x + y\n    return total\n'


@pytest.mark.parametrize(
    "variant",
    [
        'def f(x, y=2):\n    """Add them, documented at length."""\n    total = x + y\n    return total\n',
        "def f(x, y=2):\n    # a comment\n    total = x + y  # trailing\n\n    return total\n",
        "def f(x, y=2):\n    total = x + y\n    return total\n",
        "def f(\n    x,\n    y=2,\n):\n    total = (\n        x + y\n    )\n    return total\n",
        '    def f(x, y=2):\n        """Add."""\n        total = x + y\n        return total\n',
        '"""Module docstring."""\n' + BASE,
    ],
)
def test_prose_and_layout_leave_the_code_unchanged(variant):
    assert semantic_source(variant) == semantic_source(BASE)


def test_a_class_docstring_is_prose():
    assert semantic_source('class C:\n    """Doc."""\n    A = 1\n') == semantic_source(
        "class C:\n    A = 1\n"
    )


def test_a_body_that_held_only_a_docstring_is_pass():
    assert semantic_source('def f():\n    """Only a docstring."""\n') == semantic_source(
        "def f():\n    pass\n"
    )


@pytest.mark.parametrize(
    "variant",
    [
        'def f(x, y=3):\n    """Add."""\n    total = x + y\n    return total\n',
        'def f(x, y=2):\n    """Add."""\n    total = x - y\n    return total\n',
        'def f(x, z=2):\n    """Add."""\n    total = x + z\n    return total\n',
        'def f(x, y=2):\n    """Add."""\n    total = x + y\n    return x\n',
        'def f(x, y=2):\n    total = x + y\n    """Not a docstring: not first."""\n    return total\n',
        'def f(x, y=2):\n    """Add."""\n    total = x + y\n    return total\n\nLIMIT = 1\n',
        'def f(x, y=2):\n    print("Add.")\n    total = x + y\n    return total\n',
    ],
)
def test_any_executable_change_changes_the_code(variant):
    assert semantic_source(variant) != semantic_source(BASE)


def test_the_canonical_tree_is_written_the_same_under_every_python():
    """Pinned literally, so a Python whose `ast.dump` form differs (3.13 left out empty lists and None) still
    gives this text: 3.12, 3.13 and 3.14 gave the same code root on 2026-11-01."""
    assert semantic_source("def f(a, b=1):\n    return a + b\n") == (
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='a'), arg(arg='b')], "
        "defaults=[Constant(value=1)]), body=[Return(value=BinOp(left=Name(id='a', ctx=Load()), op=Add(), "
        "right=Name(id='b', ctx=Load())))])])"
    )


def test_a_field_that_holds_nothing_is_left_out_and_one_that_holds_something_is_kept():
    import ast

    from TrialLedger.warrants import canonical_tree

    assert canonical_tree(ast.Name(id="x", ctx=ast.Load())) == "Name(id='x', ctx=Load())"
    assert canonical_tree(ast.Constant(value=None)) == "Constant()"
    assert canonical_tree(ast.Constant(value=0)) == "Constant(value=0)"
    assert canonical_tree([]) == "[]" and canonical_tree(["a", 1]) == "['a', 1]"


def test_statement_order_is_code():
    first = "def f():\n    a = 1\n    b = 2\n"
    second = "def f():\n    b = 2\n    a = 1\n"
    assert semantic_source(first) != semantic_source(second)
