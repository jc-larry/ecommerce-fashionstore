"""Descarga los modelos de IA del vestidor virtual (CU32) antes de arrancar.

El CU32 usa tres modelos que se bajan de internet la primera vez que se usan:

* ``u2net_human_seg`` (~176 MB) — segmentación de la persona.
* ``isnet-general-use`` (~179 MB) — recorte de la prenda sobre cualquier fondo.
* ``pose_landmarker_lite.task`` (~6 MB) — landmarks corporales de MediaPipe.

Si no se precargan, la PRIMERA clienta que use el probador paga la descarga
(minutos de espera, y en Render el disco es efímero: se repite en cada deploy).

Uso en local:
    python preload_models.py

Uso en Render — poner en el *Build Command*, no en el *Start Command*:
    pip install -r requirements.txt && python preload_models.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    from app.packages.paquete_inteligente_y_analitica.vton_service import (
        GARMENT_REMBG_MODEL,
        REMBG_MODEL_NAME,
        VirtualTryonAIService,
    )

    failures = []

    for model_name in (REMBG_MODEL_NAME, GARMENT_REMBG_MODEL):
        try:
            from rembg import new_session

            new_session(model_name)
            print(f"[OK]  rembg '{model_name}' listo")
        except Exception as exc:  # pragma: no cover - depende de la red
            failures.append(f"rembg '{model_name}': {exc}")
            print(f"[ERR] rembg '{model_name}': {exc}")

    try:
        if VirtualTryonAIService._get_pose_landmarker() is None:
            failures.append("MediaPipe pose_landmarker no disponible")
            print("[ERR] MediaPipe pose_landmarker no disponible")
        else:
            print("[OK]  MediaPipe pose_landmarker listo")
    except Exception as exc:  # pragma: no cover - depende de la red
        failures.append(f"pose_landmarker: {exc}")
        print(f"[ERR] pose_landmarker: {exc}")

    if failures:
        print(f"\n{len(failures)} modelo(s) sin precargar; se descargarán en caliente.")
        return 1
    print("\nTodos los modelos del CU32 están precargados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
