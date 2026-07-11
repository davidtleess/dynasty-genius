Use the dg-pm write-spec skill.

When a player lookup fails, the API logs a raw Python traceback to stdout instead of a structured, caveated response — so a failed lookup can look like a crash and there's no honest signal to the caller. Spec the fix.
