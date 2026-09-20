"""Calidad del amoldado del CU32, medida con criterios objetivos.

Estas pruebas existen porque "se ve bien" no es un criterio verificable. Cada
métrica corresponde a un defecto concreto que se detectó en producción:

``aspect_err``
    Distorsión de las proporciones de la prenda. El motor escalaba el eje
    horizontal fila a fila y recortaba el vertical por separado, así que una
    blusa acababa achatada o estirada. Es la métrica que garantiza lo que se
    pidió: amoldar sin forzar.
``stretch_var``
    Cociente entre el mayor y el menor estiramiento horizontal por fila. Mide
    literalmente cuánto se "fuerza" el tejido. Llegó a valer 1,72.
``shoulder_ov``
    Ancho de la prenda en la línea de hombro dividido por el ancho del CUERPO
    ahí mismo. Detecta la "barra" de tela flotando sobre los hombros. Se
    normaliza contra la silueta y no contra los landmarks: MediaPipe los sitúa
    en la articulación, el deltoides sobresale, y medir contra ellos castigaba
    a prendas que cubrían el hombro correctamente.
``gap`` y ``leak``
    Torso sin cubrir y prenda derramada fuera de la silueta.

``hem`` se mide y se registra, pero con límites amplios a propósito: el largo
es consecuencia de las proporciones (ya vigiladas por ``aspect_err``), no un
criterio independiente. Un blazer peplum termina legítimamente en la cintura.
"""
import base64
import io
import math
import os

import numpy as np
import pytest
from PIL import Image

from app.packages.paquete_inteligente_y_analitica.vton_service import VirtualTryonAIService

UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
MODELS = os.path.join(UPLOADS, "models")
PRODUCTS = os.path.join(UPLOADS, "products")
TARGET_W, TARGET_H = 720, 1080

CASES = [
    ("blusa_camel_botones", "sofia", "M"),
    ("blazer_chocolate", "valeria", "S"),
    ("top_dior_beige", "emma", "L"),
    ("blusa_peplum_blanca", "lin", "XS"),
]

pytestmark = pytest.mark.skipif(
    not os.path.isdir(MODELS) or not os.path.isdir(PRODUCTS),
    reason="Requiere las imágenes de ejemplo en backend/uploads.",
)


def _measure(garment_name: str, model_name: str, size: str):
    person_path = os.path.join(MODELS, f"{model_name}.png")
    garment_path = os.path.join(PRODUCTS, f"{garment_name}.png")

    # La capa de prenda se captura en su origen. Detectarla restando la foto
    # limpia falla cuando prenda y ropa interior comparten tono (blazer
    # chocolate sobre bañador negro) y fabrica huecos inexistentes.
    captured = {}
    original_clip = VirtualTryonAIService._clip_garment_to_person

    def spy(layer, mask):
        out = original_clip(layer, mask)
        captured["layer"] = out
        return out

    VirtualTryonAIService._clip_garment_to_person = staticmethod(spy)
    try:
        result = VirtualTryonAIService.generate_vton_look(
            person_image_data=person_path,
            garment_image_url=garment_path,
            product_name=garment_name,
            category="tops",
            model_choice="LOCAL",
            recommended_size=size,
            garment_landmarks=VirtualTryonAIService.get_garment_landmarks("", "tops"),
        )
    finally:
        VirtualTryonAIService._clip_garment_to_person = original_clip

    assert "layer" in captured, "El motor no llegó a componer la prenda"
    garment = np.asarray(captured["layer"].getchannel("A")) >= 110
    assert garment.sum() > 500, "La prenda no se pintó"

    raw = VirtualTryonAIService._load_image(person_path)
    segmentation = VirtualTryonAIService._segment_image_with_confidence(raw)
    body_mask = np.asarray(
        VirtualTryonAIService._standardize_person_mask(segmentation.image, TARGET_W, TARGET_H)
    ) >= 96
    pose = VirtualTryonAIService._analyze_pose_image(raw)
    mapped = VirtualTryonAIService._map_pose_to_canvas(pose, raw.size, TARGET_W, TARGET_H)
    shoulder_center = mapped["shoulder_center"]
    hip_center = mapped["hip_center"]
    shoulder_width = float(mapped["shoulder_width"])
    torso_height = float(mapped["torso_height"])

    rows = np.where(garment.any(axis=1))[0]
    cols = np.where(garment.any(axis=0))[0]
    top, bottom = int(rows[0]), int(rows[-1])
    height, width = bottom - top + 1, int(cols[-1] - cols[0] + 1)

    source = VirtualTryonAIService._isolate_garment(
        VirtualTryonAIService._load_image(garment_path)
    )
    source_alpha = np.asarray(source.getchannel("A")) >= 90
    s_rows = np.where(source_alpha.any(axis=1))[0]
    s_cols = np.where(source_alpha.any(axis=0))[0]
    source_aspect = (s_rows[-1] - s_rows[0] + 1) / max(1, s_cols[-1] - s_cols[0] + 1)

    shoulder_row = int(round(shoulder_center["y"]))
    band = garment[max(0, shoulder_row - 4): shoulder_row + 5]
    band_cols = np.where(band.any(axis=0))[0]
    body_band = body_mask[max(0, shoulder_row - 4): shoulder_row + 5]
    body_band_cols = np.where(body_band.any(axis=0))[0]
    body_span = (
        (body_band_cols[-1] - body_band_cols[0] + 1)
        if body_band_cols.size else shoulder_width
    )

    torso_top = int(shoulder_center["y"] + torso_height * 0.30)
    torso_bottom = min(bottom, int(hip_center["y"]))
    gap = 0.0
    if torso_bottom > torso_top:
        half = shoulder_width * 0.34
        x0, x1 = int(shoulder_center["x"] - half), int(shoulder_center["x"] + half)
        region = body_mask[torso_top:torso_bottom, x0:x1]
        gap = float((region & ~garment[torso_top:torso_bottom, x0:x1]).sum()) / max(1, region.sum())

    stretch = []
    for frac in np.linspace(0.12, 0.92, 12):
        row = int(top + frac * height)
        hits = np.where(garment[row])[0]
        s_row = int(s_rows[0] + frac * (s_rows[-1] - s_rows[0]))
        s_hits = np.where(source_alpha[s_row])[0]
        if hits.size >= 4 and s_hits.size >= 4:
            stretch.append((hits[-1] - hits[0] + 1) / (s_hits[-1] - s_hits[0] + 1))

    return {
        "aspect_err": abs((height / max(1, width)) / source_aspect - 1.0),
        "hem": (bottom - shoulder_center["y"]) / max(1.0, torso_height),
        "shoulder_ov": (
            (band_cols[-1] - band_cols[0] + 1) / max(1.0, body_span)
            if band_cols.size else 0.0
        ),
        "gap": gap,
        "leak": float((garment & ~body_mask).sum()) / max(1, garment.sum()),
        "stretch_var": (max(stretch) / min(stretch)) if len(stretch) >= 4 else float("nan"),
        "fit_mode": result.get("fit_mode"),
    }


@pytest.fixture(scope="module", params=CASES, ids=lambda c: f"{c[0]}_{c[1]}_{c[2]}")
def fit(request):
    return _measure(*request.param)


def test_usa_el_amoldado_anatomico(fit):
    assert fit["fit_mode"] == "anatomical-warp"


def test_conserva_las_proporciones_de_la_prenda(fit):
    """Amoldar no puede significar deformar: el alto/ancho debe respetarse."""
    assert fit["aspect_err"] <= 0.18, (
        f"proporciones distorsionadas un {fit['aspect_err']:.0%}"
    )


def test_no_fuerza_el_tejido(fit):
    """El estiramiento horizontal no puede variar el doble entre filas."""
    assert math.isnan(fit["stretch_var"]) or fit["stretch_var"] <= 1.90, (
        f"estiramiento desigual x{fit['stretch_var']:.2f} entre filas"
    )


def test_el_hombro_no_desborda(fit):
    """La prenda no puede sobresalir del cuerpo en la línea de hombro.

    Se normaliza contra la SILUETA, no contra los landmarks. Medirlo contra
    los landmarks fue un error de calibración: MediaPipe los sitúa en la
    articulación y el deltoides sobresale, así que una prenda que cubre bien
    el hombro mide 1,2 veces esa distancia sin salirse del cuerpo ni un
    milímetro. Normalizado contra la silueta, el criterio es infalsificable:
    por encima de 1 la tela flota fuera del cuerpo.
    """
    assert fit["shoulder_ov"] <= 1.05, (
        f"la prenda sobresale del cuerpo en el hombro ({fit['shoulder_ov']:.2f}x)"
    )


def test_cubre_el_torso_y_no_se_derrama(fit):
    assert fit["gap"] <= 0.06, f"queda un {fit['gap']:.0%} del torso sin cubrir"
    assert fit["leak"] <= 0.02, f"un {fit['leak']:.0%} de la prenda cae fuera de la silueta"


def test_el_largo_es_plausible(fit):
    """Límites amplios a propósito: solo cazan anomalías gruesas.

    El largo se deriva de las proporciones de la prenda, que ya verifica
    ``test_conserva_las_proporciones_de_la_prenda``. Exigir aquí un rango
    estrecho obligaría a deformar la prenda para cumplirlo.
    """
    assert 0.60 <= fit["hem"] <= 1.40, f"bajo en {fit['hem']:.2f} alturas de torso"


UNDERLAYER_CASES = [
    # sofia y lin son maniquíes que posan VESTIDOS (camiseta de manga corta).
    # Antes, la manga de esa camiseta asomaba por los hombros de la prenda
    # nueva y delataba el montaje. Es el caso realista: una clienta sube su
    # foto vestida, no en ropa interior.
    ("sofia", "blusa_camel_botones", "S"),
    ("lin", "blusa_camel_botones", "M"),
]


@pytest.mark.parametrize("model_name,garment_name,size", UNDERLAYER_CASES)
def test_borra_la_manga_de_la_ropa_de_debajo(model_name, garment_name, size):
    """En la zona de los brazos no puede quedar tejido ajeno a la vista."""
    import cv2

    person_path = os.path.join(MODELS, f"{model_name}.png")
    garment_path = os.path.join(PRODUCTS, f"{garment_name}.png")

    captured = {}
    original_clip = VirtualTryonAIService._clip_garment_to_person

    def spy(layer, mask):
        out = original_clip(layer, mask)
        captured["layer"] = out
        return out

    VirtualTryonAIService._clip_garment_to_person = staticmethod(spy)
    try:
        result = VirtualTryonAIService.generate_vton_look(
            person_image_data=person_path,
            garment_image_url=garment_path,
            product_name=garment_name,
            category="tops",
            model_choice="LOCAL",
            recommended_size=size,
            garment_landmarks=VirtualTryonAIService.get_garment_landmarks("", "tops"),
        )
    finally:
        VirtualTryonAIService._clip_garment_to_person = original_clip

    composed = np.asarray(
        Image.open(
            io.BytesIO(base64.b64decode(result["result_image_url"].split(",", 1)[1]))
        ).convert("RGB")
    )
    raw = VirtualTryonAIService._load_image(person_path)
    segmentation = VirtualTryonAIService._segment_image_with_confidence(raw)
    body = np.asarray(
        VirtualTryonAIService._standardize_person_mask(segmentation.image, TARGET_W, TARGET_H)
    ) >= 96
    pose = VirtualTryonAIService._analyze_pose_image(raw)
    mapped = VirtualTryonAIService._map_pose_to_canvas(pose, raw.size, TARGET_W, TARGET_H)
    points = mapped["points"]
    shoulder_width = float(mapped["shoulder_width"])
    garment = np.asarray(captured["layer"].getchannel("A")) >= 110

    arms = np.zeros(body.shape, np.uint8)
    for start, end in (
        ("left_shoulder", "left_elbow"),
        ("right_shoulder", "right_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_elbow", "right_wrist"),
    ):
        if start in points and end in points:
            cv2.line(
                arms,
                (int(points[start]["x"]), int(points[start]["y"])),
                (int(points[end]["x"]), int(points[end]["y"])),
                1,
                int(shoulder_width * 0.20),
            )
    visible_arm = (arms > 0) & body & ~garment
    assert visible_arm.sum() > 500, "No se pudo medir la zona de brazos"

    ycrcb = cv2.cvtColor(composed, cv2.COLOR_RGB2YCrCb)
    cr, cb = ycrcb[..., 1], ycrcb[..., 2]
    skin = (cr >= 133) & (cr <= 183) & (cb >= 77) & (cb <= 132)
    skin_share = float(skin[visible_arm].mean())

    assert skin_share >= 0.90, (
        f"solo el {skin_share:.0%} del brazo visible es piel: "
        "asoma la ropa que la modelo lleva debajo"
    )
