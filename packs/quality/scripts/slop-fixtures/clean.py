"""Clean fixture for the slop-fixture-clean golden task.

Must score erosion <= 0.10 and verbosity <= 0.05. If this fixture starts
failing without being edited, the slop-check detectors are producing false
positives and the rule pack needs tuning.
"""

from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    quantity: int


def line_total(item: Item) -> float:
    return item.price * item.quantity


def order_total(items: list[Item], tax_rate: float) -> float:
    subtotal = 0.0
    for item in items:
        subtotal += line_total(item)
    return subtotal * (1 + tax_rate)


def cheapest(items: list[Item]) -> Item | None:
    best: Item | None = None
    for item in items:
        if best is None or item.price < best.price:
            best = item
    return best


def summarize(items: list[Item]) -> dict[str, float | int | str]:
    total = order_total(items, tax_rate=0.0)
    count = len(items)
    first = ""
    for name in sorted(item.name for item in items):
        first = name
        break
    return {"count": count, "total": total, "first": first}
