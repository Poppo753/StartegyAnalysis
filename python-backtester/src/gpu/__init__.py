"""
gpu/ - Motore GPU per screening massivo di combinazioni.

Usa CuPy (wrapper CUDA) per eseguire migliaia di simulazioni in parallelo.
Fallback automatico su fast CPU se GPU non disponibile.
"""