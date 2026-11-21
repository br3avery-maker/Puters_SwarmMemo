// Executed only by the manually authorized story job, in an ephemeral runner.
// Import the exact upstream source already pinned in the workflow. Never print
// the credential, remote signer errors, or signing-client state.
import { resolvePubkey } from '../.nsyte-upstream/src/lib/resolver-utils.ts';
const expected = 'ab71b3f86d3428d62530dbe7344995188eaa8197db23b3a45c3eb3cac6ae3e45';
const secret = Deno.env.get('NBUNK_SECRET') ?? '';
if (!secret.startsWith('nbunksec1')) Deno.exit(2);
try {
  const actual = await resolvePubkey({sec: secret}, null, false);
  if (actual !== expected) Deno.exit(3);
  Deno.exit(0);
} catch {
  Deno.exit(4);
}
