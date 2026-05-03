# Calculator tool (AST-safe eval)

Letting an LLM (or user) supply a **string** that you pass straight to **`eval()`** is dangerous: you would execute arbitrary Python. This example treats the string as a **math expression only**: it is parsed with **`ast.parse(..., mode="eval")`**, then walked with a tiny recursive evaluator that only allows **numeric constants**, binary operators (add, subtract, multiply, divide, power), and unary minus. Anything else raises **`ValueError`**.

The **`CalcParams`** model is what you register in [tool_router](../tool_router/CODE.md): the LLM fills **`expression`**, Pydantic validates it is a string, and your code never sees unchecked types.

---

## Runnable

Run **[`calculator_tool.py`](./calculator_tool.py)**; **`__main__`** evaluates **`(2+3)*4`** once and prints the result.

```bash
uv run python 07_tools/calculator_tool/calculator_tool.py
```

---

## Code walkthrough (`calculator_tool.py`)

### 1. Map AST operator nodes to real functions

Instead of interpreting opcodes by hand in nested `if` chains, we map each allowed **`ast`** operator class to a function from the **`operator`** module. That list is the **whitelist**: if the tree contains any other operator, **`_eval`** will not find it in **`_OPS`** and will fail.

```python
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}
```

**Takeaway:** extending the calculator means adding entries here **and** matching branches in **`_eval`**—keep those two in sync.

---

### 2. Pydantic input: one field, JSON Schema description

The **`Field(..., description=...)`** text is copied into the tool’s JSON Schema when the model is registered. That helps the LLM know the expected format (e.g. parenthesis-heavy expressions).

```python
class CalcParams(BaseModel):
    expression: str = Field(..., description="Arithmetic like (2+3)*4")
```

**Takeaway:** the tool’s **contract** with the model lives in the schema; the AST code is the **trust boundary** after validation.

---

### 3. Recursive `_eval` on a small subset of nodes

**`_eval`** only handles three shapes: numeric **`ast.Constant`**, binary **`ast.BinOp`** whose **`node.op`** is in **`_OPS`**, and unary **`ast.UnaryOp`** with **`ast.USub`**. Every other node type hits **`ValueError("unsupported expression")`**.

```python
def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ValueError("unsupported expression")
```

**Takeaway:** there is **no** **`ast.Name`**, **no** attribute access, **no** function calls—so **`__import__`**-style escapes are impossible from this tree.

---

### 4. `calculator_eval`: parse once, evaluate the body, return text

**`mode="eval"`** gives a single expression; **`tree.body`** is that expression’s root node. The return type is **`str`** so the registry and LLM always see a plain string (e.g. **`"20.0"`**), not a raw float JSON type.

```python
def calculator_eval(params: CalcParams) -> str:
    tree = ast.parse(params.expression, mode="eval")
    v = _eval(tree.body)
    return str(v)
```

**Takeaway:** **`ast.parse`** can still raise **`SyntaxError`** for malformed input; you may want to catch that at the agent layer and return an error string to the model.
