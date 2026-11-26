"""check_migrations.py

Validates that a directory of Alembic migration files forms a single,
unbroken, linear chain (root -> ... -> head), with no duplicate revisions,
no dangling references, no forks (two migrations sharing a down_revision),
no merge points with multiple down_revisions, and no cycles.

Usage:
    python check_migrations.py [path_to_versions_dir]

If no path is given, it defaults to "alembic/versions" resolved relative
to this script's own location (i.e. ../alembic/versions from wherever
this file lives), so it works no matter what directory you run it from.

Exit code is 0 if the chain is valid, 1 otherwise (handy for CI).
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Migration:
    file: Path
    revision: str | None = None
    down_revision: object = None  # str, tuple[str, ...], or None
    name: str | None = None
    parse_errors: list[str] = field(default_factory=list)


def extract_migration(path: Path) -> Migration:
    """Parse a migration file with `ast` (no execution) and pull out the
    revision metadata and the first line of the module docstring as the
    human-readable migration name.
    """
    mig = Migration(file=path)

    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        mig.parse_errors.append(f"could not read file: {exc}")
        return mig

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        mig.parse_errors.append(f"syntax error while parsing: {exc}")
        return mig

    docstring = ast.get_docstring(tree)
    if docstring:
        first_line = docstring.strip().splitlines()[0].strip()
        mig.name = first_line
    else:
        mig.name = "<no docstring>"

    wanted = {"revision", "down_revision"}
    found = set()

    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            targets = [node.target]

        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in wanted:
                continue

            value_node = node.value
            if value_node is None:
                continue

            try:
                value = ast.literal_eval(value_node)
            except (ValueError, SyntaxError):
                mig.parse_errors.append(
                    f"could not statically evaluate '{target.id}' "
                    f"(line {node.lineno}) - is it a non-literal expression?"
                )
                continue

            setattr(mig, target.id, value)
            found.add(target.id)

    missing = wanted - found
    if missing:
        mig.parse_errors.append(
            f"missing required field(s): {', '.join(sorted(missing))}"
        )

    return mig


def load_migrations(versions_dir: Path) -> list[Migration]:
    files = sorted(versions_dir.glob("*.py"))
    files = [f for f in files if f.name != "__init__.py"]
    return [extract_migration(f) for f in files]


def normalize_down_revisions(value: object) -> tuple[str, ...]:
    """down_revision may be None, a single string, or a tuple/list of
    strings (merge point). Normalize to a tuple for uniform handling.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (tuple, list)):
        return tuple(value)
    return (str(value),)  # defensive fallback


def main() -> int:
    # scripts/check_migrations.py -> project_root/alembic/versions
    default_versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "versions_dir",
        nargs="?",
        default=str(default_versions_dir),
        help="Path to the directory containing migration files "
        f"(default: {default_versions_dir})",
    )
    args = parser.parse_args()

    versions_dir = Path(args.versions_dir)
    if not versions_dir.is_dir():
        print(f"ERROR: '{versions_dir}' is not a directory.")
        return 1

    migrations = load_migrations(versions_dir)
    if not migrations:
        print(f"No migration files found in '{versions_dir}'.")
        return 1

    errors: list[str] = []

    # --- 1. parse-level errors -------------------------------------------------
    for mig in migrations:
        for err in mig.parse_errors:
            errors.append(f"[{mig.file.name}] {err}")

    usable = [m for m in migrations if m.revision and not m.parse_errors]

    # --- 2. duplicate revision ids ----------------------------------------------
    by_revision: dict[str, list[Migration]] = {}
    for mig in usable:
        by_revision.setdefault(mig.revision, []).append(mig)

    for rev, migs in by_revision.items():
        if len(migs) > 1:
            files = ", ".join(m.file.name for m in migs)
            errors.append(
                f"duplicate revision id '{rev}' used in multiple files: {files}"
            )

    # keep one representative per revision id for graph purposes
    node_by_revision: dict[str, Migration] = {
        rev: migs[0] for rev, migs in by_revision.items()
    }

    # --- 3. dangling down_revision references + build parent->children map -----
    children_of: dict[str, list[Migration]] = {}
    roots: list[Migration] = []
    merges: list[Migration] = []

    for mig in usable:
        parents = normalize_down_revisions(mig.down_revision)

        if len(parents) == 0:
            roots.append(mig)
            continue

        if len(parents) > 1:
            merges.append(mig)

        for parent in parents:
            if parent not in node_by_revision:
                errors.append(
                    f"[{mig.file.name}] revision '{mig.revision}' has "
                    f"down_revision '{parent}' which does not match any "
                    f"known revision in this directory"
                )
                continue
            children_of.setdefault(parent, []).append(mig)

    # --- 4. multiple roots --------------------------------------------------
    if len(roots) > 1:
        files = ", ".join(m.file.name for m in roots)
        errors.append(
            f"multiple root migrations found (down_revision=None): {files}"
        )
    elif len(roots) == 0:
        errors.append(
            "no root migration found (every migration has a down_revision "
            "- possible cycle or all files reference a missing parent)"
        )

    # --- 5. forks: two+ migrations sharing the same down_revision -------------
    for parent_rev, kids in children_of.items():
        if len(kids) > 1:
            parent_name = node_by_revision.get(parent_rev)
            parent_desc = parent_rev if parent_name is None else f"{parent_rev} ({parent_name.name})"
            kid_files = ", ".join(f"{k.file.name} [{k.revision}]" for k in kids)
            errors.append(
                f"branch/fork detected: multiple migrations revise "
                f"'{parent_desc}': {kid_files}"
            )

    # --- 6. merge points (down_revision is a tuple) ----------------------------
    for mig in merges:
        parents = normalize_down_revisions(mig.down_revision)
        errors.append(
            f"[{mig.file.name}] revision '{mig.revision}' is a merge "
            f"migration with multiple down_revisions {parents} - not a "
            f"linear chain"
        )

    # --- 7. cycle detection (only meaningful if no dangling refs so far) ------
    def has_cycle() -> list[str] | None:
        visiting: set[str] = set()
        visited: set[str] = set()
        path_stack: list[str] = []

        def visit(rev: str) -> list[str] | None:
            if rev in visiting:
                cycle_start = path_stack.index(rev)
                return path_stack[cycle_start:] + [rev]
            if rev in visited:
                return None
            visiting.add(rev)
            path_stack.append(rev)
            for child in children_of.get(rev, []):
                result = visit(child.revision)
                if result:
                    return result
            path_stack.pop()
            visiting.discard(rev)
            visited.add(rev)
            return None

        for r in list(node_by_revision.keys()):
            if r not in visited:
                result = visit(r)
                if result:
                    return result
        return None

    cycle = has_cycle()
    if cycle:
        errors.append(f"cycle detected among revisions: {' -> '.join(cycle)}")

    # --- 8. multiple heads (revisions nobody revises) --------------------------
    heads = [m for m in usable if not children_of.get(m.revision)]
    if len(heads) > 1:
        files = ", ".join(f"{h.file.name} [{h.revision}]" for h in heads)
        errors.append(f"multiple head migrations found (ambiguous head): {files}")
    elif len(heads) == 0:
        errors.append(
            "no head migration found (this usually means there's a cycle)"
        )

    # --- report ------------------------------------------------------------
    if errors:
        print(f"FOUND {len(errors)} ERROR(S) in '{versions_dir}':\n")
        for i, err in enumerate(errors, start=1):
            print(f"  {i}. {err}")
        print("\nChain is NOT valid.")
        return 1

    # --- everything's fine: walk the single linear chain root -> head ---------
    order: list[Migration] = []
    current = roots[0]
    seen: set[str] = set()
    while True:
        order.append(current)
        seen.add(current.revision)
        kids = children_of.get(current.revision, [])
        if not kids:
            break
        current = kids[0]

    if len(order) != len(usable):
        # shouldn't happen given the checks above, but guard anyway
        missing = [m for m in usable if m.revision not in seen]
        files = ", ".join(m.file.name for m in missing)
        print(
            "ERROR: chain walk did not cover all migrations - "
            f"disconnected file(s): {files}"
        )
        return 1

    print(f"All {len(order)} migrations are in order. Chain is VALID.\n")
    print("Oldest -> Newest:\n")
    for i, mig in enumerate(order, start=1):
        print(f"  {i:>3}. {mig.revision}  -  {mig.name}   ({mig.file.name})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
