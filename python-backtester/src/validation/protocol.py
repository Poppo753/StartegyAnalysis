"""protocol.py - Semaforo PBO nel flusso di validazione (F3-V04).

Wiring di `evaluate_pbo` nel protocollo anti-overfitting (masterplan v3
§6.2 step 5): SOLID → accetta, POTENTIALLY_VALID → walk-forward + holdout
obbligatori, OVERFITTED → rigetta. N_trials e` sempre loggato accanto al
PBO (trabocchetto v3). La regola DSR < 0 → rigetta (F3-V05) e` applicata
qui come override finale del gate.
"""

import logging

from src.validation.cross_validator import evaluate_pbo

logger = logging.getLogger(__name__)


def apply_pbo_gate(pbo: float, n_trials=None, dsr=None) -> dict:
    """Applica il semaforo PBO + regola DSR al flusso di validazione.

    Args:
        pbo: frazione 0-1 oppure percentuale 0-100 (vedi evaluate_pbo).
        n_trials: numero di trial/strategie testate (sempre loggato).
        dsr: Deflated Sharpe operativo (se noto). Se < 0 → REJECT
            indipendentemente dal verdetto PBO (F3-V05).

    Returns:
        dict {decision, required_steps, verdict, action, pbo_percent,
        n_trials, dsr, reason, log_line} con decision in
        {ACCEPT, CONDITIONAL, REJECT}.
    """
    ev = evaluate_pbo(pbo, n_trials=n_trials)
    verdict = ev["verdict"]
    if dsr is not None and float(dsr) < 0:
        decision = "REJECT"
        required_steps: list = []
        reason = f"DSR={float(dsr):.4f} < 0: strategia rigettata (override su {verdict})"
    elif verdict == "SOLID":
        decision = "ACCEPT"
        required_steps = []
        reason = "PBO SOLID: accetta"
    elif verdict == "POTENTIALLY_VALID":
        decision = "CONDITIONAL"
        required_steps = ["walk_forward", "holdout_final"]
        reason = "PBO POTENTIALLY_VALID: walk-forward + holdout finale obbligatori"
    else:
        decision = "REJECT"
        required_steps = []
        reason = "PBO OVERFITTED: rigetta"
    log_line = (
        f"{ev['log_line']} | DSR={dsr if dsr is not None else 'n/a'} "
        f"| decision={decision}"
        + (f" steps={required_steps}" if required_steps else "")
    )
    logger.info(log_line)
    return {
        "decision": decision,
        "required_steps": required_steps,
        "verdict": verdict,
        "action": ev["action"],
        "pbo_percent": ev["pbo_percent"],
        "n_trials": n_trials,
        "dsr": dsr,
        "reason": reason,
        "boundary_note": ev["boundary_note"],
        "log_line": log_line,
    }
