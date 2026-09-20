"""Pruebas de regresión del CU32 — Vestidor Virtual.

Cubren los defectos que hacían que la prenda no se amoldara al cuerpo:

1. Una foto PNG con canal alfa "sucio" (opaco) debe segmentarse con rembg y no
   tomarse ese alfa como máscara de persona.
2. El recorte de la prenda debe funcionar con prenda blanca sobre fondo blanco
   y con fotos de producto que traen sofá, percha o marca de agua.
3. El resultado debe salir por la vía de amoldado anatómico, no por el pegado
   rectangular de reserva.
4. La prenda debe quedar dentro de la silueta y centrada en el torso.
"""
import os

import numpy as np
import pytest
from PIL import Image

from app.packages.paquete_inteligente_y_analitica.vton_service import VirtualTryonAIService

UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
PERSON = os.path.join(UPLOADS, "models", "sofia.png")
GARMENT_DARK = os.path.join(UPLOADS, "products", "blazer_chocolate.png")
GARMENT_WHITE = os.path.join(UPLOADS, "products", "blusa_peplum_blanca.png")

pytestmark = pytest.mark.skipif(
    not (os.path.exists(PERSON) and os.path.exists(GARMENT_DARK)),
    reason="Requiere las imágenes de ejemplo en backend/uploads.",
)


@pytest.fixture(scope="module")
def vton_result():
    return VirtualTryonAIService.generate_vton_look(
        person_image_data=PERSON,
        garment_image_url=GARMENT_DARK,
        product_name="Blazer chocolate",
        category="tops",
        model_choice="LOCAL",
        recommended_size="M",
        garment_landmarks=VirtualTryonAIService.get_garment_landmarks("", "tops"),
    )


def test_persona_se_segmenta_con_rembg_pese_al_alfa_sucio():
    """El alfa opaco de la exportación no debe usarse como máscara de persona."""
    original = Image.open(PERSON).convert("RGBA")
    assert original.getchannel("A").getextrema()[0] < 250, "La foto de prueba trae alfa sucio"

    result = VirtualTryonAIService._segment_image_with_confidence(original)
    assert result.source == "rembg-mask"
    assert result.mask_reliable is True
    assert result.confidence >= 0.75


def test_prenda_blanca_sobre_fondo_blanco_no_se_borra():
    """El umbral de blancos borraba la prenda; la segmentación por IA no."""
    isolated = VirtualTryonAIService._isolate_garment(
        VirtualTryonAIService._load_image(GARMENT_WHITE)
    )
    alpha = np.asarray(isolated.getchannel("A"))
    opaque_ratio = float((alpha >= 128).sum()) / alpha.size
    assert opaque_ratio > 0.35, "La prenda blanca se perdió al recortar"


def test_perfil_de_prenda_detecta_hombro_y_bajo():
    profile = VirtualTryonAIService._measure_garment_profile(
        VirtualTryonAIService._isolate_garment(
            VirtualTryonAIService._load_image(GARMENT_DARK)
        )
    )
    assert profile is not None
    assert profile["top_row"] <= profile["shoulder_row"] < profile["bottom_row"]
    assert profile["half_width"].min() >= 1.0


def test_resultado_usa_amoldado_anatomico(vton_result):
    """Si hay pose válida, la prenda se amolda; nunca se pega en rectángulo."""
    assert vton_result["pose_valid"] is True
    assert vton_result["fit_mode"] == "anatomical-warp"
    assert vton_result["result_image_url"].startswith("data:image/jpeg;base64,")


def test_prenda_queda_centrada_y_dentro_de_la_silueta(vton_result):
    """La prenda modifica el torso y no se derrama sobre el fondo."""
    import base64
    import io

    person = VirtualTryonAIService._standardize_person_canvas_with_bbox(
        VirtualTryonAIService._segment_image_with_confidence(
            VirtualTryonAIService._load_image(PERSON)
        ).image
    )[0].convert("RGB")
    composed = Image.open(
        io.BytesIO(base64.b64decode(vton_result["result_image_url"].split(",", 1)[1]))
    ).convert("RGB")

    changed = np.abs(
        np.asarray(composed, dtype=np.int16) - np.asarray(person, dtype=np.int16)
    ).max(axis=2) > 24

    assert changed.sum() > 8000, "La prenda apenas alteró la imagen"

    # Todo lo que cambió debe caer dentro de la silueta (con holgura de borde).
    mask = np.asarray(
        VirtualTryonAIService._standardize_person_mask(
            VirtualTryonAIService._segment_image_with_confidence(
                VirtualTryonAIService._load_image(PERSON)
            ).image
        ).filter(__import__("PIL.ImageFilter", fromlist=["MaxFilter"]).MaxFilter(11))
    ) >= 64
    leaked = float((changed & ~mask).sum()) / max(1, changed.sum())
    assert leaked < 0.02, f"La prenda se derrama al fondo ({leaked:.1%})"

    # El centro de masa de la prenda debe coincidir con el eje del cuerpo.
    columns = np.where(changed.any(axis=0))[0]
    garment_center = (columns[0] + columns[-1]) / 2
    body_columns = np.where(mask.any(axis=0))[0]
    body_center = (body_columns[0] + body_columns[-1]) / 2
    assert abs(garment_center - body_center) < composed.width * 0.05


def test_el_perfil_sigue_el_contorno_real_y_no_los_landmarks():
    """El contorno medido sobre la silueta debe mandar sobre el modelo teórico.

    Los landmarks de cadera de MediaPipe marcan la articulación: dan una cadera
    ~45 % más estrecha que el contorno real. Si el motor volviera a apoyarse en
    ellos, la prenda quedaría más angosta que el cuerpo y asomaría la piel.
    """
    import math

    raw = VirtualTryonAIService._load_image(PERSON)
    segmentation = VirtualTryonAIService._segment_image_with_confidence(raw)
    pose = VirtualTryonAIService._analyze_pose_image(raw)
    mapped = VirtualTryonAIService._map_pose_to_canvas(pose, raw.size, 720, 1080)
    mask = VirtualTryonAIService._standardize_person_mask(segmentation.image, 720, 1080)

    shoulder_center = mapped["shoulder_center"]
    hip_center = mapped["hip_center"]
    shoulder_width = float(mapped["shoulder_width"])
    torso_height = float(mapped["torso_height"])
    delta = (hip_center["x"] - shoulder_center["x"], hip_center["y"] - shoulder_center["y"])
    norm = max(1.0, math.hypot(*delta))
    axis = (delta[0] / norm, delta[1] / norm)
    across = (-axis[1], axis[0])

    length = torso_height * 1.10
    samples = np.linspace(0.0, 1.0, 96).astype(np.float32)
    centers = [
        (shoulder_center["x"] + axis[0] * length * t, shoulder_center["y"] + axis[1] * length * t)
        for t in samples
    ]
    analytic = np.full(96, shoulder_width / 2.0 * 0.90, dtype=np.float32)
    measured = VirtualTryonAIService._measure_body_half_widths(
        mask, samples, centers, across, analytic
    )

    waist = float(measured[int(0.50 * 95)])
    hip = float(measured[int(0.95 * 95)])
    assert waist < hip, "La cintura debe medirse más estrecha que la cadera"
    # La cadera real ronda el ancho de hombros; los landmarks daban ~55 % de eso.
    assert hip > shoulder_width / 2.0 * 0.95, (
        f"La cadera medida ({hip:.0f}px) volvió a colapsar al modelo teórico"
    )
