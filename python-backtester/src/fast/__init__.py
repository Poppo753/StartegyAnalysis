"""
fast/ - Motore di backtest accelerato con Numba JIT

Usa numpy arrays e compilazione JIT per massimizzare la velocità
delle simulazioni su grandi griglie di parametri.

Engine: CPU (Numba @njit)
Futuro: GPU CUDA (numba.cuda / cupy)
"""