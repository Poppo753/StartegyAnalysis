"""Meta-analysis package (Fase 5).

Offline "brain": in which regime each strategy worked (regime_detector),
which strategies behave alike (strategy_clusterer), where to spend the
next search budget (focus_allocator), a markdown summary (report) and
which feature predicts success (feature_importance, gated on Fase 6).

Only numpy/pandas here; scikit-learn is imported lazily inside the two
modules that need it (strategy_clusterer, feature_importance).
"""

from __future__ import annotations
