#!/bin/sh
# Foreground local-only model server; use a second terminal for make briefing-record.
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ollama_bin=${OLLAMA_BIN:-"$project_dir/artifacts/stage13/runtime/Ollama.app/Contents/Resources/ollama"}
if [ ! -x "$ollama_bin" ]; then
  ollama_bin=$(command -v ollama) || { echo 'Install Ollama from https://ollama.com/download or set OLLAMA_BIN.'; exit 1; }
fi
export OLLAMA_MODELS="${OLLAMA_MODELS:-$project_dir/artifacts/stage13/runtime/models}"
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
exec "$ollama_bin" serve
