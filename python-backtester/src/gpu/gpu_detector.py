"""
gpu_detector.py - Rilevamento GPU e fallback automatico

Verifica la disponibilità di CuPy e GPU CUDA.
Se non disponibile, segnala e permette fallback su fast CPU.
"""

import sys
from typing import Dict, Any


def check_gpu_available() -> bool:
    """
    Verifica se CuPy e una GPU CUDA sono disponibili.
    
    Returns:
        True se GPU utilizzabile, False altrimenti.
    """
    try:
        import cupy as cp
        # Verifica che ci sia almeno una GPU
        device_count = cp.cuda.runtime.getDeviceCount()
        if device_count == 0:
            return False
        
        # Test rapido: alloca un piccolo array
        test = cp.zeros(10, dtype=cp.float64)
        del test
        
        return True
    except ImportError:
        return False
    except Exception:
        return False


def get_gpu_info() -> Dict[str, Any]:
    """
    Restituisce informazioni sulla GPU disponibile.
    
    Returns:
        Dict con nome, memoria, compute capability.
        Dict vuoto se GPU non disponibile.
    """
    try:
        import cupy as cp
        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(device.id)
        
        free_mem, total_mem = cp.cuda.Device(0).mem_info
        
        return {
            "name": props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"]),
            "total_memory_gb": round(total_mem / (1024**3), 2),
            "free_memory_gb": round(free_mem / (1024**3), 2),
            "compute_capability": f"{props['major']}.{props['minor']}",
        }
    except Exception:
        return {}


def print_gpu_status() -> None:
    """Stampa lo stato GPU in console."""
    import sys
    # Forza encoding UTF-8 per emoji su Windows
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    
    if check_gpu_available():
        info = get_gpu_info()
        print(f"  [GPU] {info.get('name', 'Unknown')}")
        print(f"     Memoria: {info.get('free_memory_gb', '?')}/{info.get('total_memory_gb', '?')} GB")
        print(f"     Compute: {info.get('compute_capability', '?')}")
    else:
        print("  [!] GPU non disponibile -> uso fast CPU per screening")