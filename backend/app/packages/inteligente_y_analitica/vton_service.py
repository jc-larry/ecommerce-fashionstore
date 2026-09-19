"""Servicio de Inteligencia Artificial para el Vestidor Virtual (CU32).

Integra modelos de difusión generativa de vanguardia:
1. IDM-VTON (Improving Diffusion Models for Virtual Try-on - Hugging Face).
2. Fashn.ai (API E-commerce de producción para prueba textil).
3. Motor de Síntesis Adaptativa Local (Fallback fotorrealista con ajuste de drapeado e iluminación).
4. Segmentación corporal con rembg (u2net) para remoción de fondo con IA.
5. Calibración anatómica por landmarks (cuello, hombros, pecho, cintura, bajo).
"""
import os
import time
import base64
import logging
import io
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import requests
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
FASHN_API_KEY = os.getenv("FASHN_API_KEY", "")
FASHN_API_BASE = os.getenv("FASHN_API_BASE", "https://api.fashn.ai")
FASHN_MODEL_NAME = os.getenv("FASHN_MODEL_NAME", "tryon-max").lower()
FASHN_POLL_TIMEOUT_SEC = float(os.getenv("FASHN_POLL_TIMEOUT_SEC", "95"))
REMBG_MODEL_NAME = os.getenv("REMBG_MODEL_NAME", "u2net_human_seg")
# Modelo de segmentacion para la PRENDA. u2net_human_seg solo reconoce personas,
# por eso el recorte de producto usa un modelo de proposito general.
GARMENT_REMBG_MODEL = os.getenv("GARMENT_REMBG_MODEL", "isnet-general-use")
# Angulo minimo brazo-torso (grados) a partir del cual la manga se reproyecta
# sobre el brazo en lugar de viajar con el remapeo del torso.
SLEEVE_REPROJECTION_MIN_DEG = float(os.getenv("SLEEVE_REPROJECTION_MIN_DEG", "35"))
POSE_LANDMARKER_MODEL_URL = os.getenv(
    "POSE_LANDMARKER_MODEL_URL",
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
)
POSE_LANDMARKER_MODEL_PATH = os.getenv(
    "POSE_LANDMARKER_MODEL_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "models",
        "pose_landmarker_lite.task",
    ),
)
POSE_DETECTION_CONFIDENCE = float(os.getenv("POSE_DETECTION_CONFIDENCE", "0.70"))
POSE_PRESENCE_CONFIDENCE = float(os.getenv("POSE_PRESENCE_CONFIDENCE", "0.70"))
POSE_LANDMARK_CONFIDENCE_THRESHOLD = float(
    os.getenv("POSE_LANDMARK_CONFIDENCE_THRESHOLD", "0.75")
)
PERSON_MASK_CONFIDENCE_THRESHOLD = float(
    os.getenv("PERSON_MASK_CONFIDENCE_THRESHOLD", "0.75")
)


@dataclass
class PersonSegmentationResult:
    """Máscara de la persona y diagnóstico de su calidad.

    ``confidence`` es un score de calidad derivado de la máscara. rembg entrega
    una máscara alfa, pero no una probabilidad calibrada de confianza como un
    detector; por eso lo nombramos explícitamente como calidad de máscara.
    """

    image: Image.Image
    confidence: float
    bbox: Optional[tuple[int, int, int, int]]
    mask_reliable: bool
    source: str


@dataclass
class PoseAnalysisResult:
    """Landmarks y geometría corporal detectados por MediaPipe."""

    landmarks: Dict[str, Any]
    confidence: float
    valid: bool
    source: str

# --- Diccionario de Landmarks Anatómicos por Prenda ---
# Coordenadas normalizadas (0.0 a 1.0) relativas al bounding box de la prenda.
# Se utilizan para calcular la posición exacta de la prenda sobre la silueta.
GARMENT_LANDMARKS_DB: Dict[str, Dict[str, Any]] = {
    # Calibración predeterminada genérica para tops/blusas
    "default_top": {
        "neck_y": 0.06,
        "neck_depth": 0.12,
        "shoulder_y": 0.06,
        "shoulder_width": 0.70,
        "chest_y": 0.32,
        "waist_y": 0.55,
        "hem_y": 0.95,
        "type": "generic_top",
    },
    "default_bottom": {
        "neck_y": 0.0,
        "neck_depth": 0.0,
        "shoulder_y": 0.0,
        "shoulder_width": 0.60,
        "chest_y": 0.0,
        "waist_y": 0.05,
        "hem_y": 0.95,
        "type": "generic_bottom",
    },
    "default_dress": {
        "neck_y": 0.04,
        "neck_depth": 0.10,
        "shoulder_y": 0.04,
        "shoulder_width": 0.65,
        "chest_y": 0.22,
        "waist_y": 0.38,
        "hem_y": 0.95,
        "type": "generic_dress",
    },
    # Landmarks específicos calibrados para las 4 nuevas prendas
    "peplum_v_neck": {
        "neck_y": 0.08,
        "neck_depth": 0.22,
        "shoulder_y": 0.06,
        "shoulder_width": 0.72,
        "chest_y": 0.32,
        "waist_y": 0.55,
        "hem_y": 0.95,
        "type": "peplum_v_neck",
    },
    "off_shoulder_double_breasted": {
        "neck_y": 0.12,
        "neck_depth": 0.06,
        "shoulder_y": 0.10,
        "shoulder_width": 0.82,
        "chest_y": 0.30,
        "waist_y": 0.52,
        "hem_y": 0.92,
        "type": "off_shoulder_double_breasted",
    },
    "crew_neck_structured": {
        "neck_y": 0.05,
        "neck_depth": 0.04,
        "shoulder_y": 0.07,
        "shoulder_width": 0.68,
        "chest_y": 0.30,
        "waist_y": 0.54,
        "hem_y": 0.93,
        "type": "crew_neck_structured",
    },
    "blazer_notch_lapel_peplum": {
        "neck_y": 0.06,
        "neck_depth": 0.18,
        "shoulder_y": 0.05,
        "shoulder_width": 0.76,
        "chest_y": 0.28,
        "waist_y": 0.50,
        "hem_y": 0.94,
        "type": "blazer_notch_lapel_peplum",
    },
}

# --- Landmarks Anatómicos del Cuerpo Humano (proporción estándar femenina) ---
# Coordenadas normalizadas (0.0 a 1.0) relativas al lienzo 720x1080.
BODY_LANDMARKS = {
    "head_top_y": 0.04,
    "chin_y": 0.14,
    "neck_base_y": 0.17,
    "shoulder_l_x": 0.28,
    "shoulder_r_x": 0.72,
    "shoulder_y": 0.19,
    "chest_y": 0.28,
    "bust_y": 0.32,
    "waist_y": 0.42,
    "hip_y": 0.50,
    "knee_y": 0.72,
    "ankle_y": 0.93,
    "center_x": 0.50,
}

POSE_LANDMARK_NAMES = {
    0: "nose",
    7: "left_ear",
    8: "right_ear",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
}
POSE_ESSENTIAL_LANDMARKS = (11, 12, 23, 24)


class VirtualTryonAIService:
    """Orquestador de inferencia para Virtual Try-On (VTON) con modelos generativos."""

    _rembg_session = None
    _garment_rembg_session = None
    _pose_landmarker = None

    @staticmethod
    def normalize_category(category: str = "tops") -> str:
        """Convierte categorías del catálogo al enum esperado por el motor VTON."""
        value = (category or "tops").strip().lower()
        if any(token in value for token in (
            "vestido", "dress", "enterizo", "mono", "one-piece", "one piece", "kaftan"
        )):
            return "one-pieces"
        if any(token in value for token in (
            "pantal", "pants", "falda", "skirt", "jean", "short", "bottom", "inferior"
        )):
            return "bottoms"
        return "tops"

    @classmethod
    def _remove_background_rgba(cls, img: Image.Image) -> Image.Image:
        """Obtiene una máscara alfa si rembg está disponible; si no, conserva la foto."""
        return cls._segment_image_with_confidence(img).image

    # ─── Segmentación con rembg ───

    @classmethod
    def _run_rembg_mask(cls, img: Image.Image) -> Optional[Image.Image]:
        """Ejecuta rembg solicitando una máscara L, no solamente un recorte."""
        try:
            from rembg import new_session, remove

            source = io.BytesIO()
            img.convert("RGBA").save(source, format="PNG")
            source_bytes = source.getvalue()
            if cls._rembg_session is None:
                cls._rembg_session = new_session(REMBG_MODEL_NAME)
            try:
                # only_mask y post_process_mask son las opciones de rembg para
                # obtener y limpiar directamente la máscara de segmentación.
                mask_bytes = remove(
                    source_bytes,
                    session=cls._rembg_session,
                    only_mask=True,
                    post_process_mask=True,
                )
                return Image.open(io.BytesIO(mask_bytes)).convert("L")
            except TypeError:
                # Compatibilidad con versiones antiguas de rembg.
                cutout_bytes = remove(source_bytes, session=cls._rembg_session)
                return Image.open(io.BytesIO(cutout_bytes)).convert("RGBA").getchannel("A")
        except ImportError:
            logger.info("rembg no disponible; no se pudo crear la máscara de persona.")
        except Exception as exc:
            logger.warning("No se pudo generar la máscara de persona: %s", exc)
        return None

    @staticmethod
    def _estimate_mask_quality(
        mask: Image.Image,
    ) -> tuple[float, Optional[tuple[int, int, int, int]]]:
        """Calcula un score conservador de calidad de máscara entre 0 y 1.

        No es una probabilidad calibrada del modelo. Evalúa cobertura, continuidad
        del cuerpo, bordes suaves y si la máscara ocupa accidentalmente todo el lienzo.
        """
        original = mask.convert("L")
        binary = original.point(lambda value: 255 if value >= 32 else 0)
        bbox = binary.getbbox()
        if not bbox:
            return 0.0, None

        max_side = max(original.width, original.height)
        if max_side > 256:
            ratio = 256 / max_side
            small = original.resize(
                (max(1, int(original.width * ratio)), max(1, int(original.height * ratio))),
                Image.Resampling.BILINEAR,
            )
        else:
            small = original

        values = list(small.getdata())
        total = max(1, len(values))
        foreground = sum(value >= 32 for value in values)
        hard_foreground = sum(value >= 180 for value in values)
        if foreground == 0:
            return 0.0, bbox

        coverage = foreground / total
        soft_ratio = max(0.0, (foreground - hard_foreground) / foreground)
        core_score = hard_foreground / foreground
        edge_score = 1.0 - min(1.0, soft_ratio * 1.5)

        bbox_width_ratio = (bbox[2] - bbox[0]) / max(1, original.width)
        bbox_height_ratio = (bbox[3] - bbox[1]) / max(1, original.height)
        height_score = max(0.0, min(1.0, (bbox_height_ratio - 0.12) / 0.55))
        area_score = min(1.0, coverage / 0.025)
        if coverage > 0.85:
            area_score *= max(0.0, 1.0 - ((coverage - 0.85) / 0.15))

        touches_canvas = (
            bbox[0] <= max(2, int(original.width * 0.01))
            and bbox[1] <= max(2, int(original.height * 0.01))
            and bbox[2] >= original.width - max(2, int(original.width * 0.01))
            and bbox[3] >= original.height - max(2, int(original.height * 0.01))
        )
        bbox_score = 0.35 if touches_canvas else 1.0
        if coverage > 0.92:
            bbox_score = 0.15

        confidence = (
            0.35 * core_score
            + 0.25 * edge_score
            + 0.20 * height_score
            + 0.10 * area_score
            + 0.10 * bbox_score
        )
        # Una máscara que toca los cuatro bordes suele significar que rembg no
        # logró separar a la persona del fondo. Nunca debe pasar el umbral.
        if touches_canvas:
            confidence *= 0.55
        if coverage > 0.92:
            confidence *= 0.35
        if bbox_width_ratio < 0.05 or bbox_height_ratio < 0.10:
            confidence *= 0.40

        return round(max(0.0, min(1.0, confidence)), 3), bbox

    @classmethod
    def _segment_image_with_confidence(cls, img: Image.Image) -> PersonSegmentationResult:
        """Segmenta una imagen ya cargada y devuelve máscara más diagnóstico."""
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")

        # Un PNG puede traer canal alfa sin que ese alfa recorte a la persona
        # (exportaciones con alfa "sucio" de 191-255 que cubren todo el lienzo).
        # Solo confiamos en el alfa de entrada si realmente separa figura y fondo:
        # debe haber una fracción significativa de píxeles francamente transparentes.
        histogram = alpha.histogram()
        total_pixels = max(1, rgba.width * rgba.height)
        transparent_ratio = sum(histogram[:16]) / total_pixels
        input_alpha_segments = transparent_ratio >= 0.04

        if input_alpha_segments:
            mask = alpha
            source = "input-alpha"
        else:
            mask = cls._run_rembg_mask(rgba)
            source = "rembg-mask" if mask is not None else "none"
            if mask is None and alpha.getextrema()[0] < 250:
                mask, source = alpha, "input-alpha-fallback"

        if mask is None:
            return PersonSegmentationResult(
                image=rgba,
                confidence=0.0,
                bbox=(0, 0, rgba.width, rgba.height),
                mask_reliable=False,
                source=source,
            )

        if mask.size != rgba.size:
            mask = mask.resize(rgba.size, Image.Resampling.LANCZOS)
        rgba.putalpha(mask)
        confidence, bbox = cls._estimate_mask_quality(mask)
        return PersonSegmentationResult(
            image=rgba,
            confidence=confidence,
            bbox=bbox,
            mask_reliable=confidence >= PERSON_MASK_CONFIDENCE_THRESHOLD,
            source=source,
        )

    @classmethod
    def segment_person_with_confidence(cls, image_data: str) -> PersonSegmentationResult:
        """Carga y segmenta una imagen, aplicando el umbral de calidad configurado."""
        raw_img = cls._load_image(image_data)
        if raw_img is None:
            return PersonSegmentationResult(
                image=Image.new("RGBA", (1, 1), (0, 0, 0, 0)),
                confidence=0.0,
                bbox=None,
                mask_reliable=False,
                source="none",
            )
        return cls._segment_image_with_confidence(raw_img)

    @classmethod
    def _compose_person_preview(cls, person_no_bg: Image.Image) -> str:
        """Renderiza el recorte sobre el fondo blanco usado por la previsualización."""
        target_w, target_h = 720, 1080
        studio_bg = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))
        aspect = person_no_bg.width / max(1, person_no_bg.height)
        target_aspect = target_w / target_h
        if aspect > target_aspect:
            new_w = target_w
            new_h = int(target_w / aspect)
        else:
            new_h = target_h
            new_w = int(target_h * aspect)

        p_resized = person_no_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = (target_w - new_w) // 2
        pos_y = target_h - new_h
        studio_bg.paste(p_resized, (pos_x, pos_y), p_resized)

        output_buf = io.BytesIO()
        studio_bg.convert("RGB").save(output_buf, format="JPEG", quality=92)
        encoded = base64.b64encode(output_buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    @classmethod
    def analyze_person(cls, image_data: str) -> Dict[str, Any]:
        """Devuelve la previsualización segmentada junto con sus métricas."""
        start_time = time.time()
        raw_img = cls._load_image(image_data)
        if raw_img is None:
            segmentation = cls.segment_person_with_confidence(image_data)
            pose = PoseAnalysisResult({}, 0.0, False, "none")
        else:
            segmentation = cls._segment_image_with_confidence(raw_img)
            pose = cls._analyze_pose_image(raw_img)
        preview = cls._compose_person_preview(segmentation.image)
        elapsed = round(time.time() - start_time, 2)
        logger.info(
            "Segmentación corporal completada en %ss: source=%s confidence=%s reliable=%s",
            elapsed,
            segmentation.source,
            segmentation.confidence,
            segmentation.mask_reliable,
        )
        return {
            "processed_image_url": preview,
            "mask_confidence": segmentation.confidence,
            "mask_reliable": segmentation.mask_reliable,
            "mask_source": segmentation.source,
            "mask_bbox": list(segmentation.bbox) if segmentation.bbox else None,
            "pose_confidence": pose.confidence,
            "pose_valid": pose.valid,
            "pose_source": pose.source,
            "pose_landmarks": pose.landmarks,
            "processing_time_sec": elapsed,
        }

    @classmethod
    def segment_person_background(cls, image_data: str) -> str:
        """Segmenta la persona y conserva esta API para los clientes existentes."""
        try:
            return cls.analyze_person(image_data)["processed_image_url"]
        except Exception as exc:
            logger.error("Error en segmentación corporal: %s", exc)
            return image_data

    # ─── Pose anatómica con MediaPipe ───

    @classmethod
    def _get_pose_landmarker(cls):
        """Crea una instancia reutilizable de MediaPipe Pose Landmarker."""
        if cls._pose_landmarker is not None:
            return cls._pose_landmarker
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            model_path = POSE_LANDMARKER_MODEL_PATH
            if not os.path.isabs(model_path):
                backend_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                )
                relative_path = model_path.replace("/", os.sep).replace("\\", os.sep)
                if relative_path.lower().startswith(f"backend{os.sep}"):
                    relative_path = relative_path[len(f"backend{os.sep}"):]
                model_path = os.path.join(backend_dir, relative_path)
            if not os.path.isfile(model_path):
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                response = requests.get(POSE_LANDMARKER_MODEL_URL, timeout=45.0)
                response.raise_for_status()
                temporary_path = f"{model_path}.part"
                with open(temporary_path, "wb") as model_file:
                    model_file.write(response.content)
                os.replace(temporary_path, model_path)

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=POSE_DETECTION_CONFIDENCE,
                min_pose_presence_confidence=POSE_PRESENCE_CONFIDENCE,
                min_tracking_confidence=POSE_PRESENCE_CONFIDENCE,
                output_segmentation_masks=False,
            )
            cls._pose_landmarker = vision.PoseLandmarker.create_from_options(options)
            return cls._pose_landmarker
        except ImportError:
            logger.info("MediaPipe no está instalado; se usará el fallback anatómico.")
        except Exception as exc:
            logger.warning("No se pudo inicializar MediaPipe Pose Landmarker: %s", exc)
        return None

    @staticmethod
    def _pose_point_score(landmark: Any) -> float:
        values = [
            getattr(landmark, "visibility", None),
            getattr(landmark, "presence", None),
        ]
        values = [float(value) for value in values if value is not None]
        return max(0.0, min(1.0, sum(values) / len(values))) if values else 0.0

    @staticmethod
    def _point_distance(first: Dict[str, float], second: Dict[str, float]) -> float:
        return math.hypot(first["x"] - second["x"], first["y"] - second["y"])

    @staticmethod
    def _point_midpoint(first: Dict[str, float], second: Dict[str, float]) -> Dict[str, float]:
        return {
            "x": round((first["x"] + second["x"]) / 2, 5),
            "y": round((first["y"] + second["y"]) / 2, 5),
        }

    @classmethod
    def _analyze_pose_image(cls, img: Image.Image) -> PoseAnalysisResult:
        """Obtiene landmarks y medidas anatómicas normalizadas de una persona."""
        landmarker = cls._get_pose_landmarker()
        if landmarker is None:
            return PoseAnalysisResult({}, 0.0, False, "none")

        try:
            import mediapipe as mp
            import numpy as np

            rgb_array = np.asarray(img.convert("RGB"))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_array)
            result = landmarker.detect(mp_image)
            if not result.pose_landmarks:
                return PoseAnalysisResult({}, 0.0, False, "mediapipe")

            pose = result.pose_landmarks[0]
            points: Dict[str, Dict[str, float]] = {}
            scores = []
            for index, name in POSE_LANDMARK_NAMES.items():
                if index >= len(pose):
                    continue
                landmark = pose[index]
                landmark_score = cls._pose_point_score(landmark)
                points[name] = {
                    "x": round(float(landmark.x), 5),
                    "y": round(float(landmark.y), 5),
                    "z": round(float(landmark.z), 5),
                    "visibility": round(landmark_score, 5),
                }
                if index in POSE_ESSENTIAL_LANDMARKS:
                    scores.append(landmark_score)

            required_names = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
            if not all(name in points for name in required_names):
                confidence = round(sum(scores) / max(1, len(scores)), 3)
                return PoseAnalysisResult(
                    {"points": points, "pose_confidence": confidence},
                    confidence,
                    False,
                    "mediapipe",
                )

            left_shoulder = points["left_shoulder"]
            right_shoulder = points["right_shoulder"]
            left_hip = points["left_hip"]
            right_hip = points["right_hip"]
            shoulder_center = cls._point_midpoint(left_shoulder, right_shoulder)
            hip_center = cls._point_midpoint(left_hip, right_hip)
            shoulder_width = cls._point_distance(left_shoulder, right_shoulder)
            hip_width = cls._point_distance(left_hip, right_hip)
            torso_height = cls._point_distance(shoulder_center, hip_center)
            shoulder_angle = math.degrees(
                math.atan2(
                    right_shoulder["y"] - left_shoulder["y"],
                    right_shoulder["x"] - left_shoulder["x"],
                )
            )
            confidence = round(sum(scores) / max(1, len(scores)), 3)
            essential_points = [points[name] for name in required_names]
            points_in_frame = all(
                -0.05 <= point[axis] <= 1.05
                for point in essential_points
                for axis in ("x", "y")
            )
            valid_geometry = (
                shoulder_width >= 0.08
                and hip_width >= 0.08
                and torso_height >= 0.08
                and hip_center["y"] > shoulder_center["y"]
                and points_in_frame
            )
            valid = confidence >= POSE_LANDMARK_CONFIDENCE_THRESHOLD and valid_geometry
            landmarks = {
                "points": points,
                "pose_confidence": confidence,
                "pose_valid": valid,
                "shoulder_center": shoulder_center,
                "hip_center": hip_center,
                "shoulder_width": round(shoulder_width, 5),
                "hip_width": round(hip_width, 5),
                "torso_height": round(torso_height, 5),
                "shoulder_angle_deg": round(shoulder_angle, 3),
            }
            return PoseAnalysisResult(landmarks, confidence, valid, "mediapipe")
        except Exception as exc:
            logger.warning("No se pudo analizar la pose con MediaPipe: %s", exc)
            return PoseAnalysisResult({}, 0.0, False, "mediapipe-error")

    @staticmethod
    def _map_pose_to_canvas(
        pose: PoseAnalysisResult,
        source_size: tuple[int, int],
        target_w: int,
        target_h: int,
    ) -> Dict[str, Any]:
        """Traslada landmarks normalizados a las coordenadas del lienzo VTON."""
        if not pose.landmarks.get("points"):
            return dict(pose.landmarks)

        source_w, source_h = source_size
        source_aspect = source_w / max(1, source_h)
        target_aspect = target_w / target_h
        if source_aspect > target_aspect:
            new_w = target_w
            new_h = int(target_w / source_aspect)
        else:
            new_h = target_h
            new_w = int(target_h * source_aspect)
        pos_x = (target_w - new_w) // 2
        pos_y = target_h - new_h

        mapped = dict(pose.landmarks)
        mapped_points = {}
        for name, point in pose.landmarks["points"].items():
            mapped_points[name] = {
                "x": round(pos_x + point["x"] * new_w, 2),
                "y": round(pos_y + point["y"] * new_h, 2),
                "z": point.get("z", 0.0),
                "visibility": point.get("visibility", 0.0),
            }
        mapped["points"] = mapped_points

        required = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        if all(name in mapped_points for name in required):
            ls = mapped_points["left_shoulder"]
            rs = mapped_points["right_shoulder"]
            lh = mapped_points["left_hip"]
            rh = mapped_points["right_hip"]
            shoulder_center = VirtualTryonAIService._point_midpoint(ls, rs)
            hip_center = VirtualTryonAIService._point_midpoint(lh, rh)
            mapped.update({
                "shoulder_center": shoulder_center,
                "hip_center": hip_center,
                "shoulder_width": round(VirtualTryonAIService._point_distance(ls, rs), 2),
                "hip_width": round(VirtualTryonAIService._point_distance(lh, rh), 2),
                "torso_height": round(VirtualTryonAIService._point_distance(shoulder_center, hip_center), 2),
            })
        return mapped

    # ─── Landmarks Anatómicos ───

    @classmethod
    def get_garment_landmarks(cls, product_tags: str = "", category_name: str = "") -> Dict[str, Any]:
        """Determina los landmarks anatómicos de una prenda según sus tags y categoría.

        Busca primero en los landmarks calibrados específicos del catálogo,
        luego cae en los defaults genéricos por tipo de prenda.
        """
        tags_lower = (product_tags or "").lower()
        cat_lower = (category_name or "").lower()

        # Buscar match específico por tipo de corte en los tags
        for landmark_key, landmark_data in GARMENT_LANDMARKS_DB.items():
            if landmark_key.startswith("default_"):
                continue
            ltype = landmark_data.get("type", "")
            if ltype and ltype in tags_lower:
                return landmark_data

        # Heurística por nombre de categoría y tags
        if any(k in tags_lower for k in ["peplum", "plisada", "escote v", "v_neck", "v-neck"]):
            return GARMENT_LANDMARKS_DB["peplum_v_neck"]
        if any(k in tags_lower for k in ["off-shoulder", "off_shoulder", "barco", "boat"]):
            return GARMENT_LANDMARKS_DB["off_shoulder_double_breasted"]
        if any(k in tags_lower for k in ["blazer", "solapa", "lapel", "sastre"]):
            return GARMENT_LANDMARKS_DB["blazer_notch_lapel_peplum"]
        if any(k in tags_lower for k in ["cuello redondo", "crew", "caja", "round"]):
            return GARMENT_LANDMARKS_DB["crew_neck_structured"]

        # Defaults genéricos por categoría
        is_dress = any(k in cat_lower for k in ["vestido", "dress", "mono", "enterizo"])
        is_bottom = any(k in cat_lower for k in ["pantalon", "pantalón", "falda", "jean", "short"])

        if is_dress:
            return GARMENT_LANDMARKS_DB["default_dress"]
        elif is_bottom:
            return GARMENT_LANDMARKS_DB["default_bottom"]
        return GARMENT_LANDMARKS_DB["default_top"]

    @classmethod
    def compute_body_landmarks(cls, height_cm: float = 168, chest_cm: float = 90,
                                waist_cm: float = 70, hip_cm: float = 94) -> Dict[str, Any]:
        """Calcula los landmarks del cuerpo basados en las medidas biométricas del usuario."""
        base = dict(BODY_LANDMARKS)

        # Ajustar ancho de hombros según medida de pecho (aproximación proporcional)
        shoulder_span = 0.44
        if chest_cm < 86:
            shoulder_span = 0.38
        elif chest_cm <= 92:
            shoulder_span = 0.42
        elif chest_cm <= 100:
            shoulder_span = 0.46
        elif chest_cm <= 108:
            shoulder_span = 0.50
        else:
            shoulder_span = 0.54

        base["shoulder_l_x"] = 0.50 - shoulder_span / 2
        base["shoulder_r_x"] = 0.50 + shoulder_span / 2
        base["shoulder_span"] = shoulder_span

        return base

    # ─── VTON Principal ───

    @classmethod
    def generate_vton_look(
        cls,
        person_image_data: str,
        garment_image_url: str,
        product_name: str,
        category: str = "tops",
        model_choice: str = "IDM-VTON",
        recommended_size: str = "M",
        garment_landmarks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecuta la síntesis de vestimenta virtual combinando la persona y la prenda."""
        start_time = time.time()
        model_used = (model_choice or "IDM-VTON").upper()
        normalized_category = cls.normalize_category(category)
        raw_person_for_pose = cls._load_image(person_image_data)
        pose_analysis = (
            cls._analyze_pose_image(raw_person_for_pose)
            if raw_person_for_pose
            else PoseAnalysisResult({}, 0.0, False, "none")
        )

        # 1. Intento con Fashn.ai si está configurado
        if model_used == "FASHN_AI" and FASHN_API_KEY:
            try:
                res = cls._call_fashn_api(
                    person_image_data, garment_image_url, normalized_category
                )
                if res:
                    elapsed = round(time.time() - start_time, 2)
                    return {
                        "result_image_url": res,
                        "model_used": "Fashn.ai",
                        "processing_time_sec": elapsed,
                        "pose_confidence": pose_analysis.confidence,
                        "pose_valid": pose_analysis.valid,
                        "pose_source": pose_analysis.source,
                        "pose_landmarks": pose_analysis.landmarks,
                        "fit_mode": "fashn-diffusion",
                        "style_advice": f"Prenda '{product_name}' sintetizada con precisión mediante la API de Fashn.ai.",
                    }
            except Exception as e:
                logger.warning(f"Error al invocar Fashn.ai API: {e}. Pasando a motor de difusión...")

        # 2. Intento con IDM-VTON (Hugging Face)
        if HUGGINGFACE_API_TOKEN:
            try:
                res = cls._call_idm_vton_api(
                    person_image_data, garment_image_url, normalized_category
                )
                if res:
                    elapsed = round(time.time() - start_time, 2)
                    return {
                        "result_image_url": res,
                        "model_used": "IDM-VTON (Diffusion)",
                        "processing_time_sec": elapsed,
                        "pose_confidence": pose_analysis.confidence,
                        "pose_valid": pose_analysis.valid,
                        "pose_source": pose_analysis.source,
                        "pose_landmarks": pose_analysis.landmarks,
                        "fit_mode": "idm-vton-diffusion",
                        "style_advice": f"Prenda '{product_name}' sintetizada exitosamente con difusión IDM-VTON conservando texturas y caída.",
                    }
            except Exception as e:
                logger.warning(f"Error en endpoint IDM-VTON: {e}. Utilizando síntesis adaptativa...")

        # 3. Motor de Síntesis Adaptativa Local con Landmarks Anatómicos
        result_url = cls._synthesize_adaptive_tryon(
            person_image_data=person_image_data,
            garment_image_url=garment_image_url,
            category=normalized_category,
            recommended_size=recommended_size,
            garment_landmarks=garment_landmarks,
            pose_analysis=pose_analysis,
        )
        elapsed = round(time.time() - start_time, 2)
        local_reason = "FASHN no configurado" if model_used == "FASHN_AI" else "sin motor remoto configurado"

        return {
            "result_image_url": result_url["result_image_url"],
            "model_used": f"Previsualización local ({local_reason})",
            "processing_time_sec": elapsed,
            "mask_confidence": result_url.get("mask_confidence", 0.0),
            "mask_reliable": result_url.get("mask_reliable", False),
            "mask_source": result_url.get("mask_source", "none"),
            "pose_confidence": result_url.get("pose_confidence", 0.0),
            "pose_valid": result_url.get("pose_valid", False),
            "pose_source": result_url.get("pose_source", "none"),
            "pose_landmarks": result_url.get("pose_landmarks", {}),
            "fit_mode": result_url.get("fit_mode", "unknown"),
            "style_advice": (
                f"Previsualización local de '{product_name}' para Talla {recommended_size}. "
                "La máscara se usa solo si supera el 75% de calidad; de lo contrario se aplica un ajuste conservador. "
                "Configura FASHN o ejecuta IDM-VTON/CatVTON con GPU para un resultado fotorrealista."
            ),
        }

    @classmethod
    def _call_fashn_api(cls, person_image: str, garment_image: str, category: str) -> Optional[str]:
        """Llamada a la API REST de Fashn.ai para Virtual Try-On."""
        headers = {
            "Authorization": f"Bearer {FASHN_API_KEY}",
            "Content-Type": "application/json",
        }
        external_person = cls._as_external_image(person_image)
        external_garment = cls._as_external_image(garment_image)
        if not external_person or not external_garment:
            logger.warning("No se pudieron preparar las imagenes para FASHN.")
            return None

        if FASHN_MODEL_NAME == "tryon-max":
            inputs = {
                "model_image": external_person,
                "product_image": external_garment,
                "generation_mode": "balanced",
                "resolution": "1k",
                "num_images": 1,
                "output_format": "jpeg",
            }
        else:
            inputs = {
                "model_image": external_person,
                "garment_image": external_garment,
                "category": category,
                "mode": "balanced",
                "num_samples": 1,
                "output_format": "jpeg",
            }
        payload = {"model_name": FASHN_MODEL_NAME, "inputs": inputs}
        try:
            resp = requests.post(
                f"{FASHN_API_BASE}/v1/run",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code not in [200, 201]:
                logger.warning("FASHN /v1/run devolvio %s: %s", resp.status_code, resp.text[:300])
                return None

            data = resp.json()
            if data.get("output"):
                return data["output"][0]

            prediction_id = data.get("id")
            if not prediction_id:
                logger.warning("FASHN no devolvio id de prediccion: %s", data)
                return None

            deadline = time.time() + FASHN_POLL_TIMEOUT_SEC
            while time.time() < deadline:
                status_resp = requests.get(
                    f"{FASHN_API_BASE}/v1/status/{prediction_id}",
                    headers={"Authorization": f"Bearer {FASHN_API_KEY}"},
                    timeout=15.0,
                )
                if status_resp.status_code != 200:
                    logger.warning("FASHN status devolvio %s", status_resp.status_code)
                    return None
                status_data = status_resp.json()
                state = status_data.get("status")
                if state == "completed":
                    output = status_data.get("output") or []
                    return output[0] if output else None
                if state == "failed":
                    logger.warning("FASHN fallo: %s", status_data.get("error"))
                    return None
                time.sleep(2.0)
            logger.warning("FASHN excedio el tiempo maximo de espera.")
        except Exception as e:
            logger.warning(f"Error en Fashn API: {e}")
        return None

    @classmethod
    def _as_external_image(cls, source: str) -> Optional[str]:
        """Convierte rutas locales/localhost a data URI para que FASHN pueda leerlas."""
        if not source:
            return None
        if source.startswith("data:image"):
            return source

        parsed = urlparse(source)
        host = (parsed.hostname or "").lower()
        if parsed.scheme in ("http", "https") and host not in ("localhost", "127.0.0.1", "::1"):
            return source

        img = cls._load_image(source)
        if img is None:
            return None
        return cls._image_to_data_uri(img)

    @staticmethod
    def _image_to_data_uri(img: Image.Image) -> str:
        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )
        output = io.BytesIO()
        if has_alpha:
            img.convert("RGBA").save(output, format="PNG", optimize=True)
            mime = "image/png"
        else:
            img.convert("RGB").save(output, format="JPEG", quality=95, optimize=True)
            mime = "image/jpeg"
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @classmethod
    def _call_idm_vton_api(cls, person_image: str, garment_image: str, category: str) -> Optional[str]:
        """Llamada a la API de inferencia de Hugging Face con el checkpoint de IDM-VTON."""
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
            "Content-Type": "application/json",
        }
        # Endpoint de modelo IDM-VTON en Hugging Face
        api_url = "https://api-inference.huggingface.co/models/yisol/IDM-VTON"
        payload = {
            "inputs": {
                "human_img": cls._as_external_image(person_image),
                "garm_img": cls._as_external_image(garment_image),
                "garment_des": category,
                "is_checking": True,
            }
        }
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=45.0)
            if resp.status_code == 200:
                # Retorna imagen binaria sintetizada en Base64
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.warning(f"Error en endpoint IDM-VTON Hugging Face: {e}")
        return None

    @classmethod
    def _load_image(cls, source: str) -> Optional[Image.Image]:
        """Carga una imagen desde Base64, URL HTTP o archivo del sistema de archivos local."""
        if not source:
            return None
        try:
            # 1. Base64
            if source.startswith("data:image"):
                header, encoded = source.split(",", 1)
                b = base64.b64decode(encoded)
                return Image.open(io.BytesIO(b)).convert("RGBA")
            
            # 2. URL remota HTTP / HTTPS
            if source.startswith("http://") or source.startswith("https://"):
                r = requests.get(source, timeout=8.0)
                if r.status_code == 200:
                    return Image.open(io.BytesIO(r.content)).convert("RGBA")
                return None

            # 3. Ruta local en disco (ej. /uploads/products/blusa.png)
            clean_path = source.lstrip("/\\")
            # Directorio raíz del backend
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            candidates = [
                os.path.join(backend_dir, clean_path),
                os.path.join(backend_dir, "uploads", clean_path.replace("uploads/", "").replace("uploads\\", "")),
                os.path.abspath(clean_path),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    return Image.open(c).convert("RGBA")
        except Exception as e:
            logger.warning(f"Error al cargar imagen '{source[:60]}': {e}")
        return None

    @classmethod
    def _isolate_garment_white_bg(cls, img: Image.Image) -> Image.Image:
        """Estandariza la prenda removiendo fondos claros para generar canal alfa limpio."""
        rgba = img.convert("RGBA")
        datas = rgba.getdata()
        new_data = []
        for item in datas:
            # Si el píxel es blanco o casi blanco de estudio (>236 en todos los canales y baja saturación)
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                diff = max(item[:3]) - min(item[:3])
                if diff < 15:
                    new_data.append((255, 255, 255, 0))  # Totalmente transparente
                    continue
            # Transición suave en bordes claros
            if item[0] > 218 and item[1] > 218 and item[2] > 218:
                diff = max(item[:3]) - min(item[:3])
                if diff < 12:
                    alpha = int(255 * (1.0 - (min(item[:3]) - 218) / 20.0))
                    new_data.append((item[0], item[1], item[2], max(0, min(255, alpha))))
                    continue
            new_data.append(item)
        rgba.putdata(new_data)
        alpha_bbox = rgba.getchannel("A").getbbox()
        if not alpha_bbox:
            return rgba
        left, top, right, bottom = alpha_bbox
        pad_x = max(2, int((right - left) * 0.02))
        pad_y = max(2, int((bottom - top) * 0.02))
        return rgba.crop((
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(rgba.width, right + pad_x),
            min(rgba.height, bottom + pad_y),
        ))

    @classmethod
    def _standardize_person_canvas(cls, person_img: Optional[Image.Image], target_w: int = 720, target_h: int = 1080) -> Image.Image:
        """Estandariza la foto de la persona a 9:16 sobre fondo neutro uniforme de estudio (#F0EFEB)."""
        # Fondo neutro de estudio fotográfico editorial (como en las referencias de Kristine)
        studio_bg = Image.new("RGBA", (target_w, target_h), (240, 239, 235, 255))
        if person_img is None:
            return studio_bg

        # Redimensionar manteniendo aspecto y anclando al suelo
        aspect = person_img.width / max(1, person_img.height)
        target_aspect = target_w / target_h
        if aspect > target_aspect:
            new_w = target_w
            new_h = int(target_w / aspect)
        else:
            new_h = target_h
            new_w = int(target_h * aspect)

        p_resized = person_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = (target_w - new_w) // 2
        pos_y = target_h - new_h  # Alineado a la base

        if p_resized.mode == "RGBA":
            studio_bg.paste(p_resized, (pos_x, pos_y), p_resized)
        else:
            studio_bg.paste(p_resized, (pos_x, pos_y))

        return studio_bg

    @classmethod
    def _standardize_person_canvas_with_bbox(
        cls,
        person_img: Optional[Image.Image],
        target_w: int = 720,
        target_h: int = 1080,
    ) -> tuple[Image.Image, tuple[int, int, int, int]]:
        """Normaliza la foto y conserva el bounding box visible de la persona."""
        studio_bg = Image.new("RGBA", (target_w, target_h), (240, 239, 235, 255))
        if person_img is None:
            return studio_bg, (0, 0, target_w, target_h)

        source = person_img.convert("RGBA")
        alpha_bbox = source.getchannel("A").point(
            lambda value: 255 if value >= 32 else 0
        ).getbbox() or (0, 0, source.width, source.height)
        aspect = source.width / max(1, source.height)
        target_aspect = target_w / target_h
        if aspect > target_aspect:
            new_w = target_w
            new_h = int(target_w / aspect)
        else:
            new_h = target_h
            new_w = int(target_h * aspect)

        resized = source.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = (target_w - new_w) // 2
        pos_y = target_h - new_h
        studio_bg.paste(resized, (pos_x, pos_y), resized)

        scale_x = new_w / max(1, source.width)
        scale_y = new_h / max(1, source.height)
        bbox = (
            max(0, int(pos_x + alpha_bbox[0] * scale_x)),
            max(0, int(pos_y + alpha_bbox[1] * scale_y)),
            min(target_w, int(pos_x + alpha_bbox[2] * scale_x)),
            min(target_h, int(pos_y + alpha_bbox[3] * scale_y)),
        )
        return studio_bg, bbox

    @classmethod
    def _standardize_person_mask(
        cls,
        person_img: Optional[Image.Image],
        target_w: int = 720,
        target_h: int = 1080,
    ) -> Image.Image:
        """Traslada la máscara alfa de la persona al lienzo final del VTON."""
        canvas = Image.new("L", (target_w, target_h), 0)
        if person_img is None:
            return canvas

        source = person_img.convert("RGBA")
        alpha = source.getchannel("A")
        aspect = source.width / max(1, source.height)
        target_aspect = target_w / target_h
        if aspect > target_aspect:
            new_w = target_w
            new_h = int(target_w / aspect)
        else:
            new_h = target_h
            new_w = int(target_h * aspect)

        resized = alpha.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = (target_w - new_w) // 2
        pos_y = target_h - new_h
        canvas.paste(resized, (pos_x, pos_y), resized)
        return canvas

    @staticmethod
    def _warp_garment_to_quad(
        garment: Image.Image,
        top_left: tuple[float, float],
        top_right: tuple[float, float],
        bottom_right: tuple[float, float],
        bottom_left: tuple[float, float],
        target_w: int,
        target_h: int,
    ) -> Optional[Image.Image]:
        """Deforma la prenda a un cuadrilátero anatómico usando perspectiva."""
        try:
            import cv2
            import numpy as np

            source = np.float32([
                [0, 0],
                [max(1, garment.width - 1), 0],
                [max(1, garment.width - 1), max(1, garment.height - 1)],
                [0, max(1, garment.height - 1)],
            ])
            destination = np.float32([
                top_left,
                top_right,
                bottom_right,
                bottom_left,
            ])
            transform = cv2.getPerspectiveTransform(source, destination)
            rgba = np.asarray(garment.convert("RGBA"))
            warped = cv2.warpPerspective(
                rgba,
                transform,
                (target_w, target_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0),
            )
            return Image.fromarray(warped, mode="RGBA")
        except ImportError:
            logger.info("OpenCV no está instalado; se conserva el ajuste rectangular.")
        except Exception as exc:
            logger.warning("No se pudo deformar la prenda con perspectiva: %s", exc)
        return None

    @classmethod
    def _warp_garment_to_pose(
        cls,
        garment: Image.Image,
        pose: Dict[str, Any],
        category: str,
        garment_landmarks: Optional[Dict[str, Any]],
        scale_mult: float,
        target_w: int,
        target_h: int,
        body_bottom: int,
    ) -> Optional[Image.Image]:
        """Calcula una malla de cuatro lados entre hombros, cintura y cadera."""
        points = pose.get("points", {})
        required = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        if not all(name in points for name in required):
            return None

        left_shoulder = points["left_shoulder"]
        right_shoulder = points["right_shoulder"]
        left_hip = points["left_hip"]
        right_hip = points["right_hip"]
        shoulder_center = pose["shoulder_center"]
        hip_center = pose["hip_center"]
        shoulder_width = max(1.0, float(pose["shoulder_width"]))
        hip_width = max(1.0, float(pose["hip_width"]))
        torso_height = max(1.0, float(pose["torso_height"]))

        axis_x = hip_center["x"] - shoulder_center["x"]
        axis_y = hip_center["y"] - shoulder_center["y"]
        axis_length = max(1.0, math.hypot(axis_x, axis_y))
        axis = (axis_x / axis_length, axis_y / axis_length)
        shoulder_dx = right_shoulder["x"] - left_shoulder["x"]
        shoulder_dy = right_shoulder["y"] - left_shoulder["y"]
        shoulder_length = max(1.0, math.hypot(shoulder_dx, shoulder_dy))
        across = (shoulder_dx / shoulder_length, shoulder_dy / shoulder_length)

        garment_type = (garment_landmarks or {}).get("type", "")
        normalized_category = (category or "").lower()
        is_dress = any(token in f"{garment_type} {normalized_category}" for token in (
            "dress", "vestido", "enterizo", "one-piece", "one piece", "mono"
        ))
        is_bottom = any(token in f"{garment_type} {normalized_category}" for token in (
            "bottom", "pantal", "falda", "skirt", "pants", "short"
        ))

        source_ratio = garment.height / max(1, garment.width)
        top_width = shoulder_width * (1.16 if is_dress else 1.10) * scale_mult
        if is_bottom:
            top_width = hip_width * 0.98 * scale_mult
            bottom_width = hip_width * 1.02 * scale_mult
            start_center = {
                "x": shoulder_center["x"] + axis[0] * torso_height * 0.56,
                "y": shoulder_center["y"] + axis[1] * torso_height * 0.56,
            }
            height = min(top_width * source_ratio, target_h * 0.48, max(80, body_bottom - start_center["y"]))
        elif is_dress:
            bottom_width = max(hip_width * 1.05, top_width * 0.92)
            start_center = {
                "x": shoulder_center["x"],
                "y": shoulder_center["y"],
            }
            height = min(top_width * source_ratio, target_h * 0.76, max(120, body_bottom - start_center["y"]))
        else:
            bottom_width = max(shoulder_width * 0.96, hip_width * 0.76) * scale_mult
            start_center = {
                "x": shoulder_center["x"] - axis[0] * torso_height * 0.03,
                "y": shoulder_center["y"] - axis[1] * torso_height * 0.03,
            }
            height = min(top_width * source_ratio, target_h * 0.46, max(100, torso_height * 1.18))

        shoulder_y = float((garment_landmarks or {}).get("shoulder_y", 0.06))
        start_center = {
            "x": start_center["x"] - axis[0] * height * shoulder_y,
            "y": start_center["y"] - axis[1] * height * shoulder_y,
        }
        end_center = {
            "x": start_center["x"] + axis[0] * height,
            "y": start_center["y"] + axis[1] * height,
        }

        top_left = (
            start_center["x"] - across[0] * top_width / 2,
            start_center["y"] - across[1] * top_width / 2,
        )
        top_right = (
            start_center["x"] + across[0] * top_width / 2,
            start_center["y"] + across[1] * top_width / 2,
        )
        bottom_left = (
            end_center["x"] - across[0] * bottom_width / 2,
            end_center["y"] - across[1] * bottom_width / 2,
        )
        bottom_right = (
            end_center["x"] + across[0] * bottom_width / 2,
            end_center["y"] + across[1] * bottom_width / 2,
        )
        return cls._warp_garment_to_quad(
            garment,
            top_left,
            top_right,
            bottom_right,
            bottom_left,
            target_w,
            target_h,
        )

    @staticmethod
    def _clip_garment_to_person(
        garment: Image.Image,
        person_mask: Optional[Image.Image],
    ) -> Image.Image:
        """Evita que la prenda final invada el fondo fuera de la silueta."""
        if person_mask is None:
            return garment
        # Dilatación mínima (1 px) más un difuminado suave: la dilatación de
        # 17 px original dejaba la prenda derramarse sobre el fondo alrededor
        # de hombros y mangas, y una dilatación sin difuminar recorta la prenda
        # con canto de tijera. Así el borde queda pegado a la silueta y suave.
        expanded_mask = person_mask.filter(ImageFilter.MaxFilter(3)).filter(
            ImageFilter.GaussianBlur(1.2)
        )
        alpha = ImageChops.multiply(garment.getchannel("A"), expanded_mask)
        clipped = garment.convert("RGBA")
        clipped.putalpha(alpha)
        return clipped

    # ─────────────────────────────────────────────────────────────────────
    #  Motor de amoldado anatómico (CU32)
    #  Sustituye el pegado rectangular por un remapeo fila a fila que hace
    #  que la prenda siga el eje del torso, los hombros, la cintura y la
    #  cadera reales detectados en la foto.
    # ─────────────────────────────────────────────────────────────────────

    @classmethod
    def _largest_component(cls, mask_array):
        """Conserva solo la mancha más grande de la máscara (descarta percha, marcas de agua)."""
        import cv2
        import numpy as np

        binary = (mask_array >= 32).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if count <= 2:
            return mask_array
        # stats[0] es el fondo; buscamos la componente de mayor área.
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        keep = (labels == largest).astype(np.uint8) * 255
        return np.minimum(mask_array, keep)

    @classmethod
    def _isolate_garment(cls, img: Image.Image) -> Image.Image:
        """Recorta la prenda de cualquier fondo usando segmentación por IA.

        El umbral de blancos anterior fallaba en los dos casos más comunes del
        catálogo: prendas blancas sobre fondo blanco (se borraba la prenda) y
        fotos de producto con sofá, percha o marca de agua (se pegaba el fondo
        entero sobre el cuerpo). rembg ``isnet-general-use`` resuelve ambos.
        """
        rgba = img.convert("RGBA")
        mask: Optional[Image.Image] = None
        try:
            from rembg import new_session, remove
            import numpy as np

            if cls._garment_rembg_session is None:
                cls._garment_rembg_session = new_session(GARMENT_REMBG_MODEL)
            buffer = io.BytesIO()
            rgba.save(buffer, format="PNG")
            mask_bytes = remove(
                buffer.getvalue(),
                session=cls._garment_rembg_session,
                only_mask=True,
                post_process_mask=True,
            )
            candidate = Image.open(io.BytesIO(mask_bytes)).convert("L")
            if candidate.size != rgba.size:
                candidate = candidate.resize(rgba.size, Image.Resampling.LANCZOS)
            array = cls._largest_component(np.asarray(candidate))
            candidate = Image.fromarray(array, mode="L")
            coverage = float((array >= 32).sum()) / max(1, array.size)
            # Una máscara vacía o que cubre casi todo indica que la segmentación
            # no encontró la prenda; en ese caso preferimos el método clásico.
            if 0.04 <= coverage <= 0.96:
                mask = candidate
        except ImportError:
            logger.info("rembg no disponible; se recorta la prenda por umbral de blancos.")
        except Exception as exc:
            logger.warning("No se pudo segmentar la prenda con IA: %s", exc)

        if mask is None:
            return cls._isolate_garment_white_bg(img)

        # Suavizamos el borde un píxel para que no quede recorte "de tijera".
        mask = mask.filter(ImageFilter.GaussianBlur(0.8))
        rgba.putalpha(mask)
        bbox = mask.point(lambda value: 255 if value >= 24 else 0).getbbox()
        if not bbox:
            return cls._isolate_garment_white_bg(img)
        return rgba.crop(bbox)

    @staticmethod
    def _smooth_profile(values, window: int = 9):
        """Suaviza un perfil 1D con media móvil para eliminar ruido del recorte."""
        import numpy as np

        if window < 3 or values.size < window:
            return values
        kernel = np.ones(window, dtype=np.float32) / window
        padded = np.pad(values, (window // 2, window // 2), mode="edge")
        return np.convolve(padded, kernel, mode="valid")[: values.size].astype(np.float32)

    @classmethod
    def _measure_garment_profile(cls, garment: Image.Image) -> Optional[Dict[str, Any]]:
        """Mide en la propia prenda dónde están hombros, centro y ancho por fila.

        Devuelve centro y semiancho por fila (en píxeles de la imagen de prenda)
        más la fila de hombros y la del bajo. Medirlos sobre el alfa real es lo
        que permite anclar la costura de hombro al hombro del cuerpo, en vez de
        confiar en las constantes del diccionario de landmarks.
        """
        import numpy as np

        alpha = np.asarray(garment.getchannel("A"), dtype=np.float32) / 255.0
        solid = alpha >= 0.35
        rows_with_content = np.where(solid.any(axis=1))[0]
        if rows_with_content.size < 8:
            return None

        top_row = int(rows_with_content[0])
        bottom_row = int(rows_with_content[-1])
        height, width = solid.shape

        left = np.full(height, np.nan, dtype=np.float32)
        right = np.full(height, np.nan, dtype=np.float32)
        for row in range(top_row, bottom_row + 1):
            hits = np.where(solid[row])[0]
            if hits.size:
                left[row] = float(hits[0])
                right[row] = float(hits[-1])

        valid = ~np.isnan(left)
        if valid.sum() < 8:
            return None
        indices = np.arange(height, dtype=np.float32)
        left = np.interp(indices, indices[valid], left[valid]).astype(np.float32)
        right = np.interp(indices, indices[valid], right[valid]).astype(np.float32)

        left = cls._smooth_profile(left)
        right = cls._smooth_profile(right)
        center = ((left + right) / 2.0).astype(np.float32)
        half_width = np.maximum(1.0, (right - left) / 2.0).astype(np.float32)

        # Recorte del gancho de la percha: una protuberancia estrecha y centrada
        # en el extremo superior. El umbral (32 % del ancho máximo) es holgado
        # para no comerse el cuello ni las solapas de un blazer.
        peak = float(half_width[top_row:bottom_row + 1].max())
        while top_row < bottom_row and half_width[top_row] < peak * 0.32:
            top_row += 1

        # La costura de hombro se apoya prácticamente en el borde superior de la
        # prenda: lo que queda por encima es cuello o solapa. Anclar aquí (y no
        # en la fila más ancha, que suele ser la punta de la manga o la cadera)
        # evita que el cuello se estire sobre la cabeza.
        span = max(4, bottom_row - top_row)
        shoulder_row = int(min(bottom_row - 2, top_row + span * 0.05))
        widest_upper = int(top_row + np.argmax(
            half_width[top_row:min(bottom_row, int(top_row + span * 0.35)) + 1]
        ))

        return {
            "center": center,
            "half_width": half_width,
            "top_row": top_row,
            "bottom_row": bottom_row,
            "shoulder_row": shoulder_row,
            "shoulder_half_width": float(half_width[widest_upper]),
            "widest_upper_row": widest_upper,
        }

    @classmethod
    def _measure_body_half_widths(cls, person_mask, samples, centers, across, analytic):
        """Mide el semiancho real del torso sobre la silueta, altura por altura.

        Escanea la máscara de la persona perpendicularmente al eje del torso y
        toma el tramo continuo que contiene el centro. El resultado se acota
        contra el perfil analítico para que un brazo pegado al cuerpo no infle
        la medida.
        """
        import numpy as np

        if person_mask is None:
            return analytic

        mask = np.asarray(person_mask, dtype=np.uint8) >= 96
        height, width = mask.shape
        measured = analytic.copy()
        sampled = np.zeros(len(samples), dtype=bool)
        step_x, step_y = across

        for index in range(len(samples)):
            cx, cy = centers[index]
            col, row = int(round(cx)), int(round(cy))
            if not (0 <= row < height and 0 <= col < width) or not mask[row, col]:
                continue
            limit = float(analytic[index]) * 1.6
            extent = []
            for direction in (-1.0, 1.0):
                distance = 0.0
                while distance < limit:
                    distance += 1.0
                    px = int(round(cx + step_x * distance * direction))
                    py = int(round(cy + step_y * distance * direction))
                    if not (0 <= px < width and 0 <= py < height) or not mask[py, px]:
                        break
                extent.append(distance)
            candidate = (extent[0] + extent[1]) / 2.0
            # La silueta MANDA. El perfil analítico solo descarta lecturas
            # absurdas (agujeros en la máscara o fugas al fondo): los landmarks
            # de MediaPipe marcan articulaciones, no contorno, y subestiman la
            # cadera real en torno a un 50 %.
            reference = float(analytic[index])
            measured[index] = float(np.clip(candidate, reference * 0.55, reference * 2.40))
            sampled[index] = True

        if sampled.sum() < 6:
            return analytic

        # Las alturas sin lectura fiable se rellenan interpolando las vecinas,
        # no volviendo al modelo teórico.
        indices = np.arange(len(samples), dtype=np.float32)
        filled = np.interp(indices, indices[sampled], measured[sampled]).astype(np.float32)
        return cls._smooth_profile(filled, window=7)

    @classmethod
    def _split_torso_and_sleeves(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Separa, dentro de la imagen de la prenda, el torso de las mangas.

        Sin esta separación la manga (que en la foto de producto sale hacia los
        lados) se comprime dentro del ancho del torso y produce las "hombreras"
        cuadradas: la prenda queda pegada al hombro en vez de bajar por el brazo.
        """
        import numpy as np

        half = profile["half_width"]
        shoulder_row = profile["shoulder_row"]
        bottom_row = profile["bottom_row"]
        top_row = profile["top_row"]
        span = max(4, bottom_row - shoulder_row)

        # El ancho del torso se toma por debajo de la sisa, donde ya no hay manga.
        chest_row = int(min(bottom_row, shoulder_row + span * 0.45))
        torso_reference = float(np.median(half[chest_row:min(bottom_row, chest_row + max(2, span // 6)) + 1]))
        torso_reference = max(2.0, torso_reference)

        # Tope de ancho del torso: por encima del pecho el torso no se ensancha
        # más de un 8 % respecto del pecho; todo lo que exceda es manga.
        cap = half.copy()
        cap[: chest_row + 1] = np.minimum(half[: chest_row + 1], torso_reference * 1.08)

        # La manga se busca a partir de su punto MÁS ANCHO (`widest_upper_row`),
        # no desde la costura de hombro: esa fila cae en el cuello, es estrecha,
        # y la condición de salida se cumplía en la primera iteración dejando la
        # banda vacía. Con ese fallo un blazer de manga corta se clasificaba
        # como prenda sin manga y se escalaba un 18 % de menos.
        widest_upper = int(profile.get("widest_upper_row", shoulder_row))
        sleeve_peak = float(half[widest_upper])
        has_sleeves = sleeve_peak > torso_reference * 1.14

        sleeve_end_row = widest_upper
        for row in range(widest_upper, min(bottom_row, widest_upper + int(span * 0.60)) + 1):
            sleeve_end_row = row
            if half[row] <= cap[row] * 1.02:
                break

        return {
            "torso_half": np.maximum(2.0, cap).astype(np.float32),
            "torso_reference": torso_reference,
            "chest_row": chest_row,
            "sleeve_end_row": int(sleeve_end_row),
            "sleeve_peak": sleeve_peak,
            "has_sleeves": bool(has_sleeves),
        }

    @classmethod
    def _warp_sleeves(
        cls,
        garment: Image.Image,
        profile: Dict[str, Any],
        split: Dict[str, Any],
        pose: Dict[str, Any],
        scale: float,
        target_w: int,
        target_h: int,
    ) -> Optional[Image.Image]:
        """Proyecta cada manga sobre su brazo, siguiendo hombro → codo.

        En la foto de producto la manga sale en horizontal; sobre el cuerpo debe
        bajar por el brazo. Se resuelve con una homografía por manga cuyo eje
        largo es la dirección del brazo detectada por MediaPipe.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            return None

        points = pose.get("points", {})
        if not split["has_sleeves"]:
            return None

        shoulder_width = float(pose.get("shoulder_width", 0.0))
        if shoulder_width <= 0:
            return None

        center = profile["center"]
        half = profile["half_width"]
        top_row = profile["top_row"]
        sleeve_end_row = split["sleeve_end_row"]
        if sleeve_end_row - top_row < 4:
            return None

        band = slice(top_row, sleeve_end_row + 1)
        band_center = float(np.median(center[band]))
        torso_edge = float(np.median(split["torso_half"][band]))
        sleeve_tip = float(half[band].max())
        if sleeve_tip - torso_edge < 3:
            return None

        source_rgba = np.asarray(garment.convert("RGBA"))
        layer = np.zeros((target_h, target_w, 4), dtype=np.uint8)
        sleeve_length = (sleeve_tip - torso_edge) * scale * 1.28
        sleeve_girth = (sleeve_end_row - top_row) * scale

        drew = False
        for side in ("left", "right"):
            shoulder = points.get(f"{side}_shoulder")
            elbow = points.get(f"{side}_elbow")
            if not shoulder or not elbow:
                continue
            if min(shoulder.get("visibility", 0.0), elbow.get("visibility", 0.0)) < 0.55:
                continue

            arm_dx = elbow["x"] - shoulder["x"]
            arm_dy = elbow["y"] - shoulder["y"]
            arm_len = math.hypot(arm_dx, arm_dy)
            if arm_len < 8:
                continue
            arm_dir = (arm_dx / arm_len, arm_dy / arm_len)
            # La manga nunca debe pasar del codo.
            length = min(sleeve_length, arm_len * 0.96)

            # El eje corto de la manga es perpendicular al brazo; lo orientamos
            # hacia el interior del cuerpo para que la costura de la sisa quede
            # del lado del torso.
            perp = (-arm_dir[1], arm_dir[0])
            to_center = (
                pose["shoulder_center"]["x"] - shoulder["x"],
                pose["shoulder_center"]["y"] - shoulder["y"],
            )
            if perp[0] * to_center[0] + perp[1] * to_center[1] < 0:
                perp = (-perp[0], -perp[1])

            outward = -1.0 if to_center[0] > 0 else 1.0  # hacia afuera del torso
            x_inner = band_center + outward * torso_edge
            x_outer = band_center + outward * sleeve_tip
            source = np.float32([
                [x_inner, top_row],
                [x_outer, top_row],
                [x_outer, sleeve_end_row],
                [x_inner, sleeve_end_row],
            ])

            origin = (
                shoulder["x"] - perp[0] * sleeve_girth * 0.55,
                shoulder["y"] - perp[1] * sleeve_girth * 0.55,
            )
            destination = np.float32([
                [origin[0], origin[1]],
                [origin[0] + arm_dir[0] * length, origin[1] + arm_dir[1] * length],
                [
                    origin[0] + arm_dir[0] * length + perp[0] * sleeve_girth,
                    origin[1] + arm_dir[1] * length + perp[1] * sleeve_girth,
                ],
                [origin[0] + perp[0] * sleeve_girth, origin[1] + perp[1] * sleeve_girth],
            ])

            try:
                transform = cv2.getPerspectiveTransform(source, destination)
                warped = cv2.warpPerspective(
                    source_rgba,
                    transform,
                    (target_w, target_h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0, 0),
                )
            except cv2.error as exc:
                logger.warning("No se pudo proyectar la manga %s: %s", side, exc)
                continue

            alpha = warped[..., 3:4].astype(np.float32) / 255.0
            layer[:] = (layer.astype(np.float32) * (1 - alpha) + warped.astype(np.float32) * alpha).astype("uint8")
            drew = True

        if not drew:
            return None
        return Image.fromarray(layer, mode="RGBA")

    @classmethod
    def _mold_garment_to_body(
        cls,
        garment: Image.Image,
        profile: Dict[str, Any],
        pose: Dict[str, Any],
        person_mask: Optional[Image.Image],
        garment_kind: str,
        ease: float,
        target_w: int,
        target_h: int,
    ) -> Optional[Dict[str, Any]]:
        """Amolda la prenda al cuerpo con un remapeo no lineal fila a fila.

        Para cada píxel del lienzo se calcula su posición ``t`` a lo largo del
        eje del torso y su desplazamiento lateral ``u`` normalizado por el
        semiancho objetivo de esa altura. Ese par (t, u) se convierte en
        coordenadas dentro de la prenda usando el perfil medido de la propia
        prenda. El semiancho objetivo mezcla la silueta real del cuerpo con la
        forma original de la prenda: así entalla en la cintura sin perder su
        vuelo. Las mangas se proyectan aparte sobre los brazos.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.info("OpenCV/NumPy no disponibles; no se puede amoldar la prenda.")
            return None

        points = pose.get("points", {})
        required = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        if not all(name in points for name in required):
            return None

        shoulder_center = pose["shoulder_center"]
        hip_center = pose["hip_center"]
        shoulder_width = max(8.0, float(pose["shoulder_width"]))
        hip_width = max(8.0, float(pose["hip_width"]))
        torso_height = max(8.0, float(pose["torso_height"]))

        axis_x = hip_center["x"] - shoulder_center["x"]
        axis_y = hip_center["y"] - shoulder_center["y"]
        axis_length = max(1.0, math.hypot(axis_x, axis_y))
        axis = (axis_x / axis_length, axis_y / axis_length)
        # El eje transversal es perpendicular al del torso: así la prenda se
        # inclina con el cuerpo en vez de quedar siempre horizontal.
        across = (-axis[1], axis[0])
        if (points["right_shoulder"]["x"] - points["left_shoulder"]["x"]) * across[0] < 0:
            across = (-across[0], -across[1])

        is_dress = garment_kind == "dress"
        is_bottom = garment_kind == "bottom"

        split = cls._split_torso_and_sleeves(profile)

        # En una foto de producto la manga ya cae hacia abajo y afuera, igual que
        # un brazo en reposo: reproyectarla solo empeora el resultado. Solo se
        # reproyecta cuando el brazo está realmente separado del torso (brazo en
        # jarra, mano en la cadera, brazo levantado).
        abduction = 0.0
        for side in ("left", "right"):
            shoulder = points.get(f"{side}_shoulder")
            elbow = points.get(f"{side}_elbow")
            if not shoulder or not elbow:
                continue
            arm_dx = elbow["x"] - shoulder["x"]
            arm_dy = elbow["y"] - shoulder["y"]
            arm_len = math.hypot(arm_dx, arm_dy)
            if arm_len < 8:
                continue
            cosine = (arm_dx * axis[0] + arm_dy * axis[1]) / arm_len
            abduction = max(abduction, math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))

        reproject_sleeves = split["has_sleeves"] and abduction >= SLEEVE_REPROJECTION_MIN_DEG
        torso_half_profile = (
            split["torso_half"] if reproject_sleeves else profile["half_width"].astype(np.float32)
        )

        # 1. Escala. Se ancla en el ANCHO MÁXIMO DE LA PARTE ALTA de la prenda
        #    (punta de manga a punta de manga, o de hombro a hombro si no lleva
        #    manga), que es la medida más estable que tiene una foto de producto.
        #
        #    Antes se anclaba en el "pecho", tomado a un 45 % del largo. En una
        #    prenda entallada esa fila cae en la CINTURA, no en el pecho, y la
        #    prenda salía escalada 1,44–1,61 veces el ancho de hombros; después
        #    los topes la comprimían a la fuerza hasta 1,20, que es justo el
        #    estiramiento antinatural que había que eliminar.
        garment_span = max(4, profile["bottom_row"] - profile["shoulder_row"])
        upper_half = max(2.0, profile["shoulder_half_width"])

        if is_bottom:
            reference_half = hip_width / 2.0 * 1.04
            scale = (reference_half * ease) / max(2.0, split["torso_reference"])
            anchor_offset = torso_height * 0.92
            min_length, max_length = torso_height * 0.60, torso_height * 2.30
        else:
            # La punta de manga cae sobre el brazo; sin manga, en la articulación.
            total_reach = (1.24 if split["has_sleeves"] else 1.02)
            if is_dress:
                total_reach *= 0.98
            scale = (shoulder_width * total_reach * 0.5 * ease) / upper_half
            anchor_offset = -torso_height * 0.07
            if is_dress:
                min_length, max_length = torso_height * 1.30, torso_height * 2.60
            else:
                min_length, max_length = torso_height * 0.70, torso_height * 1.45

        # El largo sale de la propia proporción de la prenda. Si se saliera del
        # rango razonable se corrige la ESCALA COMPLETA, nunca solo el eje
        # vertical: deformar un eje y no el otro es lo que achataba la prenda.
        length = garment_span * scale
        if length > max_length:
            scale *= max_length / length
            length = max_length
        elif length < min_length:
            scale *= min_length / length
            length = min_length
        length = float(length)

        anchor = (
            shoulder_center["x"] + axis[0] * anchor_offset,
            shoulder_center["y"] + axis[1] * anchor_offset,
        )
        # Lo que la prenda tiene por encima de la costura de hombro (cuello,
        # canesú, solapa) debe quedar por encima del punto de anclaje.
        head_room = min(
            (profile["shoulder_row"] - profile["top_row"]) * scale,
            length * 0.12,
        )

        # 2. Perfil objetivo de semianchos a lo largo del torso.
        sample_count = 96
        samples = np.linspace(0.0, 1.0, sample_count).astype(np.float32)
        centers = [
            (anchor[0] + axis[0] * length * t, anchor[1] + axis[1] * length * t)
            for t in samples
        ]

        hip_t = float(np.clip(torso_height / max(1.0, length), 0.25, 1.0))
        if is_bottom:
            control_t = np.array([0.0, 0.18, 1.0], dtype=np.float32)
            control_w = np.array([
                hip_width / 2.0 * 0.99,
                hip_width / 2.0 * 1.03,
                hip_width / 2.0 * 0.80,
            ], dtype=np.float32)
        else:
            control_t = np.array([0.0, hip_t * 0.32, hip_t * 0.62, hip_t, 1.0], dtype=np.float32)
            # Si la prenda tiene manga, su punta debe caer sobre el brazo, no en
            # la articulación del hombro: de lo contrario la sisa se apoya
            # dentro del cuerpo y deja ver la piel del brazo por el hueco.
            shoulder_reach = 1.26 if split["has_sleeves"] else 1.04
            # Todas las cotas se refieren al ancho de HOMBROS. La distancia
            # entre los puntos de cadera de MediaPipe es la articulación, no el
            # contorno, y da una cadera ~45 % más estrecha de lo real.
            control_w = np.array([
                shoulder_width / 2.0 * shoulder_reach,          # hombro / manga
                shoulder_width / 2.0 * 0.90,                    # pecho
                shoulder_width / 2.0 * 0.80,                    # cintura
                shoulder_width / 2.0 * 0.90,                    # cadera
                shoulder_width / 2.0 * (0.94 if is_dress else 0.90),  # bajo
            ], dtype=np.float32)
            order = np.argsort(control_t)
            control_t, control_w = control_t[order], control_w[order]

        analytic = np.interp(samples, control_t, control_w).astype(np.float32)
        measured = cls._measure_body_half_widths(
            person_mask, samples, centers, across, analytic
        )

        # Por debajo de la axila la silueta medida ES el torso y manda sin más.
        # Por encima, el escaneo lateral atraviesa los brazos (mide ~120 px
        # donde el hombro real es ~89), así que esa franja se modela: arranca en
        # la articulación del hombro y, si la prenda tiene manga, sube hasta el
        # brazo antes de fundirse con el torso a la altura de la axila.
        if is_bottom:
            body_half = measured
        else:
            # Las cotas se fijan en unidades del CUERPO (fracciones de la altura
            # de torso) y se traducen a `t`, porque `t` depende del largo de la
            # prenda. Antes eran constantes de `t` y la punta de manga caía a
            # 13 px del hombro en vez de a media altura del brazo, lo que
            # ensanchaba la prenda justo en la línea de hombro.
            unit = torso_height / max(1.0, length)
            shoulder_t = 0.07 * unit           # el ancla está 7 % por encima
            peak_t = shoulder_t + 0.17 * unit  # punta de manga, sobre el bíceps
            armpit_t = shoulder_t + 0.31 * unit
            armpit_t = float(min(armpit_t, 0.70))
            peak_t = float(min(peak_t, armpit_t * 0.75))

            torso_band = (samples >= armpit_t) & (samples <= min(1.0, armpit_t + 0.20))
            torso_reference_half = (
                float(np.median(measured[torso_band])) if torso_band.any()
                else float(shoulder_width / 2.0 * 0.88)
            )
            # El hombro no acaba en la articulación: el deltoides sobresale.
            # Con 1.02 la prenda moría justo en el punto de MediaPipe y dejaba
            # el hombro exterior al aire (cobertura medida del 51-85 %).
            reach = 1.26 if split["has_sleeves"] else 1.04
            shoulder_shape = np.interp(
                samples,
                [0.0, shoulder_t, peak_t, armpit_t],
                [
                    shoulder_width / 2.0 * 1.02,        # cuello / canesú
                    shoulder_width / 2.0 * 1.12,        # costura de hombro
                    shoulder_width / 2.0 * reach,       # punta de manga sobre el brazo
                    torso_reference_half,               # axila: empalma con el torso
                ],
            ).astype(np.float32)
            body_half = np.where(samples < armpit_t, shoulder_shape, measured).astype(np.float32)
        body_half = cls._smooth_profile(body_half, window=17)

        # Mezcla entre la forma propia de la prenda (escalada) y la silueta del
        # cuerpo. `conformity` controla cuánto abraza la prenda: 0 = calcomanía
        # plana (el comportamiento anterior), 1 = segunda piel.
        garment_rows = (
            profile["shoulder_row"]
            + samples * (profile["bottom_row"] - profile["shoulder_row"])
        ).astype(np.float32)
        row_index = np.arange(torso_half_profile.size, dtype=np.float32)
        garment_half_at = np.interp(garment_rows, row_index, torso_half_profile).astype(np.float32)
        uniform_half = garment_half_at * scale
        # Con la escala ya correcta, el amoldado es un ajuste suave, no una
        # renormalización. `conformity` bajo = la prenda conserva su patrón y
        # solo insinúa la cintura, que es lo que pide un resultado natural.
        conformity = 0.35 if is_bottom else 0.30
        target_half = (1.0 - conformity) * uniform_half + conformity * (body_half * ease)
        # La prenda nunca puede quedar más estrecha que el cuerpo: si lo hiciera
        # asomaría la piel o la ropa interior por los costados.
        # Dos únicas restricciones, ambas con sentido físico:
        #  - suelo: la prenda nunca puede quedar más estrecha que el cuerpo, o
        #    asomaría la piel por los costados;
        #  - techo: tampoco puede hincharse más de un 10 % sobre su propio
        #    patrón ya escalado, o dejaría de parecer esa prenda.
        # Forzarla a ir pegada al contorno (el `clip` anterior contra
        # `body_half`) era precisamente lo que la estiraba fila a fila.
        target_half = np.maximum(target_half, body_half * 1.00)
        target_half = np.minimum(target_half, uniform_half * 1.10)
        # En la franja alta manda la anatomía: `body_half` ya describe ahí el
        # hombro y la bajada hacia el brazo, así que la prenda no puede
        # excederlo. Sin esto, una foto de producto recortada a ras de hombro
        # (su fila más ancha es la primera) dibuja una barra por encima de los
        # hombros en lugar de una costura.
        upper_band = samples < (0.22 if is_bottom else armpit_t)
        target_half = np.where(
            upper_band, np.minimum(target_half, body_half * 1.10), target_half
        ).astype(np.float32)
        target_half = np.maximum(4.0, cls._smooth_profile(target_half, window=7))

        # 3. Remapeo inverso: cada píxel del lienzo busca su origen en la prenda.
        grid_y, grid_x = np.mgrid[0:target_h, 0:target_w]
        grid_x = grid_x.astype(np.float32)
        grid_y = grid_y.astype(np.float32)
        rel_x = grid_x - anchor[0]
        rel_y = grid_y - anchor[1]
        along = rel_x * axis[0] + rel_y * axis[1]
        lateral = rel_x * across[0] + rel_y * across[1]
        t_field = (along / max(1.0, length)).astype(np.float32)
        t_clamped = np.clip(t_field, 0.0, 1.0)

        # a) Coordenada lateral normalizada por el semiancho objetivo del cuerpo.
        half_field = np.interp(t_clamped, samples, target_half).astype(np.float32)
        u_field = (lateral / np.maximum(1.0, half_field)).astype(np.float32)

        # b) Apoyo en el hombro. La foto de producto está tumbada: el borde
        #    superior de la prenda es casi recto y, colocado tal cual, cae por
        #    debajo de los hombros y los deja al aire (efecto palabra de honor).
        #    Se mide el contorno REAL del hombro sobre la silueta y se desplaza
        #    la coordenada longitudinal, columna a columna, para que el borde de
        #    la prenda se apoye ahí. El efecto se desvanece hacia la cintura,
        #    que ya estaba bien y no debe tocarse.
        #
        #    El desplazamiento se calcula en DOS PASADAS: primero se deforma sin
        #    corregir para ver dónde cae realmente el borde en cada columna, y
        #    con esa medida se repite la deformación. Calcularlo contra el plano
        #    teórico del borde no sirve, porque el borde visible depende del
        #    recorte de la propia prenda en cada columna.
        #
        #    Un intento anterior desplazaba `t` en función de |u| en vez de por
        #    columna: al depender el desplazamiento de la propia coordenada
        #    lateral, el remuestreo dejaba de ser monótono y el escote salía
        #    invertido y festoneado.
        source = np.asarray(garment.convert("RGBA"))
        shoulder_fade = np.clip(1.0 - t_field / 0.45, 0.0, 1.0).astype(np.float32)
        row_axis = np.arange(profile["center"].size, dtype=np.float32)
        span_rows = float(profile["bottom_row"] - profile["shoulder_row"])

        def deform(drape):
            """Aplica el remapeo con un desplazamiento vertical por columna."""
            t_draped = (
                t_field - (drape[None, :] / max(1.0, length)) * shoulder_fade
            ).astype(np.float32)
            garment_row_field = (
                profile["shoulder_row"] + np.clip(t_draped, -1.0, 2.0) * span_rows
            ).astype(np.float32)
            garment_half_field = np.interp(
                np.clip(garment_row_field, 0, torso_half_profile.size - 1),
                row_index,
                torso_half_profile,
            ).astype(np.float32)
            garment_center_field = np.interp(
                np.clip(garment_row_field, 0, profile["center"].size - 1),
                row_axis,
                profile["center"],
            ).astype(np.float32)

            local_half = half_field
            local_u = u_field
            above = t_field < 0.0
            if above.any():
                reference = float(target_half[0])
                base = max(1.0, float(garment_half_at[0]))
                local_half = np.where(
                    above, reference * garment_half_field / base, half_field
                )
                local_u = (lateral / np.maximum(1.0, local_half)).astype(np.float32)

            map_x = (garment_center_field + local_u * garment_half_field).astype(np.float32)
            map_y = garment_row_field.astype(np.float32)
            warped = cv2.remap(
                source,
                map_x,
                map_y,
                interpolation=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0),
            )
            edge = np.clip((1.04 - np.abs(local_u)) / 0.04, 0.0, 1.0)
            alpha_channel = warped[..., 3].astype(np.float32) * edge
            alpha_channel[t_draped > 1.005] = 0.0
            warped[..., 3] = alpha_channel.astype("uint8")
            return warped

        warped = deform(np.zeros(target_w, dtype=np.float32))

        # Se probó una segunda pasada que desplazaba la prenda por columna para
        # apoyarla en el contorno del hombro. Visualmente parecía cubrir más,
        # pero la medición dijo lo contrario: la cobertura del deltoides bajaba
        # del 85 % al 77 %. Descartado; el hombro se resuelve ensanchando el
        # perfil objetivo en esa franja, no desplazando la prenda.

        torso_layer = Image.fromarray(warped, mode="RGBA")
        sleeves = (
            cls._warp_sleeves(garment, profile, split, pose, scale, target_w, target_h)
            if reproject_sleeves else None
        )
        if sleeves is not None:
            composite = sleeves.copy()
            composite.alpha_composite(torso_layer)
            torso_layer = composite

        inside_torso = ((np.abs(u_field) <= 1.0) & (t_field >= -0.02) & (t_field <= 1.01))
        return {
            "image": torso_layer,
            "torso_region": Image.fromarray((inside_torso * 255).astype("uint8"), mode="L"),
            "axis": axis,
            "across": across,
            "anchor": anchor,
            "length": round(length, 2),
            "scale": round(float(scale), 4),
            "conformity": conformity,
            "sleeves_reprojected": sleeves is not None,
            "arm_abduction_deg": round(abduction, 1),
        }

    @classmethod
    def _apply_body_shading(cls, garment: Image.Image, person_canvas: Image.Image) -> Image.Image:
        """Transfiere la iluminación del cuerpo a la prenda para que no parezca calcomanía."""
        try:
            import numpy as np
        except ImportError:
            return garment

        luminance = person_canvas.convert("L").filter(ImageFilter.GaussianBlur(34))
        light = np.asarray(luminance, dtype=np.float32) / 255.0
        alpha = np.asarray(garment.getchannel("A"), dtype=np.float32) / 255.0
        if alpha.sum() < 1.0:
            return garment

        mean_light = float((light * alpha).sum() / max(1.0, alpha.sum()))
        if mean_light <= 0.01:
            return garment
        # El color del tejido es un dato del catálogo: no se puede alterar. Antes
        # la modulación era tan fuerte que teñía la prenda con un degradado
        # oscuro-claro. Ahora es un realce de volumen de ±6 % como máximo, y se
        # calcula sobre una versión muy difuminada para que no copie el estampado
        # ni la ropa que la clienta lleva debajo.
        factor = np.clip(1.0 + 0.16 * (light - mean_light) / max(0.20, mean_light), 0.94, 1.06)

        rgba = np.asarray(garment.convert("RGBA"), dtype=np.float32)
        rgba[..., :3] = np.clip(rgba[..., :3] * factor[..., None], 0, 255)
        return Image.fromarray(rgba.astype("uint8"), mode="RGBA")

    @classmethod
    def _erase_underlying_sleeves(
        cls,
        person_canvas: Image.Image,
        person_mask: Optional[Image.Image],
        pose: Dict[str, Any],
        garment_alpha: Optional[Image.Image],
    ) -> Image.Image:
        """Borra la manga de la ropa que la persona ya lleva puesta.

        Un probador real recibe fotos de clientas vestidas, y los propios
        maniquíes de estudio llevan camiseta. Si la prenda nueva no tapa esa
        manga, asoma por los hombros y delata el montaje: se ve una camiseta
        negra saliendo de una blusa camel.

        La zona de trabajo es deliberadamente estrecha —por debajo de la línea
        de hombro, por encima del bajo de la prenda nueva, fuera de ella y
        alejada del eje del cuerpo—, de modo que solo caen ahí los brazos:

        * por encima del hombro está la cabeza, y el pelo tampoco es piel;
        * por debajo del bajo está la ropa inferior de la clienta, que no nos
          corresponde borrar;
        * en el eje están los pantalones o la falda, por el mismo motivo.

        Dentro de esa zona, lo que no es piel es tejido y se rellena con la piel
        de alrededor (inpainting de Telea).
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            return person_canvas

        points = pose.get("points", {})
        shoulder_width = float(pose.get("shoulder_width", 0.0))
        shoulder_center = pose.get("shoulder_center")
        if shoulder_width <= 0 or not shoulder_center:
            return person_canvas
        if "left_shoulder" not in points or "right_shoulder" not in points:
            return person_canvas

        rgb = np.asarray(person_canvas.convert("RGB"))
        height, width = rgb.shape[:2]

        # Umbral intermedio: con 96 el filo de la manga quedaba fuera y
        # sobrevivía como una raya negra; dilatando la máscara se colaba el
        # fondo alrededor del brazo y el relleno se comía el halo. 60 sobre la
        # máscara sin dilatar coge el contorno y nada más.
        body = (
            np.asarray(person_mask) >= 60
            if person_mask is not None
            else np.ones((height, width), dtype=bool)
        )
        alpha = (
            np.asarray(garment_alpha)
            if garment_alpha is not None
            else np.zeros((height, width), dtype=np.uint8)
        )
        rows_with_garment = np.where(alpha.max(axis=1) >= 40)[0]
        if rows_with_garment.size == 0:
            return person_canvas
        hem_row = int(rows_with_garment[-1])
        shoulder_row = int(min(points["left_shoulder"]["y"], points["right_shoulder"]["y"]))
        if hem_row - shoulder_row < 20:
            return person_canvas

        rows = np.arange(height)[:, None]
        columns = np.arange(width)[None, :]
        lateral = np.abs(columns - float(shoulder_center["x"]))

        # El landmark de hombro marca la ARTICULACIÓN, no el alto del hombro: la
        # costura de la camiseta de debajo queda por encima de él. La banda se
        # sube un poco para alcanzarla, pero en ese tramo se exige estar mucho
        # más separado del eje, porque ahí es donde cae el pelo.
        upper_reach = shoulder_row - shoulder_width * 0.20
        min_lateral = np.where(
            rows >= shoulder_row, shoulder_width * 0.22, shoulder_width * 0.28
        )
        # 210 y no 40: el borde de la prenda va difuminado, y bajo esa franja
        # semitransparente la manga de debajo seguía asomando en negro. Todo lo
        # que no esté cubierto del todo hay que limpiarlo igualmente.
        region = (
            body
            & (alpha < 210)
            & (rows > upper_reach)
            & (rows < hem_row)
            & (lateral > min_lateral)
        )
        if region.sum() < 400:
            return person_canvas

        # Piel en YCrCb: es el criterio clásico y se comporta bien con distintos
        # tonos de piel y temperaturas de color.
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        cr, cb = ycrcb[..., 1], ycrcb[..., 2]
        skin = (cr >= 133) & (cr <= 183) & (cb >= 77) & (cb <= 132)

        fabric = (region & ~skin).astype(np.uint8) * 255
        fabric = cv2.morphologyEx(fabric, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        fabric = cv2.dilate(fabric, np.ones((3, 3), np.uint8), iterations=1)
        fabric[~region] = 0

        share = float((fabric > 0).sum()) / max(1, int(region.sum()))
        # Nada que borrar, o tanto que probablemente no sea ropa (brazo en
        # sombra, manga larga hasta la muñeca, tatuaje): en la duda no se toca.
        if share < 0.04 or share > 0.80:
            return person_canvas

        # El relleno toma el color de la PIEL MÁS CERCANA DE LA MISMA FILA, no
        # de cualquier vecino. `cv2.inpaint` daba un gris sucio, porque la manga
        # toca el contorno de la silueta y el algoritmo propagaba el fondo hacia
        # dentro. Fila a fila se conserva además el degradado de luz del brazo.
        mask_bool = fabric > 0
        skin_in_body = skin & body
        filled = rgb.copy()
        fallback = (
            np.median(rgb[skin_in_body], axis=0).astype(np.uint8)
            if skin_in_body.any() else None
        )
        if fallback is None:
            return person_canvas

        for row in np.unique(np.where(mask_bool)[0]):
            targets = np.where(mask_bool[row])[0]
            sources = np.where(skin_in_body[row])[0]
            if sources.size:
                nearest = sources[np.abs(sources[None, :] - targets[:, None]).argmin(axis=1)]
                filled[row, targets] = rgb[row, nearest]
            else:
                filled[row, targets] = fallback

        # Un difuminado corto sobre la zona rellenada evita el bandeado que deja
        # copiar columna a columna.
        soft = cv2.GaussianBlur(filled, (0, 0), 2.2)
        blend = cv2.GaussianBlur(mask_bool.astype(np.float32), (0, 0), 2.0)[..., None]
        filled = (filled * (1 - blend) + soft * blend).astype(np.uint8)

        cleaned = Image.fromarray(filled).convert("RGBA")
        cleaned.putalpha(person_canvas.convert("RGBA").getchannel("A"))
        return cleaned

    @classmethod
    def _restore_occluders(
        cls,
        composed: Image.Image,
        person_canvas: Image.Image,
        person_mask: Optional[Image.Image],
        pose: Dict[str, Any],
        torso_region: Optional[Image.Image] = None,
    ) -> Image.Image:
        """Vuelve a dibujar antebrazos y manos por encima de la prenda.

        Sin esto la manga se pinta sobre el brazo y el resultado delata el pegado.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            return composed

        points = pose.get("points", {})
        shoulder_width = float(pose.get("shoulder_width", 0.0))
        if shoulder_width <= 0:
            return composed

        limb_mask = np.zeros((composed.height, composed.width), dtype=np.uint8)
        thickness = max(6, int(shoulder_width * 0.17))
        drew = False
        for elbow, wrist in (("left_elbow", "left_wrist"), ("right_elbow", "right_wrist")):
            if elbow not in points or wrist not in points:
                continue
            start, end = points[elbow], points[wrist]
            if min(start.get("visibility", 0.0), end.get("visibility", 0.0)) < 0.60:
                continue
            cv2.line(
                limb_mask,
                (int(start["x"]), int(start["y"])),
                (int(end["x"]), int(end["y"])),
                255,
                thickness,
            )
            # La mano se extiende algo más allá de la muñeca.
            cv2.circle(limb_mask, (int(end["x"]), int(end["y"])), int(thickness * 1.15), 255, -1)
            drew = True

        if not drew:
            return composed

        if torso_region is not None:
            # Resta del torso: dentro de la prenda manda la prenda.
            limb_mask = np.minimum(
                limb_mask,
                255 - np.asarray(torso_region.filter(ImageFilter.GaussianBlur(3)), dtype=np.uint8),
            )

        limb = Image.fromarray(limb_mask, mode="L").filter(ImageFilter.GaussianBlur(2.5))
        if person_mask is not None:
            limb = ImageChops.multiply(limb, person_mask)

        restored = composed.copy()
        restored.paste(person_canvas, (0, 0), limb)
        return restored

    @classmethod
    def _classify_garment_kind(
        cls, category: str, garment_landmarks: Optional[Dict[str, Any]]
    ) -> str:
        """Resuelve si la prenda es superior, inferior o de una pieza."""
        garment_type = (garment_landmarks or {}).get("type", "")
        haystack = f"{garment_type} {category or ''}".lower()
        if any(token in haystack for token in (
            "dress", "vestido", "enterizo", "one-piece", "one piece", "mono", "kaftan"
        )):
            return "dress"
        if any(token in haystack for token in (
            "bottom", "pantal", "falda", "skirt", "pants", "short", "jean", "inferior"
        )):
            return "bottom"
        return "top"

    @classmethod
    def _fallback_place_garment(
        cls,
        garment: Image.Image,
        person_bbox: tuple[int, int, int, int],
        garment_kind: str,
        ease: float,
        target_w: int,
        target_h: int,
    ) -> tuple[Image.Image, tuple[int, int]]:
        """Colocación conservadora cuando no hay pose utilizable (foto de espaldas, recorte…)."""
        body_left, body_top, body_right, body_bottom = person_bbox
        body_width = max(1, body_right - body_left)
        body_height = max(1, body_bottom - body_top)
        if body_left <= 2 and body_right >= target_w - 2:
            body_width = int(target_w * 0.36)
            body_left = (target_w - body_width) // 2
            body_right = body_left + body_width
            body_top = int(target_h * 0.05)
            body_height = int(target_h * 0.90)

        shoulder_y = body_top + int(body_height * 0.19)
        waist_y = body_top + int(body_height * 0.47)

        if garment_kind == "dress":
            width_factor, max_h_ratio, pos_y = 0.98, 0.74, shoulder_y
        elif garment_kind == "bottom":
            width_factor, max_h_ratio, pos_y = 0.80, 0.46, waist_y
        else:
            width_factor, max_h_ratio, pos_y = 0.92, 0.42, shoulder_y

        gw = max(8, int(body_width * width_factor * ease))
        gh = max(8, int(gw * (garment.height / max(1, garment.width))))
        if gh > int(target_h * max_h_ratio):
            gh = int(target_h * max_h_ratio)
            gw = max(8, int(gh * (garment.width / max(1, garment.height))))

        resized = garment.resize((gw, gh), Image.Resampling.LANCZOS)
        pos_x = int((body_left + body_right - gw) / 2)
        return resized, (pos_x, pos_y)

    @classmethod
    def _synthesize_adaptive_tryon(
        cls,
        person_image_data: str,
        garment_image_url: str,
        category: str = "tops",
        recommended_size: str = "M",
        garment_landmarks: Optional[Dict[str, Any]] = None,
        pose_analysis: Optional[PoseAnalysisResult] = None,
    ) -> Dict[str, Any]:
        """Motor de composición adaptativa local con amoldado anatómico.

        Pipeline: segmentación de la persona (rembg) → pose (MediaPipe) →
        recorte de la prenda por IA → medición del perfil de la prenda →
        remapeo no lineal sobre el torso → recorte a la silueta → iluminación
        → reposición de antebrazos y manos.
        """
        person_segmentation = None
        person_pose = pose_analysis or PoseAnalysisResult({}, 0.0, False, "none")
        molded = None
        try:
            target_w, target_h = 720, 1080

            # 1. Persona: segmentación y pose.
            raw_person = cls._load_image(person_image_data)
            person_segmentation = (
                cls._segment_image_with_confidence(raw_person) if raw_person else None
            )
            person_cutout = person_segmentation.image if person_segmentation else None
            if pose_analysis is None and raw_person is not None:
                person_pose = cls._analyze_pose_image(raw_person)
            mapped_pose = (
                cls._map_pose_to_canvas(person_pose, raw_person.size, target_w, target_h)
                if raw_person else {}
            )
            person_canvas, person_bbox = cls._standardize_person_canvas_with_bbox(
                person_cutout, target_w, target_h
            )
            clean_person = person_canvas.copy()
            mask_reliable = bool(person_segmentation and person_segmentation.mask_reliable)
            person_mask_canvas = (
                cls._standardize_person_mask(person_cutout, target_w, target_h)
                if mask_reliable else None
            )

            # 2. Prenda: recorte por IA y medición de su propio perfil.
            raw_garment = cls._load_image(garment_image_url)
            if raw_garment is not None:
                isolated_garment = cls._isolate_garment(raw_garment)
                profile = cls._measure_garment_profile(isolated_garment)
                garment_kind = cls._classify_garment_kind(category, garment_landmarks)

                size_ease = {
                    "XS": 0.97, "S": 1.00, "M": 1.04,
                    "L": 1.09, "XL": 1.14, "XXL": 1.19,
                }
                ease = size_ease.get((recommended_size or "M").upper(), 1.04)

                # La pose basta por sí sola para amoldar: ya no la condicionamos
                # a la calidad de la máscara, que solo sirve para recortar contra
                # el fondo y medir la silueta.
                pose_usable = bool(person_pose.valid and mapped_pose.get("points"))
                if profile is not None and pose_usable:
                    molded = cls._mold_garment_to_body(
                        garment=isolated_garment,
                        profile=profile,
                        pose=mapped_pose,
                        person_mask=person_mask_canvas,
                        garment_kind=garment_kind,
                        ease=ease,
                        target_w=target_w,
                        target_h=target_h,
                    )

                if molded is not None:
                    garment_layer, position = molded["image"], (0, 0)
                else:
                    garment_layer, position = cls._fallback_place_garment(
                        isolated_garment, person_bbox, garment_kind, ease, target_w, target_h
                    )

                # 3. Recorte a la silueta para que la prenda no invada el fondo.
                garment_layer = cls._clip_garment_to_person(
                    garment_layer,
                    person_mask_canvas if (mask_reliable and molded is not None) else None,
                )
                # 4. Limpiar la ropa que la persona lleva debajo y que la
                #    prenda nueva no llega a tapar (mangas de camiseta).
                if molded is not None and mapped_pose.get("points"):
                    garment_alpha = garment_layer.getchannel("A")
                    clean_person = cls._erase_underlying_sleeves(
                        clean_person, person_mask_canvas, mapped_pose, garment_alpha
                    )
                    person_canvas = cls._erase_underlying_sleeves(
                        person_canvas, person_mask_canvas, mapped_pose, garment_alpha
                    )

                # 5. Iluminación tomada del cuerpo.
                if molded is not None:
                    garment_layer = cls._apply_body_shading(garment_layer, clean_person)

                person_canvas.paste(garment_layer, position, garment_layer)

                # 6. Antebrazos y manos vuelven al frente.
                if molded is not None and mapped_pose.get("points"):
                    person_canvas = cls._restore_occluders(
                        person_canvas,
                        clean_person,
                        person_mask_canvas,
                        mapped_pose,
                        molded.get("torso_region"),
                    )

            output_buf = io.BytesIO()
            person_canvas.convert("RGB").save(output_buf, format="JPEG", quality=92)
            b64_res = base64.b64encode(output_buf.getvalue()).decode("utf-8")
            return {
                "result_image_url": f"data:image/jpeg;base64,{b64_res}",
                "mask_confidence": person_segmentation.confidence if person_segmentation else 0.0,
                "mask_reliable": person_segmentation.mask_reliable if person_segmentation else False,
                "mask_source": person_segmentation.source if person_segmentation else "none",
                "pose_confidence": person_pose.confidence,
                "pose_valid": person_pose.valid,
                "pose_source": person_pose.source,
                "pose_landmarks": person_pose.landmarks,
                "fit_mode": "anatomical-warp" if molded is not None else "fallback-paste",
            }

        except Exception as err:
            logger.error("Error en síntesis local: %s", err, exc_info=True)
            return {
                "result_image_url": person_image_data if person_image_data else garment_image_url,
                "mask_confidence": 0.0,
                "mask_reliable": False,
                "mask_source": "error",
                "pose_confidence": 0.0,
                "pose_valid": False,
                "pose_source": "error",
                "pose_landmarks": {},
                "fit_mode": "error",
            }
