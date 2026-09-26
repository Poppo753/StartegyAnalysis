"""dsr.py - Deflated Sharpe Ratio, due formulazioni (F3-V05, CHG-004).

QUANDO USARE QUALE (masterplan v3 §§5.6, 6.2, 8.4.3):
- `calculate_dsr` (operativa, SR×(1−2×PBO)): SEMPRE nel flusso operativo.
  Lega il DSR alla misura di overfitting che gia` calcoliamo (PBO da CPCV).
  E` un'approssimazione pratica, dichiarata come tale.
- `calculate_dsr_exact` (SR×φ(z)/Φ(z), z=SR×√T): solo per il report finale,
  con T = anni di dati. Richiede scipy (prerequisito F3-V01).

Regola di flusso: DSR < 0 → rigetta (applicata in protocol.apply_pbo_gate).
"""

import numpy as np
from scipy.stats import norm


def _pbo_fraction(pbo: float) -> float:
    pbo = float(pbo)
    if pbo < 0:
        raise ValueError(f"pbo negativo ({pbo})")
    if pbo > 1.0:
        if pbo > 100.0:
            raise ValueError(f"pbo fuori scala ({pbo})")
        return pbo / 100.0
    return pbo


def calculate_dsr(sharpe: float, pbo: float) -> float:
    """DSR operativo: SR × (1 − 2 × PBO).

    Args:
        sharpe: Sharpe Ratio osservato.
        pbo: frazione 0-1 oppure percentuale 0-100.

    Returns:
        DSR operativo. PBO > 50% → negativo → rigetta.
    """
    sharpe = float(sharpe)
    if not np.isfinite(sharpe):
        return 0.0
    return float(sharpe * (1.0 - 2.0 * _pbo_fraction(pbo)))


def calculate_dsr_exact(sharpe: float, years: float) -> float:
    """DSR esatto (Lopez de Prado & Lewis, 2019): SR × φ(z)/Φ(z), z=SR×√T.

    Args:
        sharpe: Sharpe Ratio osservato.
        years: T in anni di dati (deve essere > 0).

    Returns:
        DSR esatto per report finale. Per z grandi decade ~SR/(z√(2π)).
    """
    sharpe = float(sharpe)
    years = float(years)
    if not np.isfinite(sharpe) or not np.isfinite(years):
        return 0.0
    if years <= 0:
        return 0.0
    z = sharpe * float(np.sqrt(years))
    cdf = float(norm.cdf(z))
    if cdf <= 0:
        return 0.0
    return float(sharpe * float(norm.pdf(z)) / cdf)
