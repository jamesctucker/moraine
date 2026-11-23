"""Sloppy fixture for the slop-fixture-sloppy golden task.

Must score verbosity >= 0.30. If this fixture starts failing without being
edited, the slop-check detectors have rotted (rules no longer fire, clone
detection broken) and need repair. Deliberately terrible code — do not
"fix" it.
"""


def double(x):
    return x * 2


def helper_double(x):
    return double(x)


def process_items(items):
    results = [x for x in items]
    if len(results) == 0:
        return []
    if len(results) > 0:
        total = 0
        for x in results:
            total = total + x
        if total > 100:
            return True
        return False
    return []


def load_config(path):
    try:
        f = open(path)
        data = f.read()
        return data
    except Exception:
        pass


def save_config(path, data):
    try:
        f = open(path, "w")
        f.write(data)
    except IOError:
        pass


def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def render_report_a(rows):
    out = []
    for row in rows:
        name = row["name"]
        status = row["status"]
        value = row["value"]
        created = row["created"]
        updated = row["updated"]
        owner = row["owner"]
        line = f"{name}|{status}|{value}|{created}|{updated}|{owner}"
        out.append(line)
    return out


def render_report_b(rows):
    out = []
    for row in rows:
        name = row["name"]
        status = row["status"]
        value = row["value"]
        created = row["created"]
        updated = row["updated"]
        owner = row["owner"]
        line = f"{name}|{status}|{value}|{created}|{updated}|{owner}"
        out.append(line)
    return out


def deep_handler(node):
    if node is not None:
        if node.children:
            for child in node.children:
                if child.visible:
                    if child.enabled:
                        return child
    return None
