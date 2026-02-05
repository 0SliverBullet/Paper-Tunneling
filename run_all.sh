#!/usr/bin/env bash
set -euo pipefail

run_step() {
	local label="$1"
	shift
	local start_ts
	start_ts=$(date +%s)
	printf '[%s] START: %s\n' "$(date '+%F %T')" "$label"
	"$@"
	local end_ts
	end_ts=$(date +%s)
	local elapsed=$((end_ts - start_ts))
	printf '[%s] END:   %s (elapsed %ss)\n' "$(date '+%F %T')" "$label" "$elapsed"
}

# Run conferences first
run_step "ICML 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --conferences icml
run_step "NeurIPS 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --conferences neurips
run_step "ICLR 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --conferences iclr

# Run journals in order
run_step "NMI 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --journals nmi
run_step "NCS 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --journals ncs
run_step "npjQI 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --journals npjqi
run_step "PRL 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --journals prl
run_step "Quantum 2023-2025" python main.py --keywords quantum --years 2023 2024 2025 --journals quantum
