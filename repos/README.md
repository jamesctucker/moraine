# /repos

Repos this workspace works on — pointers, not copies. Each clone is its own git repo: no submodules, no nesting.

This file is tracked; the clones next to it are gitignored. Register a repo when you clone it, so `moraine repos check` can flag drift and `moraine repos restore` can rebuild a second machine.

## Repos

| Repo | What it is | Path | Remote | Hint |
|------|------------|------|--------|------|

<!-- [CUSTOMIZE] Add one row per repo.

     | storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |

     - Path is relative to this workspace's root, or starts with ~/. The
       default for a new entry is repos/<name>.
     - Remote is required — it is what makes `moraine repos restore` work.
     - Hint is one line. Stack, conventions, and deploy notes belong in the
       child repo's own AGENTS.md, not here.
     - Optional Machines column (comma-separated hostnames; empty = every
       machine) scopes a repo to machines by hostname.
     - Past about 20 repos, replace this table with an Areas table and give
       each area its own file (repos/<area>.md) holding a Repos table:

       | Area | Covers | File |
       |------|--------|------|
       | Billing | invoices, payments, tax | repos/billing.md |
-->
