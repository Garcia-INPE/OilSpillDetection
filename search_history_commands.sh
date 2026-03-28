#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  search_history_commands.sh <query> [--histfile PATH] [--limit N]

Description:
  Search bash history for <query>, print matching entries with their IDs,
  and print a command chain in the form:
  !xxx; !yyy; !zzz

Options:
  --histfile PATH   Use a specific history file (default: $HISTFILE or ~/.bash_history)
  --limit N         Show only the first N matches
  --execute         Execute all matched commands directly (no confirmation)
  -h, --help        Show this help
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

query=""
histfile="${HISTFILE:-$HOME/.bash_history}"
limit=""
execute=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --histfile)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --histfile requires a path" >&2
        exit 1
      fi
      histfile="$2"
      shift 2
      ;;
    --limit)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --limit requires a number" >&2
        exit 1
      fi
      if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "[ERROR] --limit must be a non-negative integer" >&2
        exit 1
      fi
      limit="$2"
      shift 2
      ;;
    --execute)
      execute=1
      shift
      ;;
    --*)
      echo "[ERROR] Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -z "$query" ]]; then
        query="$1"
      else
        query+=" $1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$query" ]]; then
  echo "[ERROR] Missing query string" >&2
  usage
  exit 1
fi

if [[ ! -f "$histfile" ]]; then
  echo "[ERROR] History file not found: $histfile" >&2
  exit 1
fi

# Parse history file directly and use line numbers as IDs.
# These IDs can be used in the current shell if its history aligns with this file.
if [[ -n "$limit" ]]; then
  mapfile -t match_lines < <(nl -ba "$histfile" | grep -i -- "$query" | head -n "$limit" || true)
else
  mapfile -t match_lines < <(nl -ba "$histfile" | grep -i -- "$query" || true)
fi

if [[ ${#match_lines[@]} -eq 0 ]]; then
  echo "No history entries matched: $query"
  exit 0
fi

echo "Matching history entries:"
for line in "${match_lines[@]}"; do
  echo "$line"
done

ids=()
for line in "${match_lines[@]}"; do
  id=$(awk '{print $1}' <<< "$line")
  if [[ "$id" =~ ^[0-9]+$ ]]; then
    ids+=("$id")
  fi
done

if [[ ${#ids[@]} -eq 0 ]]; then
  echo "\nCould not extract command IDs from matched lines."
  exit 1
fi

chain=""
for id in "${ids[@]}"; do
  if [[ -n "$chain" ]]; then
    chain+="; "
  fi
  chain+="!${id}"
done

echo
echo "Command ID chain:"
echo "$chain"

if [[ "$execute" -eq 1 ]]; then
  echo
  echo "Executing matched commands:"
  for line in "${match_lines[@]}"; do
    cmd=$(awk '{$1=""; sub(/^ /, ""); print}' <<< "$line")
    echo "+ $cmd"
    eval "$cmd"
  done
fi
