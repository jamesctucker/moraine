function findHarnessDirs(projectRoot) {
  const dirs = [];
  for (const harness of HARNESS_DIRS) {
    const skillsDir = join(projectRoot, harness, 'skills');
    // Only pin in harness dirs that already have impeccable installed
    // Check top-level and one level of category nesting (e.g. design/impeccable)
    const candidates = [
      join(skillsDir, 'impeccable'),
      join(skillsDir, 'i-impeccable'),
    ];
    try {
      for (const entry of readdirSync(skillsDir, { withFileTypes: true })) {
        if (entry.isDirectory() && entry.name !== 'impeccable' && entry.name !== 'i-impeccable') {
          candidates.push(join(skillsDir, entry.name, 'impeccable'));
        }
      }
    } catch {}
    if (candidates.some(c => existsSync(c))) {
      dirs.push(skillsDir);
    }
  }
  return dirs;
}
