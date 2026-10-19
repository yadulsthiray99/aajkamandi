// Run the workflow's own `run:` scripts locally, in order, exactly as written in daily.yml
// (no copy that can drift). Usage: node scripts/ci_local.mjs [--skip-npm-ci] [--no-deploy]
// Env: DATA_GOV_API_KEY must be set. Simulates a manual run (MANUAL=true, POLL=false).
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import yaml from 'js-yaml';

const wf = yaml.load(readFileSync('.github/workflows/daily.yml', 'utf8'));
const skipNpmCi = process.argv.includes('--skip-npm-ci');
const noDeploy = process.argv.includes('--no-deploy');
const out = join(mkdtempSync(join(tmpdir(), 'ci-')), 'out');
writeFileSync(out, '');
const env = { ...process.env, ...wf.env, POLL: 'false', MANUAL: 'true', GITHUB_OUTPUT: out,
  FETCH_RELAY: wf.env.FETCH_RELAY };
for (const [k, v] of Object.entries(env)) if (typeof v === 'string' && v.includes('${{')) delete env[k];
env.POLL = 'false'; env.MANUAL = 'true';

for (const step of wf.jobs.update.steps) {
  if (!step.run) continue;
  if (noDeploy && /Deploy|Commit/.test(step.name)) { console.log(`-- skip (no-deploy): ${step.name}`); continue; }
  if (/Source unreachable/.test(step.name)) continue; // only runs on failure
  if (/Check secrets/.test(step.name)) continue;      // secrets come from GitHub
  let script = step.run;
  if (skipNpmCi) script = script.replace(/^\s*npm ci\s*$/m, 'echo "(npm ci skipped locally)"');
  console.log(`\n== ${step.name}`);
  try {
    execSync(script, { stdio: 'inherit', env, shell: 'bash' });
  } catch (e) {
    console.error(`\nSTEP FAILED: ${step.name}`);
    process.exit(1);
  }
}
console.log('\nALL STEPS PASSED');
