# %% [markdown]
# # FashionStore · Vestidor Virtual (CU32) — Transfer Learning en 2 etapas
#
# Notebook para **Google Colab con GPU T4**. Ejecuta las celdas en orden, de arriba abajo.
#
# **Qué hace**
# 1. Monta Google Drive y **descubre solo** la estructura de tus datos
#    (`archive/labels_front.csv` para la Etapa 1 y `entrenamiento_ia_ropa/` para la Etapa 2).
# 2. **Human Parsing** con SegFormer preentrenado (`mattmdjaga/segformer_b2_clothes`):
#    cara, pelo, brazos, piernas, ropa superior, etc. Con eso arma la **representación agnóstica**
#    (borra la ropa que la persona lleva puesta) y la **máscara de preservación** (cara, cuello, brazos).
# 3. Modelo tipo **CP-VTON**: GMM (deformación de la prenda por flujo) + TOM (síntesis y fusión),
#    con **backbone ResNet34 preentrenado en ImageNet congelado** (transfer learning).
# 4. **Regla de oro**: la prenda deformada nunca puede dibujarse sobre cuello/brazos/cara.
#    Se garantiza por construcción: `final = preservar * original + (1 - preservar) * generado`.
# 5. Etapa 1 (pre-entrenamiento base) → Etapa 2 (fine-tuning con tu catálogo, solo GMM + fusión final).
# 6. Por época: gráficas Train vs Val, L1, Perceptual (VGG), IoU, SSIM, invasión de cuello y un grid
#    visual [Original | Agnóstica | Prenda | Resultado]. Checkpoints cada 5 épocas **en Drive** y
#    reanudación automática si Colab se desconecta.
# 7. Exporta el modelo final a **ONNX** (batch dinámico, opset 17) y lo verifica con onnxruntime
#    para servirlo desde el backend FastAPI (web + app móvil).
#
# **Cómo decide la estrategia de entrenamiento (según tus datos):**
# - `pareado`: hay pares (foto de persona, foto de prenda) → supervisión completa.
# - `auto`: hay fotos de personas pero sin prenda aparte → la prenda se recorta de la misma foto
#   (con deformaciones aleatorias) y la foto original es el objetivo. Supervisión completa.
# - `prenda`: solo fotos de prendas (catálogo) → se combinan con personas de la Etapa 1. No existe
#   una foto real del resultado, así que se entrena el **ajuste de forma** (Dice/IoU con la silueta
#   de la ropa de la persona) y la **fidelidad de textura** (L1/VGG/SSIM contra la prenda deformada).
#
# **Prueba rápida:** pon `MODO_PRUEBA = True` en la Celda 1 para correr todo en ~5 minutos con datos
# sintéticos y comprobar que el entorno funciona antes del entrenamiento real.

# %% [CELDA 1] Configuración general, instalación y GPU
import os
import sys
import re
import json
import time
import math
import copy
import random
import hashlib
import shutil
import tempfile
import subprocess
import inspect
import warnings
from pathlib import Path
from collections import defaultdict

# ← Pon True para una prueba rápida con datos sintéticos (no usa tu Drive).
MODO_PRUEBA = False or os.environ.get('VTON_MODO_PRUEBA') == '1'

EN_COLAB = 'google.colab' in sys.modules or os.path.isdir('/content/sample_data')
EN_NOTEBOOK = 'ipykernel' in sys.modules

if EN_COLAB:
    # Asegura todas las dependencias necesarias en Google Colab
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-q',
        'transformers', 'onnx', 'onnxruntime', 'onnxscript',
        'pandas', 'pyarrow', 'accelerate'
    ], check=False)

import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import matplotlib
if not EN_NOTEBOOK:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.utils.data.dataloader import default_collate
import torchvision
import torchvision.transforms.functional as TF
from torchvision.models import resnet34, vgg19

try:
    from IPython.display import display, clear_output
except ImportError:  # ejecución como script
    display = None
    clear_output = None

warnings.filterwarnings('ignore', category=UserWarning)

CFG = dict(
    # --- Rutas en Google Drive ---
    BASE_DIR='/content/drive/MyDrive/entrenamiento_ia_vestidor',
    ETAPA1_SUBDIR='archive',
    ETAPA1_CSV='labels_front.csv',
    ETAPA2_SUBDIR='entrenamiento_ia_ropa',
    SALIDA_SUBDIR='resultados_vton',          # checkpoints, gráficas, caché y ONNX (en Drive)
    # v2: 6 canales de parsing (fondo visible), clasificación persona/prenda por rostro y
    # composición sin halo. Los checkpoints v1 (5 canales) NO son compatibles: se entrena de nuevo
    # en carpetas etapa1_v2 / etapa2_v2 (la caché de imágenes se reutiliza).
    VERSION_MODELO='v2',
    # --- Datos ---
    IMG_H=256, IMG_W=192,                    # resolución CP-VTON (múltiplos de 32)
    MAX_IMG_ETAPA1=4000,                     # límite para terminar hoy en una T4 (None = todas)
    MAX_IMG_ETAPA2=None,
    VAL_SPLIT=0.1,
    PRESERVAR_BRAZOS=True,                   # regla de oro: los brazos originales van encima
    # --- Entrenamiento ---
    BATCH=8, WORKERS=2,
    EPOCAS_ETAPA1=20, EPOCAS_ETAPA2=15,
    LR_ETAPA1=2e-4, LR_ETAPA2=5e-5, WEIGHT_DECAY=1e-4,
    FACTOR_SCHEDULER=0.5, PACIENCIA_SCHEDULER=2,
    PACIENCIA_EARLY_STOP=6,
    CHECKPOINT_CADA=5,
    REANUDAR=True,                           # continúa desde last.pth si Colab se desconectó
    PESOS_PREENTRENADOS=True,                # ResNet34 / VGG19 de ImageNet
    PARSER_HF='mattmdjaga/segformer_b2_clothes',
    LAMBDAS=dict(l1=1.0, vgg=0.2, mascara=1.0, tv=0.5, cuello=2.0, comp=0.5, ssim=0.2),
    ONNX_OPSET=17,
    SEED=42,
)

if MODO_PRUEBA:
    CFG.update(BATCH=4, WORKERS=0, EPOCAS_ETAPA1=2, EPOCAS_ETAPA2=2, CHECKPOINT_CADA=1,
               PESOS_PREENTRENADOS=False, MAX_IMG_ETAPA1=None, PACIENCIA_EARLY_STOP=99)

H, W = CFG['IMG_H'], CFG['IMG_W']
assert H % 32 == 0 and W % 32 == 0, 'IMG_H e IMG_W deben ser múltiplos de 32'


def fijar_semilla(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


fijar_semilla(CFG['SEED'])
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
USA_AMP = DEVICE.type == 'cuda'          # precisión mixta: ~2x más rápido y menos memoria en T4
torch.backends.cudnn.benchmark = DEVICE.type == 'cuda'

print(f'PyTorch {torch.__version__} | torchvision {torchvision.__version__} | dispositivo: {DEVICE}')
if DEVICE.type == 'cuda':
    prop = torch.cuda.get_device_properties(0)
    print(f'GPU: {prop.name} ({prop.total_memory / 1024**3:.1f} GB)')
elif not MODO_PRUEBA:
    print('⚠️  No hay GPU activa. En Colab: Entorno de ejecución → Cambiar tipo → GPU T4.')
print('MODO_PRUEBA =', MODO_PRUEBA)

# %% [CELDA 2] Google Drive, rutas de datos (y datos sintéticos si MODO_PRUEBA)


def generar_datos_sinteticos(raiz, n_personas=40, n_prendas=12, seed=0):
    """Crea un mini-dataset con la MISMA estructura que tu Drive, para probar el pipeline."""
    rng = random.Random(seed)
    et1 = Path(raiz) / CFG['ETAPA1_SUBDIR'] / 'images'
    et2 = Path(raiz) / CFG['ETAPA2_SUBDIR']
    et1.mkdir(parents=True, exist_ok=True)
    et2.mkdir(parents=True, exist_ok=True)
    piel = (224, 172, 135)

    def camisa(draw, lab, cx, top, ancho, alto, color, franjas):
        pts = [(cx - ancho // 2, top), (cx + ancho // 2, top), (cx + ancho // 2 + 6, top + alto), (cx - ancho // 2 - 6, top + alto)]
        draw.polygon(pts, fill=color)
        lab.polygon(pts, fill=4)
        for k in range(top + 6, top + alto, franjas):
            draw.line([(cx - ancho // 2, k), (cx + ancho // 2, k)], fill=(255, 255, 255), width=2)

    filas = []
    for i in range(n_personas):
        w0, h0 = rng.choice([(192, 256), (300, 400), (240, 300)])
        img = Image.new('RGB', (w0, h0), (250, 250, 250))
        lab_img = Image.new('L', (w0, h0), 0)
        d, lab = ImageDraw.Draw(img), ImageDraw.Draw(lab_img)
        s = w0 / 192
        cx = w0 // 2 + rng.randint(-8, 8)
        color = tuple(rng.randint(30, 220) for _ in range(3))
        # piernas / pantalón
        d.rectangle([cx - 30 * s, 170 * s, cx + 30 * s, 250 * s], fill=(40, 60, 120))
        lab.rectangle([cx - 30 * s, 170 * s, cx + 30 * s, 250 * s], fill=6)
        # brazos
        d.rectangle([cx - 58 * s, 80 * s, cx - 42 * s, 165 * s], fill=piel)
        lab.rectangle([cx - 58 * s, 80 * s, cx - 42 * s, 165 * s], fill=14)
        d.rectangle([cx + 42 * s, 80 * s, cx + 58 * s, 165 * s], fill=piel)
        lab.rectangle([cx + 42 * s, 80 * s, cx + 58 * s, 165 * s], fill=15)
        # cuello (etiquetado como fondo a propósito)
        d.rectangle([cx - 9 * s, 55 * s, cx + 9 * s, 78 * s], fill=piel)
        # torso / camisa
        camisa(d, lab, cx, int(75 * s), int(84 * s), int(100 * s), color, rng.randint(6, 14))
        # cara y pelo
        d.ellipse([cx - 20 * s, 12 * s, cx + 20 * s, 58 * s], fill=piel)
        lab.ellipse([cx - 20 * s, 12 * s, cx + 20 * s, 58 * s], fill=11)
        d.pieslice([cx - 22 * s, 6 * s, cx + 22 * s, 40 * s], 180, 360, fill=(60, 40, 20))
        lab.pieslice([cx - 22 * s, 6 * s, cx + 22 * s, 40 * s], 180, 360, fill=2)
        nombre = f'persona_{i:03d}.jpg'
        img.save(et1 / nombre, quality=92)
        lab_img.save(et1 / f'persona_{i:03d}.labels.png')
        filas.append((f'images/{nombre}', rng.choice(['shirt', 'top', 'blouse'])))
    # una imagen corrupta para probar la robustez del cargador
    (et1 / 'corrupta_999.jpg').write_bytes(b'esto no es un jpg')
    filas.append(('images/corrupta_999.jpg', 'shirt'))
    with open(Path(raiz) / CFG['ETAPA1_SUBDIR'] / CFG['ETAPA1_CSV'], 'w', encoding='utf-8') as f:
        f.write('image,label\n' + '\n'.join(f'{a},{b}' for a, b in filas) + '\n')

    for j in range(n_prendas):
        img = Image.new('RGB', (300, 360), (255, 255, 255))
        lab_img = Image.new('L', (300, 360), 0)
        d, lab = ImageDraw.Draw(img), ImageDraw.Draw(lab_img)
        color = tuple(rng.randint(30, 220) for _ in range(3))
        camisa(d, lab, 150, 70, rng.randint(150, 190), rng.randint(180, 230), color, rng.randint(8, 16))
        img.save(et2 / f'prenda_{j:03d}.png')
        lab_img.save(et2 / f'prenda_{j:03d}.labels.png')
    print(f'Datos sintéticos creados en {raiz}')


def buscar_directorios_vton():
    """Busca de forma inteligente, rápida y segura las carpetas de datos en Google Drive."""
    if EN_COLAB:
        from google.colab import drive
        if not (os.path.exists('/content/drive/MyDrive') or os.path.exists('/content/drive/My Drive')):
            try:
                print('📂 Conectando y montando Google Drive en /content/drive...')
                drive.mount('/content/drive', force_remount=False)
            except Exception as e:
                print('Aviso montaje Drive:', e)

    dir_et1 = None
    dir_et2 = None
    base_dir = None

    def es_etapa1(p):
        if not p.is_dir():
            return False
        nom = p.name.strip().lower()
        if nom == 'archive':
            return True
        return ((p / 'selected_images').is_dir() or
                (p / 'labels_front.csv').is_file() or
                (p / 'labels_front.feather').is_file())

    def es_etapa2(p):
        if not p.is_dir():
            return False
        nom = p.name.strip().lower()
        if nom == 'entrenamiento_ia_ropa':
            return True
        return ((p / 'Vestidos').is_dir() or
                (p / 'Blusas').is_dir() or
                (p / 'Camisas').is_dir() or
                (p / 'cuerpos').is_dir() or
                (p / 'dataset_metadata.csv').is_file())

    # 1. Comprobar ruta directa configurada y variantes comunes
    candidatos_base = [
        Path(CFG['BASE_DIR']),
        Path('/content/drive/MyDrive/entrenamiento_ia_vestidor'),
        Path('/content/drive/My Drive/entrenamiento_ia_vestidor'),
        Path('/content/drive/MyDrive'),
        Path('/content/drive/My Drive'),
        Path('/content/drive/Shareddrives'),
        Path('/content/drive'),
        Path('/content'),
        Path('.'),
    ]

    for cand in candidatos_base[:3]:
        if cand.is_dir():
            sub1 = cand / CFG['ETAPA1_SUBDIR']
            sub2 = cand / CFG['ETAPA2_SUBDIR']
            if sub1.is_dir() or es_etapa1(sub1):
                dir_et1 = sub1
            if sub2.is_dir() or es_etapa2(sub2):
                dir_et2 = sub2
            if dir_et1 or dir_et2:
                base_dir = cand
                break

    # 2. Búsqueda BFS por niveles (profundidad máx. 3, sin rglob infinito que congele Drive)
    if dir_et1 is None or dir_et2 is None:
        print('🔍 Buscando carpetas de entrenamiento automáticamente en Google Drive...')
        visitados = set()
        cola = []
        for r in candidatos_base:
            if r.exists() and r.is_dir():
                cola.append((r, 0))

        while cola:
            curr, prof = cola.pop(0)
            try:
                curr_real = str(curr.resolve())
            except Exception:
                curr_real = str(curr)
            if curr_real in visitados or prof > 3:
                continue
            visitados.add(curr_real)

            # ¿Es este directorio Etapa 1 o Etapa 2?
            if dir_et1 is None and es_etapa1(curr):
                dir_et1 = curr
                print(f'   👉 Etapa 1 (archive) detectada en: {dir_et1}')
            if dir_et2 is None and es_etapa2(curr):
                dir_et2 = curr
                print(f'   👉 Etapa 2 (catálogo) detectada en: {dir_et2}')

            if dir_et1 is not None and dir_et2 is not None:
                break

            # ¿Es una carpeta contenedora del proyecto?
            nom_norm = re.sub(r'[^a-z0-9]', '', curr.name.lower())
            if 'entrenamiento' in nom_norm and 'vestid' in nom_norm:
                sub1 = curr / CFG['ETAPA1_SUBDIR']
                sub2 = curr / CFG['ETAPA2_SUBDIR']
                if dir_et1 is None and (sub1.is_dir() or es_etapa1(sub1)):
                    dir_et1 = sub1
                    print(f'   👉 Etapa 1 (archive) detectada en: {dir_et1}')
                if dir_et2 is None and (sub2.is_dir() or es_etapa2(sub2)):
                    dir_et2 = sub2
                    print(f'   👉 Etapa 2 (catálogo) detectada en: {dir_et2}')
                if base_dir is None:
                    base_dir = curr

            if dir_et1 is not None and dir_et2 is not None:
                break

            # Explorar subcarpetas inmediatas (nivel + 1)
            if prof < 3:
                try:
                    with os.scandir(curr) as it:
                        for entry in it:
                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    if entry.name.startswith('.') or entry.name in ('sample_data', '.ipynb_checkpoints', 'bin', 'etc', 'var', 'usr', 'lib', 'proc'):
                                        continue
                                    cola.append((Path(entry.path), prof + 1))
                            except Exception:
                                pass
                except Exception:
                    pass

    # Resolver carpeta base
    if base_dir is None:
        if dir_et1 is not None and dir_et1.parent.name not in ('MyDrive', 'My Drive', 'drive', 'content'):
            base_dir = dir_et1.parent
        elif dir_et2 is not None and dir_et2.parent.name not in ('MyDrive', 'My Drive', 'drive', 'content'):
            base_dir = dir_et2.parent
        elif os.path.exists('/content/drive/MyDrive'):
            base_dir = Path('/content/drive/MyDrive/entrenamiento_ia_vestidor')
        else:
            base_dir = Path(CFG['BASE_DIR'])

    if dir_et1 is None:
        dir_et1 = base_dir / CFG['ETAPA1_SUBDIR']
    if dir_et2 is None:
        dir_et2 = base_dir / CFG['ETAPA2_SUBDIR']

    return base_dir, dir_et1, dir_et2


if MODO_PRUEBA:
    BASE = Path(os.environ.get('VTON_DIR_PRUEBA') or ('/content/vton_prueba' if EN_COLAB else tempfile.mkdtemp(prefix='vton_')))
    if not (BASE / CFG['ETAPA1_SUBDIR']).exists():
        generar_datos_sinteticos(BASE)
    DIR_ETAPA1 = BASE / CFG['ETAPA1_SUBDIR']
    DIR_ETAPA2 = BASE / CFG['ETAPA2_SUBDIR']
    SALIDA = BASE / CFG['SALIDA_SUBDIR']
else:
    BASE, DIR_ETAPA1, DIR_ETAPA2 = buscar_directorios_vton()
    SALIDA = BASE / CFG['SALIDA_SUBDIR']

CACHE_DRIVE = SALIDA / 'cache'
# Copia local de la caché para leer rápido durante el entrenamiento (Drive es lento).
CACHE_LOCAL = Path('/content/cache_vton') if (EN_COLAB and not MODO_PRUEBA) else CACHE_DRIVE
for p in (SALIDA, CACHE_DRIVE, CACHE_LOCAL):
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e_mk:
        print(f'Aviso creando {p}: {e_mk}')

print('\n📂 Estado de carpetas de datos:')
for nombre, ruta in [('Etapa 1 (archive)', DIR_ETAPA1), ('Etapa 2 (catálogo)', DIR_ETAPA2)]:
    estado = '✅ Encontrada' if (ruta and ruta.exists()) else '❌ NO EXISTE'
    print(f'  · {nombre}: {ruta}  {estado}')
print(f'  · Salida de resultados: {SALIDA}')

if not DIR_ETAPA1 or not DIR_ETAPA1.exists():
    print('\n📋 Diagnóstico de carpetas detectadas en Google Drive:')
    for raiz in [Path('/content/drive/MyDrive'), Path('/content/drive/My Drive'), Path('/content')]:
        if raiz.exists():
            print(f'   Contenido de {raiz}:')
            try:
                for entry in sorted(os.listdir(raiz))[:25]:
                    print(f'     - {entry}')
            except Exception as e:
                print(f'     Error al listar {raiz}: {e}')
    raise FileNotFoundError(
        f'No se encontró la carpeta archive (Etapa 1) en {DIR_ETAPA1}.\n'
        f'Verifica que la carpeta "entrenamiento_ia_vestidor" con su subcarpeta "archive" esté en tu Google Drive.'
    )

# %% [CELDA 3] Utilidades de imágenes
EXT_IMG = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def listar_imagenes(raiz):
    """Todas las imágenes bajo 'raiz' de forma rápida y segura."""
    raiz = Path(raiz)
    if not raiz.exists():
        return []
    archivos = []
    for root, _, files in os.walk(raiz):
        for f in files:
            p = Path(root) / f
            nom = p.name.lower()
            if p.suffix.lower() in EXT_IMG and not nom.endswith('.labels.png') and not nom.endswith('_parse.png'):
                archivos.append(p)
    return sorted(archivos)


def abrir_imagen(ruta):
    """Abre una imagen en RGB respetando la orientación EXIF. Lanza excepción si está corrupta."""
    with Image.open(ruta) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert('RGB')
        im.load()                     # fuerza la decodificación completa (detecta archivos truncados)
        return im.copy()


def letterbox(im, w=W, h=H, relleno=(255, 255, 255), resample=Image.BICUBIC):
    """Escala sin deformar para caber en (w, h) y centra sobre un lienzo de color 'relleno'."""
    escala = min(w / im.width, h / im.height)
    nw, nh = max(1, round(im.width * escala)), max(1, round(im.height * escala))
    im = im.resize((nw, nh), resample)
    lienzo = Image.new(im.mode, (w, h), relleno)
    lienzo.paste(im, ((w - nw) // 2, (h - nh) // 2))
    return lienzo


def pil_a_tensor(im):
    """PIL RGB → tensor [3,H,W] en rango [-1, 1]."""
    return TF.to_tensor(im) * 2 - 1


def tensor_a_numpy_img(t):
    """Tensor [3,H,W] en [-1,1] → array HxWx3 en [0,1] para matplotlib."""
    return ((t.detach().float().cpu().clamp(-1, 1) + 1) / 2).permute(1, 2, 0).numpy()


def clave_de(ruta):
    return hashlib.md5(str(ruta).encode('utf-8')).hexdigest()[:16]

# %% [CELDA 4] Human Parsing (SegFormer preentrenado) — identifica cuello, brazos y piel visible

# Nuestra numeración de etiquetas (igual a la del modelo mattmdjaga/segformer_b2_clothes).
ETIQUETAS = {
    'background': 0, 'hat': 1, 'hair': 2, 'sunglasses': 3, 'upper-clothes': 4, 'skirt': 5,
    'pants': 6, 'dress': 7, 'belt': 8, 'left-shoe': 9, 'right-shoe': 10, 'face': 11,
    'left-leg': 12, 'right-leg': 13, 'left-arm': 14, 'right-arm': 15, 'bag': 16, 'scarf': 17,
}
L = ETIQUETAS
ANATOMIA = [L['hair'], L['face'], L['left-leg'], L['right-leg'], L['left-arm'], L['right-arm']]
ROPA = [L['upper-clothes'], L['skirt'], L['pants'], L['dress'], L['scarf'], L['belt']]


class ParserSegformer:
    """Parser humano preentrenado (no se entrena): produce un mapa de 18 partes por píxel."""

    def __init__(self, nombre_hf, device):
        from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation
        self.device = device
        self.proc = SegformerImageProcessor.from_pretrained(nombre_hf)
        self.modelo = AutoModelForSemanticSegmentation.from_pretrained(nombre_hf).to(device).eval()
        if device.type == 'cuda':
            self.modelo.half()
        # Traduce los ids del modelo a nuestros ids por NOMBRE (por si el orden cambia).
        id2label = {int(k): v.lower() for k, v in self.modelo.config.id2label.items()}
        self.lut = np.zeros(max(id2label) + 1, dtype=np.uint8)
        for k, nombre in id2label.items():
            self.lut[k] = ETIQUETAS.get(nombre, 0)
        print('Parser cargado. Etiquetas del modelo:', id2label)

    @torch.no_grad()
    def parsear(self, imagenes, rutas=None):
        pix = self.proc(images=imagenes, return_tensors='pt')['pixel_values']
        pix = pix.to(self.device, dtype=next(self.modelo.parameters()).dtype)
        logits = self.modelo(pixel_values=pix).logits
        logits = F.interpolate(logits.float(), size=(H, W), mode='bilinear', align_corners=False)
        mapas = logits.argmax(1).cpu().numpy()
        return [self.lut[m].astype(np.uint8) for m in mapas]


class ParserSintetico:
    """Solo para MODO_PRUEBA: lee el mapa '<imagen>.labels.png' que acompaña cada imagen."""

    def parsear(self, imagenes, rutas):
        salida = []
        for ruta in rutas:
            lab = Image.open(Path(ruta).with_suffix('.labels.png'))
            salida.append(np.array(letterbox(lab, relleno=0, resample=Image.NEAREST), dtype=np.uint8))
        return salida


PARSER = ParserSintetico() if MODO_PRUEBA else ParserSegformer(CFG['PARSER_HF'], DEVICE)

# %% [CELDA 5] Descubrimiento automático de la estructura de datos
PALABRAS_PRENDA = ['cloth', 'garment', 'prenda', 'product', 'producto', 'item', 'ropa', 'apparel']


def descubrir_datos(raiz, csv_nombre=None):
    """Devuelve {'pares': [(persona, prenda)], 'imagenes': [ruta], 'info': str}."""
    raiz = Path(raiz)
    imagenes = listar_imagenes(raiz)
    indice = {}
    for p in imagenes:
        indice.setdefault(p.name.lower(), p)
        indice.setdefault(p.stem.lower(), p)

    def resolver(valor):
        if not isinstance(valor, str) or not valor.strip():
            return None
        v = valor.strip()
        for cand in (
            Path(v),
            raiz / v,
            raiz / f'{v}.jpg',
            raiz / f'{v}.png',
            raiz / 'selected_images' / v,
            raiz / 'selected_images' / f'{v}.jpg',
            raiz / 'selected_images' / f'{v}.png',
            raiz / 'selected_images' / Path(v).name,
            raiz / 'images' / v,
            raiz / 'images' / f'{v}.jpg',
            raiz / 'images' / f'{v}.png',
            raiz / 'images' / Path(v).name,
        ):
            if cand.is_file():
                return cand
        nom = Path(v).name.lower()
        if nom in indice:
            return indice[nom]
        stem = Path(v).stem.lower()
        if stem in indice:
            return indice[stem]
        if f'{nom}.jpg' in indice:
            return indice[f'{nom}.jpg']
        if f'{nom}.png' in indice:
            return indice[f'{nom}.png']
        return None

    # 1) Estructura estilo VITON-HD: carpetas image/ y cloth/ con el mismo nombre de archivo.
    carpetas = {}
    for root, dirs, _ in os.walk(raiz):
        for d in dirs:
            carpetas[d.lower()] = Path(root) / d
    if 'image' in carpetas and 'cloth' in carpetas:
        pares = []
        for p in listar_imagenes(carpetas['image']):
            c = carpetas['cloth'] / p.name
            if c.exists():
                pares.append((p, c))
        if pares:
            return dict(pares=pares, imagenes=[], info=f'Estructura VITON: {len(pares)} pares image/cloth')

    # 2) CSV / Feather de metadatos (p. ej. labels_front.csv, labels_front.feather, dataset_metadata.csv)
    candidatos_meta = []
    if csv_nombre:
        candidatos_meta.append(raiz / csv_nombre)
    candidatos_meta += [raiz / 'labels_front.csv', raiz / 'labels_front.feather', raiz / 'dataset_metadata.csv']
    for root, _, files in os.walk(raiz):
        for f in files:
            if f.lower().endswith(('.csv', '.feather')):
                candidatos_meta.append(Path(root) / f)

    meta_file = next((c for c in candidatos_meta if c.is_file()), None)
    if meta_file is not None:
        try:
            import pandas as pd
            if meta_file.suffix.lower() == '.feather':
                df = pd.read_feather(meta_file)
            else:
                try:
                    df = pd.read_csv(meta_file)
                except Exception:
                    df = pd.read_csv(meta_file, sep=None, engine='python')
            print(f'Metadatos {meta_file.name}: {len(df)} filas, columnas = {list(df.columns)}')
            print(df.head(3).to_string())
            cols_img = []
            for c in df.columns:
                muestra = df[c].dropna().astype(str).head(50).tolist()
                if muestra and sum(resolver(v) is not None for v in muestra) / len(muestra) >= 0.3:
                    cols_img.append(c)
            print('Columnas con rutas de imagen detectadas:', cols_img)
            if len(cols_img) >= 2:
                col_prenda = next((c for c in cols_img if any(k in c.lower() for k in PALABRAS_PRENDA)), cols_img[1])
                col_persona = next(c for c in cols_img if c != col_prenda)
                pares = []
                for a, b in zip(df[col_persona].astype(str), df[col_prenda].astype(str)):
                    ra, rb = resolver(a), resolver(b)
                    if ra and rb and ra != rb:
                        pares.append((ra, rb))
                if pares:
                    return dict(pares=pares, imagenes=[], info=f'CSV pareado: {len(pares)} pares (persona="{col_persona}", prenda="{col_prenda}")')
            if len(cols_img) == 1 or (len(cols_img) >= 2 and not pares):
                # Si falló la creación de pares (ej. misma imagen), recolectamos las de la columna prenda o la primera válida
                col_unica = cols_img[1] if len(cols_img) >= 2 else cols_img[0]
                rutas = sorted({r for r in (resolver(v) for v in df[col_unica].astype(str)) if r})
                if rutas:
                    return dict(pares=[], imagenes=rutas, info=f'CSV con columna de imágenes: {len(rutas)} imágenes detectadas ("{col_unica}")')
        except Exception as e_csv:
            print(f'Aviso al procesar metadatos {meta_file}: {e_csv}')

    # 3) Todas las imágenes de la carpeta y subcarpetas
    return dict(pares=[], imagenes=imagenes, info=f'{len(imagenes)} imágenes encontradas en {raiz.name}')


def limitar(lista, maximo, seed=CFG['SEED']):
    if maximo is None or len(lista) <= maximo:
        return list(lista)
    return random.Random(seed).sample(list(lista), maximo)


DESC1 = descubrir_datos(DIR_ETAPA1, CFG['ETAPA1_CSV'])
DESC2 = descubrir_datos(DIR_ETAPA2)
DESC1['pares'] = limitar(DESC1['pares'], CFG['MAX_IMG_ETAPA1'])
DESC1['imagenes'] = limitar(DESC1['imagenes'], CFG['MAX_IMG_ETAPA1'])
DESC2['pares'] = limitar(DESC2['pares'], CFG['MAX_IMG_ETAPA2'])
DESC2['imagenes'] = limitar(DESC2['imagenes'], CFG['MAX_IMG_ETAPA2'])
print('Etapa 1 →', DESC1['info'])
print('Etapa 2 →', DESC2['info'])

# %% [CELDA 6] Preprocesamiento + caché (letterbox 256x192 + parsing), tolerante a imágenes corruptas
INDICE_PATH = CACHE_DRIVE / 'indice.json'
INDICE = json.loads(INDICE_PATH.read_text(encoding='utf-8')) if INDICE_PATH.exists() else {}


def clasificar(parse):
    """'persona' solo si se ve un ROSTRO o pelo además de anatomía; si no, es foto de producto.

    v1 usaba solo "anatomía visible": las mangas de una chaqueta o cárdigan fotografiado sin
    modelo se parsean como brazos, y las fotos del catálogo terminaban tratadas como personas
    (la Etapa 2 entrenó con prendas en lugar de cuerpos).
    """
    anat = np.isin(parse, ANATOMIA).mean()
    ropa = np.isin(parse, ROPA).mean()
    rostro = np.isin(parse, [L['face'], L['hair']]).mean()
    if rostro > 0.004 and anat > 0.01:
        return 'persona', None
    if ropa > 0.03:
        conteo = {k: int((parse == v).sum()) for k, v in
                  [('superior', L['upper-clothes']), ('vestido', L['dress']), ('inferior', L['pants']), ('falda', L['skirt'])]}
        return 'prenda', max(conteo, key=conteo.get)
    # Prenda que el parser no reconoce (p. ej. fondo no blanco): se decide luego por umbral.
    return 'prenda', 'desconocido'


def preprocesar(rutas, lote=16):
    rutas = [Path(r) for r in dict.fromkeys(rutas)]
    pendientes = [r for r in rutas if clave_de(r) not in INDICE]
    print(f'Preprocesando {len(pendientes)} imágenes nuevas ({len(rutas) - len(pendientes)} ya en caché)…')
    t0 = time.time()
    for i in range(0, len(pendientes), lote):
        bloque, imgs = [], []
        for r in pendientes[i:i + lote]:
            try:
                imgs.append(letterbox(abrir_imagen(r)))
                bloque.append(r)
            except Exception as e:                       # imagen corrupta → se registra y se omite
                INDICE[clave_de(r)] = dict(ruta=str(r), ok=False, error=str(e)[:120])
        if bloque:
            try:
                mapas = PARSER.parsear(imgs, bloque)
            except Exception as e:
                print(f'⚠️  Falló el parsing de un lote: {e}')
                mapas = [None] * len(bloque)
            for r, im, mp in zip(bloque, imgs, mapas):
                k = clave_de(r)
                if mp is None:
                    INDICE[k] = dict(ruta=str(r), ok=False, error='parsing')
                    continue
                im.save(CACHE_DRIVE / f'{k}.jpg', quality=95)
                Image.fromarray(mp).save(CACHE_DRIVE / f'{k}_parse.png')
                tipo, sub = clasificar(mp)
                INDICE[k] = dict(ruta=str(r), ok=True, tipo=tipo, subtipo=sub)
        if (i // lote) % 10 == 0 or i + lote >= len(pendientes):
            INDICE_PATH.write_text(json.dumps(INDICE, ensure_ascii=False), encoding='utf-8')
            hechos = min(i + lote, len(pendientes))
            print(f'  {hechos}/{len(pendientes)}  ({time.time() - t0:.0f}s)')
    INDICE_PATH.write_text(json.dumps(INDICE, ensure_ascii=False), encoding='utf-8')


todas = [p for par in DESC1['pares'] + DESC2['pares'] for p in par] + DESC1['imagenes'] + DESC2['imagenes']
preprocesar(todas)

if CACHE_LOCAL != CACHE_DRIVE:
    print('Copiando caché a disco local de Colab para acelerar el entrenamiento…')
    try:
        shutil.copytree(CACHE_DRIVE, CACHE_LOCAL, dirs_exist_ok=True)
    except Exception as e_cp:
        print(f'Aviso al copiar caché a disco local: {e_cp}')

# Reclasifica la caché existente con la regla actual (las entradas de v1 pueden estar mal).
_cambios = 0
for _k, _v in INDICE.items():
    if not _v.get('ok'):
        continue
    _ruta_parse = CACHE_DRIVE / f'{_k}_parse.png'
    if not _ruta_parse.exists():
        continue
    _tipo, _sub = clasificar(np.array(Image.open(_ruta_parse), dtype=np.uint8))
    if (_tipo, _sub) != (_v.get('tipo'), _v.get('subtipo')):
        _v['tipo'], _v['subtipo'] = _tipo, _sub
        _cambios += 1
if _cambios:
    INDICE_PATH.write_text(json.dumps(INDICE, ensure_ascii=False), encoding='utf-8')
    print(f'Reclasificadas {_cambios} imágenes de la caché (persona ↔ prenda).')

fallidas = [v for v in INDICE.values() if not v.get('ok')]
print(f'Imágenes omitidas por corruptas o ilegibles: {len(fallidas)}')
for v in fallidas[:5]:
    print('   ', v['ruta'], '→', v.get('error'))


def armar_items(desc):
    """Convierte la descripción de una carpeta en items (clave_persona, clave_prenda) + modo."""
    ok = lambda r: INDICE.get(clave_de(r), {}).get('ok')
    info = lambda r: INDICE[clave_de(r)]
    pares = [(clave_de(a), clave_de(b)) for a, b in desc['pares']
             if ok(a) and ok(b) and info(a)['tipo'] == 'persona']
    if pares:
        return 'pareado', pares
    personas = [clave_de(r) for r in desc['imagenes'] if ok(r) and info(r)['tipo'] == 'persona']
    prendas = [clave_de(r) for r in desc['imagenes'] if ok(r) and info(r)['tipo'] == 'prenda']
    if personas and len(personas) >= len(prendas):
        return 'auto', [(k, None) for k in personas]
    if prendas:
        return 'prenda', [(None, k) for k in prendas]
    return None, []


MODO1, ITEMS1 = armar_items(DESC1)
MODO2, ITEMS2 = armar_items(DESC2)
# Reúne TODAS las personas detectadas en cualquier dataset (Etapa 1 + Etapa 2 / cuerpos)
POOL_PERSONAS = sorted({k for k, v in INDICE.items() if v.get('ok') and v.get('tipo') == 'persona'})
def _conteo(desc):
    tipos = [INDICE.get(clave_de(r), {}).get('tipo') for r in desc['imagenes']]
    return tipos.count('persona'), tipos.count('prenda')


print(f'Etapa 1: modo={MODO1}, muestras={len(ITEMS1)}  (personas/prendas detectadas: {_conteo(DESC1)})')
print(f'Etapa 2: modo={MODO2}, muestras={len(ITEMS2)}  (personas/prendas detectadas: {_conteo(DESC2)})')
if MODO2 is not None and len(ITEMS2) < 20:
    print(f'⚠️  La Etapa 2 solo tiene {len(ITEMS2)} muestras: el fine-tuning será poco útil. '
          'Agrega más fotos del catálogo a entrenamiento_ia_ropa/.')
print(f'Personas disponibles en el pool para combinar con prendas del catálogo: {len(POOL_PERSONAS)}')
if MODO1 is None:
    raise RuntimeError('La Etapa 1 no tiene fotos de personas utilizables. Revisa la carpeta archive/.')
if not POOL_PERSONAS:
    raise RuntimeError('No hay ninguna foto de persona en los datos: no se puede entrenar un probador virtual.')

# %% [CELDA 7] Representación agnóstica + REGLA DE ORO (cuello/brazos) + Dataset robusto
N_PARSE = 6   # canales: [preservar, area_generar, brazos, cara_cuello, silueta, fondo_visible]  (preservar SIEMPRE en el 0)


def dilatar(mascara, k):
    im = Image.fromarray(mascara.astype(np.uint8) * 255)
    return np.array(im.filter(ImageFilter.MaxFilter(k))) > 127


def derivar_mascaras(parse, preservar_brazos=CFG['PRESERVAR_BRAZOS']):
    """Máscaras de la persona a partir del parsing.

    - ropa_sup: ropa superior/vestido que llevaba puesta (se BORRA en la agnóstica).
    - cuello: franja bajo la cara que no es ropa. Muchos parsers etiquetan el cuello como fondo, por
      eso se define por geometría: si es piel se conserva, y si es fondo conservarlo también es correcto.
    - preservar: cara, pelo, cuello, brazos, parte inferior y todo lo que está fuera del área de la prenda.
      El resultado final copia estos píxeles de la foto ORIGINAL ⇒ la parte trasera de la prenda
      (etiqueta, nuca de la camisa) jamás puede quedar dibujada sobre el cuello.
    """
    alto, ancho = parse.shape
    ropa_sup = np.isin(parse, [L['upper-clothes'], L['dress']])
    cara = np.isin(parse, [L['hat'], L['hair'], L['sunglasses'], L['face']])
    brazos = np.isin(parse, [L['left-arm'], L['right-arm']])
    inferior = np.isin(parse, [L['skirt'], L['pants'], L['belt'], L['left-shoe'], L['right-shoe'],
                               L['left-leg'], L['right-leg'], L['bag']])
    cuello = np.zeros_like(ropa_sup)
    ys, xs = np.nonzero(parse == L['face'])
    if ys.size > 20:
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        h_cara, w_cara = y1 - y0 + 1, x1 - x0 + 1
        cuello[y1:min(alto, y1 + int(0.5 * h_cara)),
               max(0, x0 - int(0.15 * w_cara)):min(ancho, x1 + int(0.15 * w_cara) + 1)] = True
        cuello &= ~ropa_sup & ~cara
    area = dilatar(ropa_sup, 9)
    if not preservar_brazos:
        area |= brazos
    preservar = ~area | cara | cuello | inferior
    if preservar_brazos:
        preservar |= brazos
    area_generar = ~preservar
    # v2 — sin halo: en el anillo dilatado solo se borra (gris) la ropa vieja y un borde de 2 px;
    # el FONDO que queda más allá sigue visible en la agnóstica y, si la prenda nueva no lo cubre,
    # el resultado final copia el píxel original (antes se regeneraba y quedaba un contorno blanco).
    fondo = parse == L['background']
    gris = area_generar & ~(fondo & ~dilatar(ropa_sup, 5))
    fondo_visible = area_generar & ~gris
    silueta = np.array(Image.fromarray((parse > 0).astype(np.uint8) * 255)
                       .resize((ancho // 8, alto // 8), Image.BILINEAR)
                       .resize((ancho, alto), Image.BILINEAR)) / 255.0
    return dict(preservar=preservar, area=area_generar, brazos=brazos, cara_cuello=cara | cuello,
                silueta=silueta, ropa=ropa_sup & area_generar, cuello=cuello,
                gris=gris, fondo_visible=fondo_visible)


def mascara_de_prenda(img, parse):
    """Máscara de una foto de producto: por parsing y, si falla, por umbral sobre fondo claro."""
    m = np.isin(parse, ROPA)
    if m.mean() < 0.03:
        arr = np.asarray(img).astype(np.int16)
        m = (255 - arr.min(axis=2)) > 25
        m = ~dilatar(~dilatar(m, 5), 5)        # cierre morfológico para rellenar huecos
    return m


def mapa_a_tensores(m):
    t = lambda a: torch.from_numpy(np.asarray(a, dtype=np.float32))[None]
    parse_t = torch.cat([t(m['preservar']), t(m['area']), t(m['brazos']), t(m['cara_cuello']), t(m['silueta']),
                         t(m['fondo_visible'])], 0)
    visible = 1 - t(m['gris'])          # la agnóstica = persona × visible (gris = 0)
    return parse_t, visible, t(m['ropa']), t(m['cuello'])


def prenda_desde_persona(persona_t, ropa_t, aleatorio):
    """Modo 'auto': recorta la prenda que lleva la persona, la centra como foto de producto y, en
    entrenamiento, la deforma al azar para que el GMM aprenda a re-colocarla."""
    ys, xs = torch.nonzero(ropa_t[0] > 0.5, as_tuple=True)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    blanco = torch.ones_like(persona_t)
    recorte = (persona_t * ropa_t + blanco * (1 - ropa_t))[:, y0:y1, x0:x1]
    mrec = ropa_t[:, y0:y1, x0:x1]
    esc = min(0.85 * H / recorte.shape[1], 0.85 * W / recorte.shape[2])
    nh, nw = max(1, int(recorte.shape[1] * esc)), max(1, int(recorte.shape[2] * esc))
    recorte = F.interpolate(recorte[None], size=(nh, nw), mode='bilinear', align_corners=False)[0]
    mrec = (F.interpolate(mrec[None], size=(nh, nw), mode='bilinear', align_corners=False)[0] > 0.5).float()
    prenda = torch.ones(3, H, W)
    mprenda = torch.zeros(1, H, W)
    oy, ox = (H - nh) // 2, (W - nw) // 2
    prenda[:, oy:oy + nh, ox:ox + nw] = recorte
    mprenda[:, oy:oy + nh, ox:ox + nw] = mrec
    if aleatorio:
        ang = random.uniform(-8, 8)
        tr = [random.randint(-int(0.06 * W), int(0.06 * W)), random.randint(-int(0.06 * H), int(0.06 * H))]
        es = random.uniform(0.9, 1.1)
        prenda = TF.affine(prenda, angle=ang, translate=tr, scale=es, shear=[0.0], fill=[1.0, 1.0, 1.0])
        mprenda = TF.affine(mprenda, angle=ang, translate=tr, scale=es, shear=[0.0], fill=[0.0])
    prenda = prenda * mprenda + (1 - mprenda)      # fondo blanco fuera de la prenda
    return prenda, mprenda


INTERCAMBIO_LR = np.arange(256, dtype=np.uint8)
for a, b in [(L['left-arm'], L['right-arm']), (L['left-leg'], L['right-leg']), (L['left-shoe'], L['right-shoe'])]:
    INTERCAMBIO_LR[a], INTERCAMBIO_LR[b] = b, a


class DatasetVTON(Dataset):
    """Muestras (persona, prenda). Si una imagen falla, devuelve None y el collate la descarta:
    el entrenamiento NUNCA se detiene por una imagen corrupta."""

    def __init__(self, items, modo, dir_cache, entrenamiento, pool_personas=None):
        self.items, self.modo, self.dir = items, modo, Path(dir_cache)
        self.entrenamiento, self.pool = entrenamiento, pool_personas or []
        self.errores = 0

    def __len__(self):
        return len(self.items)

    def _cargar(self, clave):
        img = Image.open(self.dir / f'{clave}.jpg').convert('RGB')
        parse = np.array(Image.open(self.dir / f'{clave}_parse.png'), dtype=np.uint8)
        return img, parse

    def __getitem__(self, i):
        try:
            return self._construir(i)
        except Exception as e:
            self.errores += 1
            if self.errores <= 10:
                print(f'⚠️  Muestra {i} omitida ({type(e).__name__}: {str(e)[:80]})')
            return None

    def _construir(self, i):
        k_persona, k_prenda = self.items[i]
        if self.modo == 'prenda':
            rng = random if self.entrenamiento else random.Random(i)   # validación reproducible
            k_persona = rng.choice(self.pool)
        img, parse = self._cargar(k_persona)
        if self.entrenamiento and random.random() < 0.5:
            img = ImageOps.mirror(img)
            parse = INTERCAMBIO_LR[np.ascontiguousarray(parse[:, ::-1])]
        m = derivar_mascaras(parse)
        if m['ropa'].mean() < 0.02:
            raise ValueError('la persona no tiene prenda superior visible')
        persona = pil_a_tensor(img)
        parse_t, visible, ropa, cuello = mapa_a_tensores(m)
        if self.modo == 'auto':
            prenda, mprenda = prenda_desde_persona(persona, ropa, self.entrenamiento)
        else:
            img_c, parse_c = self._cargar(k_prenda)
            if self.entrenamiento and random.random() < 0.5:
                img_c = ImageOps.mirror(img_c)
                parse_c = np.ascontiguousarray(parse_c[:, ::-1])
            mprenda = torch.from_numpy(mascara_de_prenda(img_c, parse_c).astype(np.float32))[None]
            if mprenda.mean() < 0.02:
                raise ValueError('prenda sin máscara utilizable')
            prenda = pil_a_tensor(img_c) * mprenda + (1 - mprenda)
        return dict(
            persona=persona,
            agnostica=persona * visible,                    # ropa original borrada (gris = 0), fondo visible
            parse=parse_t,
            prenda=prenda,
            mascara_prenda=mprenda,
            mascara_objetivo=ropa,
            cuello=cuello,
            tiene_gt=torch.tensor(self.modo != 'prenda'),
        )


def collate_seguro(lote):
    lote = [m for m in lote if m is not None]
    return default_collate(lote) if lote else None


def dividir(items, frac_val, seed=CFG['SEED']):
    items = list(items)
    if len(items) <= 1:
        return items, items
    random.Random(seed).shuffle(items)
    n_val = max(1, int(len(items) * frac_val))
    if n_val == len(items):
        n_val = len(items) - 1
    return items[n_val:], items[:n_val]


def crear_loaders(items, modo):
    tr, va = dividir(items, CFG['VAL_SPLIT'])
    ds_tr = DatasetVTON(tr, modo, CACHE_LOCAL, True, POOL_PERSONAS)
    ds_va = DatasetVTON(va, modo, CACHE_LOCAL, False, POOL_PERSONAS)
    kw = dict(batch_size=CFG['BATCH'], num_workers=CFG['WORKERS'], collate_fn=collate_seguro,
              pin_memory=DEVICE.type == 'cuda', persistent_workers=CFG['WORKERS'] > 0)
    dl_tr = DataLoader(ds_tr, shuffle=True, drop_last=len(ds_tr) > CFG['BATCH'], **kw)
    dl_va = DataLoader(ds_va, shuffle=False, **kw)
    print(f'  train={len(ds_tr)}  val={len(ds_va)}  (modo {modo})')
    return dl_tr, dl_va


# Vista previa de una muestra para comprobar las máscaras antes de entrenar.
_prev = DatasetVTON(ITEMS1[:8], MODO1, CACHE_LOCAL, False, POOL_PERSONAS)
_m = next((_prev[i] for i in range(len(_prev)) if _prev[i] is not None), None)
if _m is not None:
    fig, ax = plt.subplots(1, 5, figsize=(14, 4))
    paneles = [(tensor_a_numpy_img(_m['persona']), 'Persona'), (tensor_a_numpy_img(_m['agnostica']), 'Agnóstica'),
               (_m['parse'][0].numpy(), 'Preservar (cara/cuello/brazos)'), (_m['cuello'][0].numpy(), 'Cuello'),
               (tensor_a_numpy_img(_m['prenda']), 'Prenda')]
    for a, (img, t) in zip(ax, paneles):
        a.imshow(img, cmap='gray' if img.ndim == 2 else None)
        a.set_title(t, fontsize=9)
        a.axis('off')
    plt.tight_layout()
    fig.savefig(SALIDA / 'vista_previa_mascaras.png', dpi=90)
    if EN_NOTEBOOK:
        plt.show()
    plt.close(fig)

# %% [CELDA 8] Arquitectura: backbone preentrenado + GMM (deformación) + TOM (síntesis y fusión)
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


class EncoderResNet(nn.Module):
    """ResNet34 preentrenado en ImageNet.

    - 'stem': adaptador de entrada de in_ch canales (entrenable en Etapa 1). Sus 3 primeros canales
      se inicializan con los pesos preentrenados de conv1.
    - bn1 + layer1..layer4: extractor espacial y de características → se CONGELA (transfer learning).
    """

    def __init__(self, in_ch, preentrenado=True):
        super().__init__()
        pesos = torchvision.models.ResNet34_Weights.IMAGENET1K_V1 if preentrenado else None
        r = resnet34(weights=pesos)
        self.stem = nn.Conv2d(in_ch, 64, 7, 2, 3, bias=False)
        with torch.no_grad():
            self.stem.weight.zero_()
            self.stem.weight[:, :3] = r.conv1.weight
            if in_ch > 3:
                self.stem.weight[:, 3:] = r.conv1.weight.mean(1, keepdim=True) * 0.1
        self.bn1, self.relu, self.maxpool = r.bn1, r.relu, r.maxpool
        self.layer1, self.layer2, self.layer3, self.layer4 = r.layer1, r.layer2, r.layer3, r.layer4
        self.register_buffer('mean', IMAGENET_MEAN.clone(), persistent=False)
        self.register_buffer('std', IMAGENET_STD.clone(), persistent=False)

    def backbone(self):
        return [self.bn1, self.layer1, self.layer2, self.layer3, self.layer4]

    def forward(self, x):
        rgb = ((x[:, :3] + 1) / 2 - self.mean) / self.std       # [-1,1] → normalización ImageNet
        x = torch.cat([rgb, x[:, 3:]], 1)
        f0 = self.relu(self.bn1(self.stem(x)))       # H/2 , 64
        f1 = self.layer1(self.maxpool(f0))           # H/4 , 64
        f2 = self.layer2(f1)                         # H/8 , 128
        f3 = self.layer3(f2)                         # H/16, 256
        f4 = self.layer4(f3)                         # H/32, 512
        return [f0, f1, f2, f3, f4]


def bloque_conv(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, 1, 1), nn.BatchNorm2d(o), nn.LeakyReLU(0.1, inplace=True))


def rejilla_base(h, w):
    """Rejilla identidad (x, y) normalizada para grid_sample con align_corners=False."""
    ys = (torch.arange(h, dtype=torch.float32) + 0.5) / h * 2 - 1
    xs = (torch.arange(w, dtype=torch.float32) + 0.5) / w * 2 - 1
    gy, gx = torch.meshgrid(ys, xs, indexing='ij')
    return torch.stack([gx, gy], -1)[None]          # [1, h, w, 2]


def deformar(x, flujo, base, relleno):
    grid = base.expand(x.shape[0], -1, -1, -1) + flujo.permute(0, 2, 3, 1)
    return F.grid_sample(x, grid.to(x.dtype), mode='bilinear', padding_mode=relleno, align_corners=False)


class GMMFlujo(nn.Module):
    """Geometric Matching Module por flujo denso, de lo grueso (H/32) a lo fino (H/4).

    Compara las características de la persona (agnóstica + parsing) con las de la prenda y predice
    cuánto mover cada píxel de la prenda para que calce en el cuerpo."""

    def __init__(self, preentrenado=True):
        super().__init__()
        self.enc_persona = EncoderResNet(3 + N_PARSE, preentrenado)
        self.enc_prenda = EncoderResNet(3 + 1, preentrenado)
        canales = {1: 64, 2: 128, 3: 256, 4: 512}
        self.niveles = [4, 3, 2, 1]
        self.tamanos = {n: (H // 2 ** (n + 1), W // 2 ** (n + 1)) for n in self.niveles}
        self.estimadores = nn.ModuleList()
        for j, n in enumerate(self.niveles):
            c = canales[n]
            entrada = 2 * c + (0 if j == 0 else 2)
            est = nn.Sequential(bloque_conv(entrada, 128), bloque_conv(128, 64), nn.Conv2d(64, 2, 3, 1, 1))
            nn.init.zeros_(est[-1].weight)
            nn.init.zeros_(est[-1].bias)              # al inicio: flujo cero = identidad
            self.estimadores.append(est)
        for n in self.niveles:
            self.register_buffer(f'base_{n}', rejilla_base(*self.tamanos[n]), persistent=False)
        self.register_buffer('base_full', rejilla_base(H, W), persistent=False)

    def forward(self, persona_in, prenda_in, prenda, mascara_prenda):
        fp, fc = self.enc_persona(persona_in), self.enc_prenda(prenda_in)
        flujo = None
        for j, n in enumerate(self.niveles):
            p, c = fp[n], fc[n]
            if flujo is None:
                entrada = torch.cat([p, c], 1)
            else:
                flujo = F.interpolate(flujo, size=self.tamanos[n], mode='bilinear', align_corners=False)
                c = deformar(c, flujo, getattr(self, f'base_{n}'), 'border')
                entrada = torch.cat([p, c, flujo], 1)
            delta = self.estimadores[j](entrada)
            flujo = delta if flujo is None else flujo + delta
        flujo = F.interpolate(flujo, size=(H, W), mode='bilinear', align_corners=False)
        prenda_def = deformar(prenda, flujo, self.base_full, 'border')
        mascara_def = deformar(mascara_prenda, flujo, self.base_full, 'zeros')
        return prenda_def, mascara_def, flujo


class BloqueSubida(nn.Module):
    def __init__(self, i, o, tam):
        super().__init__()
        self.tam = tam
        self.conv = nn.Sequential(bloque_conv(i, o), bloque_conv(o, o))

    def forward(self, x, salto):
        x = F.interpolate(x, size=self.tam, mode='bilinear', align_corners=False)
        return self.conv(torch.cat([x, salto], 1))


class GeneradorTOM(nn.Module):
    """Try-On Module: U-Net con encoder ResNet34 preentrenado. Genera la imagen 'renderizada' y una
    máscara de composición que decide cuánto usar de la prenda deformada (conserva la textura real)."""

    def __init__(self, preentrenado=True):
        super().__init__()
        self.encoder = EncoderResNet(3 + N_PARSE + 3 + 1, preentrenado)
        self.up4 = BloqueSubida(512 + 256, 256, (H // 16, W // 16))
        self.up3 = BloqueSubida(256 + 128, 128, (H // 8, W // 8))
        self.up2 = BloqueSubida(128 + 64, 64, (H // 4, W // 4))
        # ---- capas finales de fusión (se re-entrenan en la Etapa 2) ----
        self.up1 = BloqueSubida(64 + 64, 64, (H // 2, W // 2))
        self.fusion = nn.Sequential(bloque_conv(64 + 3 + 1 + 3, 32), nn.Conv2d(32, 4, 3, 1, 1))

    def capas_fusion(self):
        return [self.up1, self.fusion]

    def forward(self, agnostica, parse, prenda_def, mascara_def):
        x = torch.cat([agnostica, parse, prenda_def, mascara_def], 1)
        f0, f1, f2, f3, f4 = self.encoder(x)
        d = self.up4(f4, f3)
        d = self.up3(d, f2)
        d = self.up2(d, f1)
        d = self.up1(d, f0)
        d = F.interpolate(d, size=(H, W), mode='bilinear', align_corners=False)
        o = self.fusion(torch.cat([d, prenda_def, mascara_def, agnostica], 1))
        return torch.tanh(o[:, :3]), torch.sigmoid(o[:, 3:4])


class ModeloVTON(nn.Module):
    def __init__(self, preentrenado=True):
        super().__init__()
        self.gmm = GMMFlujo(preentrenado)
        self.tom = GeneradorTOM(preentrenado)
        self.congelados = []

    def forward(self, agnostica, parse, prenda, mascara_prenda):
        prenda_def, mascara_def, flujo = self.gmm(torch.cat([agnostica, parse], 1),
                                                  torch.cat([prenda, mascara_prenda], 1),
                                                  prenda, mascara_prenda)
        preservar = parse[:, 0:1]
        # REGLA DE ORO (1): la prenda deformada no puede ocupar cuello/brazos/cara.
        mascara_ef = mascara_def * (1 - preservar)
        render, comp = self.tom(agnostica, parse, prenda_def, mascara_ef)
        # Borde duro: en el contorno suave de la máscara la prenda (sobre fondo blanco) se mezclaba
        # con blanco y dejaba un halo; ahora la composición solo usa la prenda donde la máscara es firme.
        comp = comp * torch.clamp((mascara_ef - 0.3) / 0.4, 0, 1)
        tryon = comp * prenda_def + (1 - comp) * render
        # REGLA DE ORO (2): la anatomía ORIGINAL se superpone sobre la prenda generada, y el fondo
        # original que la prenda nueva no cubre también se conserva (v2).
        fondo_visible = parse[:, 5:6]
        conservar = torch.clamp(preservar + fondo_visible * (1 - mascara_def), 0, 1)
        final = conservar * agnostica + (1 - conservar) * tryon
        return dict(final=final, tryon=tryon, render=render, comp=comp, prenda_def=prenda_def,
                    mascara_def=mascara_def, mascara_ef=mascara_ef, flujo=flujo)


def poner_modo(modelo, entrenamiento):
    """train()/eval() manteniendo en eval los módulos congelados (sus BatchNorm no cambian)."""
    modelo.train(entrenamiento)
    for m in modelo.congelados:
        m.eval()

# %% [CELDA 9] Transfer Learning: qué se congela y qué se entrena en cada etapa


def configurar_transfer_learning(modelo, etapa):
    """Etapa 1: backbone ImageNet congelado; se entrenan adaptadores, GMM, decoder y fusión.
    Etapa 2: además se congelan adaptadores y decoder; SOLO se entrena el GMM (estimadores de
    flujo) y las capas finales de fusión → evita el olvido catastrófico con pocos datos."""
    for p in modelo.parameters():
        p.requires_grad = False
    encoders = [modelo.gmm.enc_persona, modelo.gmm.enc_prenda, modelo.tom.encoder]
    congelados = [m for e in encoders for m in e.backbone()]
    if etapa == 1:
        entrenables = [e.stem for e in encoders] + [modelo.gmm.estimadores,
                                                    modelo.tom.up4, modelo.tom.up3, modelo.tom.up2,
                                                    *modelo.tom.capas_fusion()]
    else:
        congelados += [e.stem for e in encoders] + [modelo.tom.up4, modelo.tom.up3, modelo.tom.up2]
        entrenables = [modelo.gmm.estimadores, *modelo.tom.capas_fusion()]
    for m in entrenables:
        for p in m.parameters():
            p.requires_grad = True
    modelo.congelados = congelados
    n_tot = sum(p.numel() for p in modelo.parameters())
    n_ent = sum(p.numel() for p in modelo.parameters() if p.requires_grad)
    print(f'Etapa {etapa}: parámetros entrenables {n_ent / 1e6:.2f} M de {n_tot / 1e6:.2f} M '
          f'({100 * n_ent / n_tot:.1f} %) — backbone CNN congelado (requires_grad=False)')
    return [p for p in modelo.parameters() if p.requires_grad]

# %% [CELDA 10] Pérdidas y métricas: L1, Perceptual VGG, IoU, SSIM, invasión de cuello


class PerdidaVGG(nn.Module):
    """Perceptual loss con VGG19 de ImageNet: mide el realismo de texturas de tela."""

    def __init__(self, preentrenado=True):
        super().__init__()
        pesos = torchvision.models.VGG19_Weights.IMAGENET1K_V1 if preentrenado else None
        self.vgg = vgg19(weights=pesos).features[:27].eval()
        for p in self.vgg.parameters():
            p.requires_grad = False
        self.capas = {3: 1 / 32, 8: 1 / 16, 17: 1 / 8, 26: 1 / 4}   # relu1_2, relu2_2, relu3_4, relu4_4
        self.register_buffer('mean', IMAGENET_MEAN.clone(), persistent=False)
        self.register_buffer('std', IMAGENET_STD.clone(), persistent=False)

    def forward(self, x, y):
        x = ((x + 1) / 2 - self.mean) / self.std
        y = ((y + 1) / 2 - self.mean) / self.std
        total = 0.0
        for i, capa in enumerate(self.vgg):
            x, y = capa(x), capa(y)
            if i in self.capas:
                total = total + self.capas[i] * F.l1_loss(x, y.detach())
            if i >= 26:
                break
        return total


def _gauss(ventana=11, sigma=1.5):
    g = torch.exp(-((torch.arange(ventana) - ventana // 2) ** 2).float() / (2 * sigma ** 2))
    g = g / g.sum()
    return (g[:, None] @ g[None, :])[None, None]


_VENTANA_SSIM = _gauss()


def ssim(x, y):
    """SSIM medio (imágenes en [-1,1]). 1.0 = idénticas."""
    x, y = (x.float() + 1) / 2, (y.float() + 1) / 2
    c = x.shape[1]
    w = _VENTANA_SSIM.to(x.device).expand(c, 1, -1, -1)
    mu_x, mu_y = F.conv2d(x, w, padding=5, groups=c), F.conv2d(y, w, padding=5, groups=c)
    sxx = F.conv2d(x * x, w, padding=5, groups=c) - mu_x ** 2
    syy = F.conv2d(y * y, w, padding=5, groups=c) - mu_y ** 2
    sxy = F.conv2d(x * y, w, padding=5, groups=c) - mu_x * mu_y
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    mapa = ((2 * mu_x * mu_y + c1) * (2 * sxy + c2)) / ((mu_x ** 2 + mu_y ** 2 + c1) * (sxx + syy + c2))
    return mapa.mean()


def iou(pred, gt):
    p, g = pred > 0.5, gt > 0.5
    inter = (p & g).flatten(1).sum(1).float()
    union = (p | g).flatten(1).sum(1).float()
    valido = union > 0
    return (inter[valido] / union[valido]).mean() if valido.any() else torch.tensor(0.0, device=pred.device)


def calcular_perdidas(o, b, vgg, lam, tiene_gt):
    tm, cuello = b['mascara_objetivo'], b['cuello']
    wm, wc, flujo = o['mascara_def'], o['prenda_def'], o['flujo']
    tv = (flujo[:, :, 1:] - flujo[:, :, :-1]).abs().mean() + (flujo[:, :, :, 1:] - flujo[:, :, :, :-1]).abs().mean()
    invasion = (wm * cuello).sum() / (cuello.sum() + 1)          # prenda cayendo sobre el cuello
    dice = 1 - ((2 * (wm * tm).flatten(1).sum(1) + 1) / ((wm + tm).flatten(1).sum(1) + 1)).mean()
    if tiene_gt:
        persona = b['persona']
        l1 = (((wc - persona).abs() * tm).sum() / (tm.sum() * 3 + 1)) + F.l1_loss(o['final'], persona)
        vg = vgg(wc * tm, persona * tm) + vgg(o['final'], persona)
        comp_reg = F.l1_loss(o['comp'], o['mascara_ef'])
        s_loss = 1 - ssim(o['final'], persona)
        total = (lam['l1'] * l1 + lam['vgg'] * vg + lam['mascara'] * dice + lam['tv'] * tv
                 + lam['cuello'] * invasion + lam['comp'] * comp_reg + lam['ssim'] * s_loss)
    else:
        me = o['mascara_ef']
        l1 = ((o['tryon'] - wc).abs() * me).sum() / (me.sum() * 3 + 1)   # la textura del catálogo se conserva
        vg = vgg(o['tryon'] * me, wc * me)
        total = 2 * lam['mascara'] * dice + lam['tv'] * tv + lam['cuello'] * invasion + lam['l1'] * l1 + lam['vgg'] * vg
    return total, dict(l1=float(l1), vgg=float(vg))


@torch.no_grad()
def calcular_metricas(o, b, tiene_gt):
    m = dict(iou=float(iou(o['mascara_def'], b['mascara_objetivo'])),
             cuello=float(((o['mascara_def'] > 0.5).float() * b['cuello']).sum() / (b['cuello'].sum() + 1) * 100))
    if tiene_gt:
        m['ssim'] = float(ssim(o['final'], b['persona']))
    else:
        me = o['mascara_ef']
        m['ssim'] = float(ssim(o['tryon'] * me, o['prenda_def'] * me))
    return m

# %% [CELDA 11] Gráficas por época y grid visual de validación


def mostrar(fig, ruta):
    fig.savefig(ruta, dpi=90, bbox_inches='tight')
    if EN_NOTEBOOK and display is not None:
        display(fig)
    plt.close(fig)


def graficar_historial(hist, etapa, carpeta):
    ep = hist['epoca']
    fig, ax = plt.subplots(2, 3, figsize=(16, 8))
    pares = [('total', 'Training vs Validation Loss'), ('l1', 'L1 (exactitud por píxel)'),
             ('vgg', 'Perceptual (VGG)'), ('iou', 'IoU máscara de la prenda'), ('ssim', 'SSIM'),
             ('cuello', 'Invasión de cuello (%) · antes de la regla')]
    for a, (k, titulo) in zip(ax.flat, pares):
        a.plot(ep, hist[f'train_{k}'], 'o-', label='train')
        a.plot(ep, hist[f'val_{k}'], 's-', label='val')
        a.set_title(titulo)
        a.set_xlabel('época')
        a.grid(alpha=0.3)
        a.legend()
    ax2 = ax.flat[0].twinx()
    ax2.plot(ep, hist['lr'], 'k--', alpha=0.4)
    ax2.set_ylabel('learning rate', alpha=0.6)
    fig.suptitle(f'Etapa {etapa}', fontsize=14)
    fig.tight_layout()
    mostrar(fig, carpeta / f'curvas_etapa{etapa}.png')


@torch.no_grad()
def grid_visual(modelo, lote, etapa, epoca, carpeta, escritor=None):
    poner_modo(modelo, False)
    b = {k: v.to(DEVICE) for k, v in lote.items()}
    o = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
    n = min(4, b['persona'].shape[0])
    fig, ax = plt.subplots(n, 4, figsize=(10, 3.2 * n), squeeze=False)
    titulos = ['1. Foto original', '2. Máscara agnóstica', '3. Prenda del catálogo', '4. Resultado final']
    for i in range(n):
        for j, t in enumerate([b['persona'][i], b['agnostica'][i], b['prenda'][i], o['final'][i]]):
            ax[i, j].imshow(tensor_a_numpy_img(t))
            ax[i, j].axis('off')
            if i == 0:
                ax[i, j].set_title(titulos[j], fontsize=10)
    fig.suptitle(f'Etapa {etapa} · época {epoca}')
    fig.tight_layout()
    mostrar(fig, carpeta / f'visual_epoca_{epoca:03d}.png')
    if escritor is not None:
        filas = torch.cat([b['persona'][:n], b['agnostica'][:n], b['prenda'][:n], o['final'][:n]], 0)
        escritor.add_image('validacion', torchvision.utils.make_grid((filas.float().cpu() + 1) / 2, nrow=n), epoca)

# %% [CELDA 12] Bucle de entrenamiento: AdamW + ReduceLROnPlateau, AMP, checkpoints y reanudación


def autocast():
    return torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP)


def nuevo_scaler():
    try:
        return torch.amp.GradScaler('cuda', enabled=USA_AMP)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=USA_AMP)


def correr_epoca(modelo, loader, vgg, tiene_gt, optimizador=None, scaler=None, params=None):
    entrenando = optimizador is not None
    poner_modo(modelo, entrenando)
    acum, n = defaultdict(float), 0
    for lote in loader:
        if lote is None:                                   # todas las muestras del lote fallaron
            continue
        b = {k: v.to(DEVICE, non_blocking=True) for k, v in lote.items()}
        with torch.set_grad_enabled(entrenando):
            with autocast():
                o = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
                total, partes = calcular_perdidas(o, b, vgg, CFG['LAMBDAS'], tiene_gt)
            if entrenando:
                if not torch.isfinite(total):
                    print('⚠️  pérdida no finita, lote omitido')
                    optimizador.zero_grad(set_to_none=True)
                    continue
                optimizador.zero_grad(set_to_none=True)
                scaler.scale(total).backward()
                scaler.unscale_(optimizador)
                torch.nn.utils.clip_grad_norm_(params, 5.0)
                scaler.step(optimizador)
                scaler.update()
        met = calcular_metricas(o, b, tiene_gt)
        bs = b['persona'].shape[0]
        for k, v in {'total': float(total), **partes, **met}.items():
            acum[k] += v * bs
        n += bs
    return {k: v / max(n, 1) for k, v in acum.items()}


def guardar_ckpt(ruta, modelo, opt, sched, scaler, epoca, hist, mejor, sin_mejora, etapa):
    torch.save(dict(modelo=modelo.state_dict(), opt=opt.state_dict(), sched=sched.state_dict(),
                    scaler=scaler.state_dict(), epoca=epoca, hist=dict(hist), mejor=mejor,
                    sin_mejora=sin_mejora, etapa=etapa, cfg=CFG, n_parse=N_PARSE), ruta)


def entrenar_etapa(etapa, modelo, items, modo, epocas, lr):
    carpeta = SALIDA / f"etapa{etapa}_{CFG['VERSION_MODELO']}"
    dir_ckpt = carpeta / 'checkpoints'
    dir_ckpt.mkdir(parents=True, exist_ok=True)
    tiene_gt = modo != 'prenda'
    print(f'\n========== ETAPA {etapa} · modo {modo} · supervisión completa: {tiene_gt} ==========')
    dl_tr, dl_va = crear_loaders(items, modo)
    params = configurar_transfer_learning(modelo, etapa)
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=CFG['WEIGHT_DECAY'])
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=CFG['FACTOR_SCHEDULER'],
                                                       patience=CFG['PACIENCIA_SCHEDULER'])
    scaler = nuevo_scaler()
    vgg = PerdidaVGG(CFG['PESOS_PREENTRENADOS']).to(DEVICE)
    try:
        from torch.utils.tensorboard import SummaryWriter
        escritor = SummaryWriter(str(SALIDA / 'tensorboard' / f"etapa{etapa}_{CFG['VERSION_MODELO']}"))
    except Exception:
        escritor = None

    hist, inicio, mejor, sin_mejora = defaultdict(list), 1, float('inf'), 0
    ultimo = dir_ckpt / 'last.pth'
    ck = torch.load(ultimo, map_location=DEVICE, weights_only=False) if (CFG['REANUDAR'] and ultimo.exists()) else None
    if ck is not None and ck.get('n_parse') != N_PARSE:
        print(f'⚠️  {ultimo} es de otra versión del modelo ({ck.get("n_parse")} canales); se entrena desde cero.')
        ck = None
    if ck is not None:
        modelo.load_state_dict(ck['modelo'])
        opt.load_state_dict(ck['opt'])
        sched.load_state_dict(ck['sched'])
        scaler.load_state_dict(ck['scaler'])
        hist = defaultdict(list, ck['hist'])
        inicio, mejor, sin_mejora = ck['epoca'] + 1, ck['mejor'], ck['sin_mejora']
        print(f'↻ Reanudando la etapa {etapa} desde la época {inicio}')

    lote_visual = next((lt for lt in dl_va if lt is not None), None)
    for epoca in range(inicio, epocas + 1):
        t0 = time.time()
        tr = correr_epoca(modelo, dl_tr, vgg, tiene_gt, opt, scaler, params)
        with torch.no_grad():
            va = correr_epoca(modelo, dl_va, vgg, tiene_gt)
        sched.step(va.get('total', float('inf')))
        hist['epoca'].append(epoca)
        hist['lr'].append(opt.param_groups[0]['lr'])
        for k in ('total', 'l1', 'vgg', 'iou', 'ssim', 'cuello'):
            hist[f'train_{k}'].append(tr.get(k, float('nan')))
            hist[f'val_{k}'].append(va.get(k, float('nan')))
            if escritor is not None:
                escritor.add_scalars(k, {'train': tr.get(k, 0.0), 'val': va.get(k, 0.0)}, epoca)

        if va.get('total', float('inf')) < mejor:
            mejor, sin_mejora = va['total'], 0
            guardar_ckpt(dir_ckpt / 'best.pth', modelo, opt, sched, scaler, epoca, hist, mejor, sin_mejora, etapa)
        else:
            sin_mejora += 1
        if epoca % CFG['CHECKPOINT_CADA'] == 0:
            guardar_ckpt(dir_ckpt / f'epoca_{epoca:03d}.pth', modelo, opt, sched, scaler, epoca, hist, mejor, sin_mejora, etapa)
        guardar_ckpt(ultimo, modelo, opt, sched, scaler, epoca, hist, mejor, sin_mejora, etapa)

        if EN_NOTEBOOK and clear_output is not None:
            clear_output(wait=True)
        print(f'Etapa {etapa} | época {epoca}/{epocas} | {time.time() - t0:.0f}s | lr {opt.param_groups[0]["lr"]:.1e}')
        print(f'  train: loss {tr.get("total", 0):.4f}  L1 {tr.get("l1", 0):.4f}  VGG {tr.get("vgg", 0):.4f}  '
              f'IoU {tr.get("iou", 0):.3f}  SSIM {tr.get("ssim", 0):.3f}')
        print(f'  val  : loss {va.get("total", 0):.4f}  L1 {va.get("l1", 0):.4f}  VGG {va.get("vgg", 0):.4f}  '
              f'IoU {va.get("iou", 0):.3f}  SSIM {va.get("ssim", 0):.3f}  invasión cuello {va.get("cuello", 0):.1f}%')
        graficar_historial(hist, etapa, carpeta)
        if lote_visual is not None:
            grid_visual(modelo, lote_visual, etapa, epoca, carpeta, escritor)
        if sin_mejora >= CFG['PACIENCIA_EARLY_STOP']:
            print(f'⏹  Early stopping: {sin_mejora} épocas sin mejorar la validación.')
            break

    if escritor is not None:
        escritor.close()
    mejor_ruta = dir_ckpt / 'best.pth'
    if mejor_ruta.exists():
        modelo.load_state_dict(torch.load(mejor_ruta, map_location=DEVICE, weights_only=False)['modelo'])
    print(f'Etapa {etapa} terminada. Mejor val loss = {mejor:.4f}. Pesos: {mejor_ruta}')
    return hist

# %% [CELDA 13] ETAPA 1 — Pre-entrenamiento base (archive/labels_front.csv)
modelo = ModeloVTON(CFG['PESOS_PREENTRENADOS']).to(DEVICE)
HIST1 = entrenar_etapa(1, modelo, ITEMS1, MODO1, CFG['EPOCAS_ETAPA1'], CFG['LR_ETAPA1'])

# %% [CELDA 14] ETAPA 2 — Fine-tuning con tu catálogo (entrenamiento_ia_ropa/)
if MODO2 is None or not ITEMS2:
    print('⚠️  La carpeta de la Etapa 2 no tiene imágenes utilizables; se exportará el modelo de la Etapa 1.')
else:
    ck1 = SALIDA / f"etapa1_{CFG['VERSION_MODELO']}" / 'checkpoints' / 'best.pth'
    modelo = ModeloVTON(CFG['PESOS_PREENTRENADOS']).to(DEVICE)
    if ck1.exists():
        modelo.load_state_dict(torch.load(ck1, map_location=DEVICE, weights_only=False)['modelo'])
        print(f'Pesos de la Etapa 1 cargados desde {ck1}')
    else:
        print('⚠️  No existe el checkpoint de la Etapa 1; se parte de los pesos de ImageNet.')
    HIST2 = entrenar_etapa(2, modelo, ITEMS2, MODO2, CFG['EPOCAS_ETAPA2'], CFG['LR_ETAPA2'])

# %% [CELDA 15] Exportación a ONNX (batch dinámico) y verificación con onnxruntime
import onnx
import onnxruntime as ort

DIR_ONNX = SALIDA / 'onnx'
DIR_ONNX.mkdir(parents=True, exist_ok=True)
RUTA_ONNX = DIR_ONNX / 'vton_fashionstore.onnx'


class ModeloExportable(nn.Module):
    """Entradas/salidas planas y con nombre para el microservicio."""

    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, agnostic, parse, cloth, cloth_mask):
        o = self.m(agnostic, parse, cloth, cloth_mask)
        return o['final'], o['prenda_def'], o['mascara_def']


exportable = ModeloExportable(copy.deepcopy(modelo).float().cpu()).eval()
for mod in exportable.modules():
    mod.eval()
torch.manual_seed(0)
ejemplo = (torch.rand(2, 3, H, W) * 2 - 1, torch.rand(2, N_PARSE, H, W).round(),
           torch.rand(2, 3, H, W) * 2 - 1, torch.rand(2, 1, H, W).round())
NOMBRES_IN = ['agnostic', 'parse', 'cloth', 'cloth_mask']
NOMBRES_OUT = ['result', 'warped_cloth', 'warped_mask']
kwargs = dict(input_names=NOMBRES_IN, output_names=NOMBRES_OUT, opset_version=CFG['ONNX_OPSET'],
              do_constant_folding=True,
              dynamic_axes={n: {0: 'batch'} for n in NOMBRES_IN + NOMBRES_OUT})
if 'dynamo' in inspect.signature(torch.onnx.export).parameters:
    kwargs['dynamo'] = False          # exportador clásico: soporta dynamic_axes y GridSample (opset ≥16)
with torch.no_grad():
    torch.onnx.export(exportable, ejemplo, str(RUTA_ONNX), **kwargs)

onnx.checker.check_model(onnx.load(str(RUTA_ONNX)))
opciones = ort.SessionOptions()
opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sesion = ort.InferenceSession(str(RUTA_ONNX), opciones, providers=['CPUExecutionProvider'])
print('Entradas ONNX :', [(i.name, i.shape) for i in sesion.get_inputs()])
print('Salidas ONNX  :', [(o.name, o.shape) for o in sesion.get_outputs()])

for lote in (1, 3):                      # comprueba que el batch es dinámico
    entradas = [t[:1].repeat(lote, 1, 1, 1) for t in ejemplo]
    with torch.no_grad():
        ref = exportable(*entradas)
    t0 = time.time()
    sal = sesion.run(None, {n: e.numpy() for n, e in zip(NOMBRES_IN, entradas)})
    ms = (time.time() - t0) * 1000
    dif = max(float(np.abs(s - r.numpy()).max()) for s, r in zip(sal, ref))
    print(f'batch={lote}: diferencia máx. PyTorch vs ONNX = {dif:.2e} | {ms:.0f} ms en CPU')
    assert dif < 1e-2, 'La salida ONNX no coincide con PyTorch'

METADATOS = dict(
    modelo='vton_fashionstore.onnx', version=time.strftime('%Y%m%d-%H%M'),
    arquitectura='CP-VTON (GMM por flujo + TOM U-Net), backbone ResNet34 ImageNet',
    alto=H, ancho=W, opset=CFG['ONNX_OPSET'],
    entradas={
        'agnostic': f'float32 [batch,3,{H},{W}] en [-1,1]: persona con la ropa superior borrada (0 = gris)',
        'parse': f'float32 [batch,{N_PARSE},{H},{W}] en {{0,1}}: [preservar, area_generar, brazos, cara_cuello, silueta, fondo_visible]',
        'cloth': f'float32 [batch,3,{H},{W}] en [-1,1]: prenda centrada sobre fondo blanco',
        'cloth_mask': f'float32 [batch,1,{H},{W}] en {{0,1}}',
    },
    salidas={
        'result': 'imagen final [-1,1] (cuello/brazos/cara originales superpuestos)',
        'warped_cloth': 'prenda deformada [-1,1]', 'warped_mask': 'máscara de la prenda deformada [0,1]',
    },
    preprocesamiento='letterbox 192x256 sobre blanco → parser segformer_b2_clothes → derivar_mascaras()',
    parser=CFG['PARSER_HF'], etiquetas=ETIQUETAS, preservar_brazos=CFG['PRESERVAR_BRAZOS'],
)
(DIR_ONNX / 'vton_metadatos.json').write_text(json.dumps(METADATOS, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'✅ ONNX guardado en {RUTA_ONNX} ({RUTA_ONNX.stat().st_size / 1e6:.1f} MB)')

# %% [CELDA 16] (Opcional) Exportar también el parser a ONNX para que el backend no necesite PyTorch
if not MODO_PRUEBA:
    try:
        class ParserExportable(nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m

            def forward(self, pixel_values):
                return self.m(pixel_values=pixel_values).logits

        pe = ParserExportable(copy.deepcopy(PARSER.modelo).float().cpu()).eval()
        ruta_parser = DIR_ONNX / 'parser_segformer.onnx'
        kw = dict(input_names=['pixel_values'], output_names=['logits'], opset_version=CFG['ONNX_OPSET'],
                  dynamic_axes={'pixel_values': {0: 'batch'}, 'logits': {0: 'batch'}})
        if 'dynamo' in inspect.signature(torch.onnx.export).parameters:
            kw['dynamo'] = False
        with torch.no_grad():
            torch.onnx.export(pe, (torch.randn(1, 3, 512, 512),), str(ruta_parser), **kw)
        onnx.checker.check_model(onnx.load(str(ruta_parser)))
        (DIR_ONNX / 'parser_lut.json').write_text(json.dumps(PARSER.lut.tolist()), encoding='utf-8')
        print(f'✅ Parser ONNX guardado en {ruta_parser} (entrada 1x3x512x512 normalizada como SegformerImageProcessor)')
    except Exception as e:
        print(f'⚠️  No se pudo exportar el parser ({e}). El backend puede usar transformers para el parsing.')

# %% [CELDA 17] Inferencia de prueba con el ONNX (igual a como lo usará el backend FastAPI)


def preparar_entrada(persona_pil, prenda_pil):
    """Convierte (foto de la persona, foto de la prenda) en los 4 tensores del ONNX.
    El backend debe replicar EXACTAMENTE esta función (usa el mismo parser y derivar_mascaras)."""
    persona = letterbox(persona_pil.convert('RGB'))
    prenda = letterbox(prenda_pil.convert('RGB'))
    parse_p, parse_c = PARSER.parsear([persona, prenda], [getattr(persona_pil, 'ruta', None), getattr(prenda_pil, 'ruta', None)])
    m = derivar_mascaras(parse_p)
    parse_t, visible, _, _ = mapa_a_tensores(m)
    persona_t = pil_a_tensor(persona)
    mprenda = torch.from_numpy(mascara_de_prenda(prenda, parse_c).astype(np.float32))[None]
    prenda_t = pil_a_tensor(prenda) * mprenda + (1 - mprenda)
    return {'agnostic': (persona_t * visible)[None].numpy(), 'parse': parse_t[None].numpy(),
            'cloth': prenda_t[None].numpy(), 'cloth_mask': mprenda[None].numpy()}, persona_t


# Prueba REAL de probador: cada persona con una prenda DISTINTA a la que lleva puesta.
# (La prueba de v1 usaba la misma prenda de la foto y por eso "salía bien" aunque el modelo no transfiriera.)
_personas = [m for m in (DatasetVTON(ITEMS1[:24], MODO1, CACHE_LOCAL, False, POOL_PERSONAS)[i] for i in range(min(24, len(ITEMS1))))
             if m is not None][:4]
if MODO2 == 'prenda' and ITEMS2:
    _ds_c = DatasetVTON(ITEMS2[:12], 'prenda', CACHE_LOCAL, False, POOL_PERSONAS)
    _prendas = [m for m in (_ds_c[i] for i in range(len(_ds_c))) if m is not None]
else:
    _prendas = _personas[1:] + _personas[:1]          # prenda de OTRA persona
_n = min(len(_personas), len(_prendas))
if _n:
    fig, ax = plt.subplots(_n, 4, figsize=(11, 3.4 * _n), squeeze=False)
    for i in range(_n):
        per, pre = _personas[i], _prendas[i]
        entrada = {'agnostic': per['agnostica'][None].numpy(), 'parse': per['parse'][None].numpy(),
                   'cloth': pre['prenda'][None].numpy(), 'cloth_mask': pre['mascara_prenda'][None].numpy()}
        resultado = torch.from_numpy(sesion.run(['result'], entrada)[0][0])
        for j, (img, t) in enumerate([(per['persona'], 'Original'), (per['agnostica'], 'Agnóstica'),
                                      (pre['prenda'], 'Prenda nueva'), (resultado, 'Resultado ONNX')]):
            ax[i, j].imshow(tensor_a_numpy_img(img))
            ax[i, j].axis('off')
            if i == 0:
                ax[i, j].set_title(t)
    fig.tight_layout()
    mostrar(fig, DIR_ONNX / 'demo_inferencia_onnx.png')

print('\n================ RESUMEN ================')
print(f'Resultados en Drive: {SALIDA}')
print(f"  · Curvas y grids por época: {SALIDA}/etapa1_{CFG['VERSION_MODELO']}, {SALIDA}/etapa2_{CFG['VERSION_MODELO']}")
print(f'  · Checkpoints (.pth cada {CFG["CHECKPOINT_CADA"]} épocas + best/last): {SALIDA}/etapaN/checkpoints')
print(f'  · Modelo para el backend: {RUTA_ONNX} + vton_metadatos.json')
print('  · TensorBoard:  %load_ext tensorboard   y   %tensorboard --logdir "' + str(SALIDA / 'tensorboard') + '"')
