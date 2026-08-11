#!/usr/bin/env bash
# Ringer adapter for exact OpenRouter text selectors through Pi.
set -o pipefail

fail() {
  printf 'pi-openrouter-ringer: %s\n' "$1" >&2
  exit "${2:-64}"
}

usage() {
  printf 'usage: %s <taskdir> <model> <spec>\n' "${0##*/}" >&2
}

if [[ $# -ne 3 ]]; then
  usage
  exit 64
fi

taskdir=$1
requested_model=$2
spec=$3
agent_dir=${RINGER_PI_OPENROUTER_AGENT_DIR:-"$HOME/.pi/agent"}
test_mode=${RINGER_PI_OPENROUTER_TEST_MODE-}

if [[ ! -d $taskdir ]]; then
  fail 'task directory does not exist'
fi
if [[ -L $taskdir ]]; then
  fail 'task directory must not be a symbolic link'
fi
if ! canonical_taskdir=$(realpath -e -- "$taskdir") || [[ ! -d $canonical_taskdir ]]; then
  fail 'could not canonicalize task directory'
fi
case "$canonical_taskdir" in
  /|/bin|/boot|/dev|/etc|/home|/lib|/lib64|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/var)
    fail 'refusing unsafe root task directory'
    ;;
esac
if [[ $canonical_taskdir == "$HOME" ]]; then
  fail 'refusing unsafe home task directory'
fi
if ! canonical_agent_dir=$(realpath -e -- "$agent_dir") || [[ ! -d $canonical_agent_dir ]]; then
  fail 'could not canonicalize Pi agent directory'
fi
case "$canonical_taskdir:$canonical_agent_dir" in
  "$canonical_agent_dir:$canonical_agent_dir"|"$canonical_agent_dir"/*:*|*:"$canonical_taskdir"/*)
    fail 'task directory overlaps Pi agent directory'
    ;;
esac
if [[ ! $requested_model =~ ^openrouter/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._:+-]*$ ]]; then
  fail 'model must be an exact lowercase openrouter/<publisher>/<model> selector'
fi
if [[ ! -f $canonical_agent_dir/auth.json ]]; then
  fail 'Pi auth metadata is missing'
fi

if [[ $test_mode == 1 && -n ${RINGER_TEST_BWRAP_BIN-} ]]; then
  bwrap_bin=$RINGER_TEST_BWRAP_BIN
else
  bwrap_bin=/usr/bin/bwrap
fi
if [[ $bwrap_bin != /* || ! -x $bwrap_bin || ! -f $bwrap_bin ]]; then
  fail 'bubblewrap is unavailable; refusing to launch Pi unconfined' 127
fi
if ! bwrap_bin=$(realpath -e -- "$bwrap_bin") || [[ $bwrap_bin != /* || ! -x $bwrap_bin ]]; then
  fail 'bubblewrap path is unsafe; refusing to launch Pi unconfined' 127
fi

if [[ ! -x /usr/bin/node ]] || ! node_source=$(realpath -e -- /usr/bin/node); then
  fail 'required /usr/bin/node runtime is unavailable' 127
fi
case "$node_source" in
  /usr/bin/node|/usr/bin/node-[0-9]*|/usr/bin/node[0-9]*)
    ;;
  *)
    fail 'resolved /usr/bin/node runtime path is untrusted' 127
    ;;
esac
if [[ ! -f $node_source || ! -x $node_source ]]; then
  fail 'resolved /usr/bin/node runtime is unusable' 127
fi

if [[ $test_mode == 1 ]]; then
  if [[ -z ${RINGER_TEST_PI_BIN-} || ${RINGER_TEST_PI_BIN} != /* || ! -f ${RINGER_TEST_PI_BIN} ]]; then
    fail 'test Pi JavaScript worker is unavailable'
  fi
  if ! pi_source=$(realpath -e -- "$RINGER_TEST_PI_BIN") || [[ $pi_source != /* || ! -f $pi_source ]]; then
    fail 'test Pi JavaScript worker path is unsafe'
  fi
  pi_mount_source=$pi_source
  pi_mount_target=/opt/pi-test.js
  pi_command=(/runtime/bin/node /opt/pi-test.js)
else
  pi_bin=$(type -P pi) || true
  if [[ -z $pi_bin ]] || ! pi_cli=$(realpath -e -- "$pi_bin"); then
    fail 'could not locate the Pi package entrypoint' 127
  fi
  pi_package=${pi_cli%/dist/cli.js}
  if [[ $pi_package == "$pi_cli" || ! -f $pi_package/package.json || ! -f $pi_package/dist/cli.js ]]; then
    fail 'installed Pi package layout is unsupported' 127
  fi
  if ! canonical_pi_package=$(realpath -e -- "$pi_package") || [[ ! -d $canonical_pi_package ]]; then
    fail 'installed Pi package path is unsafe' 127
  fi
  case "$canonical_taskdir:$canonical_pi_package" in
    "$canonical_pi_package:$canonical_pi_package"|"$canonical_pi_package"/*:*|*:"$canonical_taskdir"/*)
      fail 'task directory overlaps installed Pi package'
      ;;
  esac
  if ! python3 - "$canonical_pi_package/package.json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "rb") as source:
        package = json.load(source)
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    raise SystemExit(1)
if (
    not isinstance(package, dict)
    or package.get("name") != "@earendil-works/pi-coding-agent"
    or not isinstance(package.get("bin"), dict)
    or package["bin"].get("pi") != "dist/cli.js"
):
    raise SystemExit(1)
PY
  then
    fail 'installed Pi package layout is unsupported' 127
  fi
  pi_mount_source=$canonical_pi_package
  pi_mount_target=/opt/pi-package
  pi_command=(/runtime/bin/node /opt/pi-package/dist/cli.js)
fi

old_umask=$(umask)
umask 077
runtime_agent_dir=$(mktemp -d "${TMPDIR:-/tmp}/pi-openrouter-agent.XXXXXX") || {
  umask "$old_umask"
  fail 'could not create ephemeral agent directory' 1
}
tmpfile=$(mktemp "${TMPDIR:-/tmp}/pi-openrouter-ringer.XXXXXX") || {
  rm -rf -- "$runtime_agent_dir"
  umask "$old_umask"
  fail 'could not create temporary output' 1
}
statusfile=$(mktemp "${TMPDIR:-/tmp}/pi-openrouter-status.XXXXXX") || {
  rm -f -- "$tmpfile"
  rm -rf -- "$runtime_agent_dir"
  umask "$old_umask"
  fail 'could not create temporary status' 1
}
umask "$old_umask"
cleanup() {
  rm -f -- "$tmpfile" "$statusfile"
  chmod u+w -- "$runtime_agent_dir" 2>/dev/null || true
  chmod u+w -- "$runtime_agent_dir/models-store.json" 2>/dev/null || true
  rm -rf -- "$runtime_agent_dir"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

runtime_manifest=$runtime_agent_dir/node-runtime.tsv
if ! /usr/bin/ldd -- "$node_source" >"$runtime_agent_dir/node.ldd" 2>/dev/null; then
  fail 'could not resolve Node shared-library dependencies' 127
fi
# Minimal Fedora-family hosts ship without binutils, so /usr/bin/readelf can be
# absent entirely (observed 2026-08-04: no readelf, objdump, eu-readelf, or
# llvm-readelf, and neither binutils nor elfutils installed). That made every
# pi-openrouter task exit 127 before the model was ever called. Prefer readelf
# when it exists; otherwise read PT_INTERP straight out of the ELF program
# headers and emit the identical single line the parser below consumes. The
# downstream trusted_file() validation is untouched either way, so the trust
# boundary does not move.
if [[ -x /usr/bin/readelf ]]; then
  if ! /usr/bin/readelf -lW -- "$node_source" >"$runtime_agent_dir/node.readelf" 2>/dev/null; then
    fail 'could not resolve Node ELF interpreter' 127
  fi
elif ! python3 - "$node_source" >"$runtime_agent_dir/node.readelf" 2>/dev/null <<'PY'
import struct
import sys

with open(sys.argv[1], "rb") as handle:
    header = handle.read(64)
    if len(header) < 64 or header[:4] != b"\x7fELF":
        raise SystemExit(1)
    is64 = header[4] == 2
    endian = "<" if header[5] == 1 else ">"
    if is64:
        e_phoff = struct.unpack_from(endian + "Q", header, 0x20)[0]
        e_phentsize = struct.unpack_from(endian + "H", header, 0x36)[0]
        e_phnum = struct.unpack_from(endian + "H", header, 0x38)[0]
    else:
        e_phoff = struct.unpack_from(endian + "I", header, 0x1C)[0]
        e_phentsize = struct.unpack_from(endian + "H", header, 0x2A)[0]
        e_phnum = struct.unpack_from(endian + "H", header, 0x2C)[0]
    handle.seek(e_phoff)
    for _ in range(e_phnum):
        entry = handle.read(e_phentsize)
        if len(entry) < e_phentsize:
            raise SystemExit(1)
        if struct.unpack_from(endian + "I", entry, 0)[0] != 3:  # PT_INTERP
            continue
        if is64:
            p_offset = struct.unpack_from(endian + "Q", entry, 8)[0]
            p_filesz = struct.unpack_from(endian + "Q", entry, 32)[0]
        else:
            p_offset = struct.unpack_from(endian + "I", entry, 4)[0]
            p_filesz = struct.unpack_from(endian + "I", entry, 16)[0]
        handle.seek(p_offset)
        raw = handle.read(p_filesz).split(b"\x00", 1)[0]
        print("      [Requesting program interpreter: %s]" % raw.decode("ascii"))
        raise SystemExit(0)
raise SystemExit(1)
PY
then
  fail 'could not resolve Node ELF interpreter' 127
fi
if ! python3 - "$runtime_agent_dir/node.ldd" "$runtime_agent_dir/node.readelf" "$runtime_manifest" <<'PY'
import os
import re
import sys

ldd_path, readelf_path, output_path = sys.argv[1:]
allowed_roots = ("/lib/", "/lib64/", "/usr/lib/", "/usr/lib64/")
line_with_name = re.compile(r"^\s*\S+\s+=>\s+(/\S+)\s+\(0x[0-9a-fA-F]+\)\s*$")
line_absolute = re.compile(r"^\s*(/\S+)\s+\(0x[0-9a-fA-F]+\)\s*$")
vdso = re.compile(r"^\s*linux-vdso\.so\.\d+\s+\(0x[0-9a-fA-F]+\)\s*$")
interp_line = re.compile(r"^\s*\[Requesting program interpreter:\s*(/\S+)\]\s*$")

def trusted_file(raw):
    if not raw.startswith(allowed_roots) or any(c.isspace() for c in raw):
        raise ValueError
    canonical = os.path.realpath(raw)
    if not canonical.startswith(allowed_roots) or not os.path.isfile(canonical):
        raise ValueError
    return canonical

dependencies = []
with open(ldd_path, encoding="utf-8") as source:
    for raw_line in source:
        line = raw_line.rstrip("\n")
        if not line.strip() or vdso.fullmatch(line):
            continue
        if "not found" in line:
            raise ValueError
        match = line_with_name.fullmatch(line) or line_absolute.fullmatch(line)
        if match is None:
            raise ValueError
        requested = match.group(1)
        dependencies.append((os.path.basename(requested), trusted_file(requested)))
if not dependencies:
    raise ValueError

interpreters = []
with open(readelf_path, encoding="utf-8") as source:
    for raw_line in source:
        match = interp_line.fullmatch(raw_line.rstrip("\n"))
        if match:
            requested = match.group(1)
            interpreters.append((trusted_file(requested), requested))
if len(interpreters) != 1:
    raise ValueError
interpreter_source, interpreter_target = interpreters[0]

by_basename = {}
for basename, path in dependencies:
    previous = by_basename.setdefault(basename, path)
    if previous != path:
        raise ValueError
with open(output_path, "x", encoding="utf-8") as output:
    output.write("interpreter\t" + interpreter_source + "\t" + interpreter_target + "\n")
    for basename, path in sorted(by_basename.items()):
        output.write("library\t" + path + "\t" + basename + "\n")
PY
then
  fail 'Node runtime dependency resolution was malformed or unsafe' 127
fi

runtime_mount_args=()
elf_interpreter_source=
elf_interpreter_target=
while IFS=$'\t' read -r kind source basename extra; do
  if [[ $kind == interpreter && -n $basename && -z $extra ]]; then
    elf_interpreter_source=$source
    elf_interpreter_target=$basename
  elif [[ $kind == library && -n $basename && -z $extra ]]; then
    runtime_mount_args+=(--ro-bind "$source" "/runtime/lib/$basename")
  else
    fail 'Node runtime dependency manifest was malformed' 127
  fi
done <"$runtime_manifest"
if [[ -z $elf_interpreter_source || -z $elf_interpreter_target || ${#runtime_mount_args[@]} -eq 0 ]]; then
  fail 'Node runtime dependency manifest was incomplete' 127
fi
interpreter_parent=${elf_interpreter_target%/*}
case "$interpreter_parent" in
  /lib|/lib64)
    interpreter_dir_args=(--dir "$interpreter_parent")
    ;;
  /usr/lib|/usr/lib64)
    interpreter_dir_args=(--dir "$interpreter_parent")
    ;;
  *)
    fail 'Node ELF interpreter directory was untrusted' 127
    ;;
esac
rm -f -- "$runtime_agent_dir/node.ldd" "$runtime_agent_dir/node.readelf" "$runtime_manifest"

# Fedora-family hosts keep the OpenSSL trust store under /etc/pki (OPENSSLDIR is
# /etc/pki/tls, and openssl.cnf includes /etc/crypto-policies), so /etc/ssl/certs
# alone leaves TLS unable to build a chain inside the sandbox. Both trees are
# public trust material; mount them read-only only where they exist.
ca_trust_mount_args=()
if [[ -d /etc/pki ]]; then
  ca_trust_mount_args+=(--ro-bind /etc/pki /etc/pki)
fi
if [[ -d /etc/crypto-policies ]]; then
  ca_trust_mount_args+=(--ro-bind /etc/crypto-policies /etc/crypto-policies)
fi
# The back-ends/*.config entries are symlinks into /usr/share/crypto-policies.
if [[ -d /usr/share/crypto-policies ]]; then
  ca_trust_mount_args+=(--ro-bind /usr/share/crypto-policies /usr/share/crypto-policies)
fi

# models.json is deliberately ignored. Only the exact cached OpenRouter model
# and pinned endpoint are copied into the isolated runtime agent directory.
# auth.json is never copied or mounted. The launch supervisor below is its
# only reader, pinning the validated key in memory for launch and redaction.
if python3 - "$canonical_agent_dir/models-store.json" \
  "$runtime_agent_dir/models-store.json" \
  "${requested_model#openrouter/}" <<'PY'
import json
import os
import sys

models_source, models_dest, requested_id = sys.argv[1:]
endpoint = "https://openrouter.ai/api/v1"
try:
    with open(models_source, "rb") as source:
        store = json.load(source)
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    raise SystemExit(2)
provider_cache = store.get("openrouter") if isinstance(store, dict) else None
models = provider_cache.get("models") if isinstance(provider_cache, dict) else None
if not isinstance(models, list):
    raise SystemExit(2)
matches = [
    model for model in models
    if isinstance(model, dict) and model.get("id") == requested_id
]
if len(matches) != 1:
    raise SystemExit(2)
model = matches[0]
if model.get("provider") != "openrouter" or model.get("baseUrl") != endpoint:
    raise SystemExit(2)

# Keep Pi's documented model fields, but discard routing-capable headers and
# every unknown cache field. JSON round-tripping also rejects non-JSON data.
allowed = (
    "id", "name", "api", "provider", "baseUrl", "reasoning", "input",
    "cost", "contextWindow", "maxTokens", "compat",
)
sanitized = {key: model[key] for key in allowed if key in model}
if sanitized.get("id") != requested_id:
    raise SystemExit(2)
if sanitized.get("provider") != "openrouter":
    raise SystemExit(2)
if sanitized.get("baseUrl") != endpoint:
    raise SystemExit(2)
try:
    encoded_models = json.dumps(
        {"openrouter": {"models": [sanitized]}},
        separators=(",", ":"),
        allow_nan=False,
    )
except (TypeError, ValueError):
    raise SystemExit(2)
with open(models_dest, "x", encoding="utf-8") as destination:
    destination.write(encoded_models)
os.chmod(models_dest, 0o400)
os.chmod(os.path.dirname(models_dest), 0o500)
PY
then
  :
else
  fail 'exact OpenRouter model cache is missing or malformed'
fi

bwrap_argv=(
  "$bwrap_bin"
    --die-with-parent \
    --new-session \
    --unshare-user \
    --unshare-ipc \
    --unshare-pid \
    --unshare-uts \
    --unshare-cgroup \
    --tmpfs / \
    --dir /usr \
    --dir /usr/share \
    --ro-bind /usr/share/zoneinfo /usr/share/zoneinfo \
    --dir /runtime \
    --dir /runtime/bin \
    --dir /runtime/lib \
    --ro-bind "$node_source" /runtime/bin/node \
    "${runtime_mount_args[@]}" \
    "${interpreter_dir_args[@]}" \
    --ro-bind "$elf_interpreter_source" "$elf_interpreter_target" \
    --dir /etc \
    --ro-bind /etc/hosts /etc/hosts \
    --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --ro-bind /etc/nsswitch.conf /etc/nsswitch.conf \
    --dir /etc/ssl \
    --ro-bind /etc/ssl/certs /etc/ssl/certs \
    "${ca_trust_mount_args[@]}" \
    --dev /dev \
    --tmpfs /tmp \
    --dir /tmp/home \
    --dir /opt \
    --ro-bind "$pi_mount_source" "$pi_mount_target" \
    --bind "$canonical_taskdir" /workspace \
    --ro-bind "$runtime_agent_dir" /agent \
    --remount-ro / \
    --chdir /workspace \
    "${pi_command[@]}" \
    --print \
    --mode json \
    --no-session \
    --no-extensions \
    --no-skills \
    --no-prompt-templates \
    --no-themes \
    --no-context-files \
    --approve \
    --tools read,write,edit \
    --model "$requested_model" \
    --thinking high \
    "$spec"
)

# One supervisor owns the credential-bearing boundary. It opens auth.json once,
# retains the validated key only in memory, launches bubblewrap with a
# from-scratch environment, captures the combined transcript, and redacts any
# exact leak before reporting non-secret status to the shell.
python3 - "$canonical_agent_dir/auth.json" "$tmpfile" "$statusfile" "${bwrap_argv[@]}" <<'PY'
import json
import os
import subprocess
import sys

auth_source, transcript_path, status_path = sys.argv[1:4]
argv = sys.argv[4:]
status = {
    "child_status": None,
    "credential_leak": False,
    "supervisor_error": True,
    "auth_error": True,
}
try:
    with open(auth_source, "rb") as source:
        auth = json.load(source)
    entry = auth.get("openrouter") if isinstance(auth, dict) else None
    key = entry.get("key") if isinstance(entry, dict) else None
    if (
        not isinstance(entry, dict)
        or entry.get("type") != "api_key"
        or not isinstance(key, str)
        or not key.strip()
        or key.startswith(("!", "$"))
    ):
        raise ValueError
    status["auth_error"] = False
    needle = key.encode("utf-8")
    clean_env = {
        "HOME": "/tmp/home",
        "PATH": "/runtime/bin",
        "LD_LIBRARY_PATH": "/runtime/lib",
        "PI_CODING_AGENT_DIR": "/agent",
        "PI_OFFLINE": "1",
        "OPENROUTER_API_KEY": key,
    }
    with open(transcript_path, "wb") as transcript_file:
        child = subprocess.run(
            argv,
            env=clean_env,
            stdout=transcript_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
        child_status = child.returncode
    with open(transcript_path, "rb") as transcript_file:
        transcript = transcript_file.read()
    credential_leak = needle in transcript
    if credential_leak:
        with open(transcript_path, "wb") as transcript_file:
            transcript_file.write(transcript.replace(needle, b"[REDACTED]"))
    status = {
        "child_status": child_status,
        "credential_leak": credential_leak,
        "supervisor_error": False,
        "auth_error": False,
    }
except BaseException:
    pass
# Deliberately do not use os.execve: the same process must retain the pinned
# key after the child exits so it can redact the captured transcript.
try:
    with open(status_path, "w", encoding="utf-8") as status_file:
        json.dump(status, status_file, separators=(",", ":"))
except BaseException:
    raise SystemExit(1)
PY

if ! supervisor_status=$(python3 - "$statusfile" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as source:
        status = json.load(source)
    child = status["child_status"]
    leak = status["credential_leak"]
    error = status["supervisor_error"]
    auth_error = status["auth_error"]
    if child is not None and (type(child) is not int or child < 0 or child > 255):
        raise ValueError
    if type(leak) is not bool or type(error) is not bool or type(auth_error) is not bool:
        raise ValueError
except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
    raise SystemExit(1)
print(f"{-1 if child is None else child} {int(leak)} {int(error)} {int(auth_error)}")
PY
); then
  cleanup
  trap - EXIT
  fail 'child supervisor failed' 1
fi
read -r child_status credential_leak supervisor_error auth_error <<<"$supervisor_status"
if [[ $supervisor_error -ne 0 ]]; then
  cleanup
  trap - EXIT
  if [[ $auth_error -ne 0 ]]; then
    fail 'Pi auth metadata is malformed'
  fi
  fail 'child supervisor failed' 1
fi
if [[ $credential_leak -ne 0 ]]; then
  cleanup
  trap - EXIT
  fail 'credential leak detected in child transcript' 1
fi

cat -- "$tmpfile"
if [[ -s $tmpfile ]] && [[ $(tail -c 1 -- "$tmpfile" | od -An -t x1) != *0a* ]]; then
  printf '\n'
fi
if [[ $child_status -ne 0 ]]; then
  exit "$child_status"
fi

expected_model=${requested_model#openrouter/}
if ! accounting=$(python3 - "$tmpfile" "$expected_model" <<'PY'
import json
import math
import sys

path = sys.argv[1]
expected_model = sys.argv[2]
fields = ("input", "output", "cacheRead", "cacheWrite", "totalTokens")
totals = {field: 0 for field in fields}
cost_fields = ("input", "output", "cacheRead", "cacheWrite", "total")
costs = {field: 0.0 for field in cost_fields}
assistant_messages = 0
try:
    with open(path, "rb") as source:
        for raw_line in source:
            try:
                record = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(record, dict):
                continue
            if record.get("type") in ("error", "abort", "aborted"):
                raise ValueError("error or abort record")
            if record.get("type") != "message_end":
                continue
            message = record.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            assistant_messages += 1
            if message.get("stopReason") in ("error", "aborted"):
                raise ValueError("assistant message ended in error or abort")
            if message.get("errorMessage"):
                raise ValueError("assistant message contains an error")
            provider = message.get("provider")
            model = message.get("model")
            if provider != "openrouter" or model != expected_model:
                raise ValueError("assistant identity did not match requested OpenRouter model")
            usage = message.get("usage")
            if not isinstance(usage, dict):
                raise ValueError("assistant message has no usage object")
            for field in fields:
                value = usage.get(field)
                if type(value) is not int or value < 0:
                    raise ValueError(f"invalid usage.{field}")
                totals[field] += value
            cost = usage.get("cost")
            if not isinstance(cost, dict):
                raise ValueError("assistant message has no usage.cost object")
            for field in cost_fields:
                value = cost.get(field)
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError(f"invalid usage.cost.{field}")
                costs[field] += float(value)
except (OSError, ValueError) as error:
    print(f"pi-openrouter-ringer: invalid assistant accounting: {error}", file=sys.stderr)
    raise SystemExit(1)
if assistant_messages == 0:
    print("pi-openrouter-ringer: no assistant message_end record", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps({"provider": "openrouter", "model": expected_model}, separators=(",", ":")))
print(json.dumps(totals, separators=(",", ":")))
print(json.dumps(costs, separators=(",", ":")))
PY
); then
  exit 1
fi

identity_json=${accounting%%$'\n'*}
remaining=${accounting#*$'\n'}
usage_json=${remaining%%$'\n'*}
cost_json=${remaining#*$'\n'}
cleanup
trap - EXIT
printf 'RINGER_PI_IDENTITY %s\n' "$identity_json"
printf 'RINGER_PI_USAGE %s\n' "$usage_json"
printf 'RINGER_PI_COST %s\n' "$cost_json"
printf 'tokens used: %s\n' "$(python3 - "$usage_json" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["totalTokens"])
PY
)"
