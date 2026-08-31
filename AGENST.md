# AGENST.md - Reglas e Instrucciones para Agentes Inteligentes (Antigravity/Gemini)

Este archivo define las restricciones de comportamiento, reglas de estilo y flujos de trabajo para los agentes de Inteligencia Artificial que colaboren en el desarrollo de la plataforma **FashionStore**.

## Directrices de Comportamiento del Agente

### 1. Modificación de Código y Documentación
- **Integridad:** Mantén intactos los comentarios, docstrings y anotaciones existentes que no estén directamente relacionados con tu cambio.
- **Consistencia:** Utiliza siempre español técnico y profesional para las explicaciones, y respeta la estructura del código base actual.
- **Precisión:** Al realizar cambios en archivos de documentación (`.md`), asegúrate de mantener la coherencia y no alterar las decisiones arquitectónicas previas sin aprobación del usuario.

### 2. Base de Datos y Persistencia
- **Aislamiento Transaccional:** Al interactuar con la base de datos PostgreSQL, cada consulta que afecte al stock de inventario o reservas concurrentes debe asegurar integridad transaccional rigurosa para evitar condiciones de carrera.
- **Validación:** Antes de sugerir o escribir consultas SQL complejas, verifica los modelos SQLAlchemy o el esquema de base de datos definido en el proyecto.

### 3. Restricciones Académicas
- **Google Cloud Platform (GCP):** Las propuestas de despliegue deben ser Serverless y sin uso de contenedores (prohibido utilizar Docker o Kubernetes).
- **No Frameworks Preconstruidos:** Queda estrictamente prohibido integrar o sugerir el uso de Shopify, WooCommerce, Magento o soluciones similares de E-Commerce llave en mano.

---

## Flujo de Trabajo Técnico

### Iteración 1 (Foco del Ciclo 1)
El agente debe priorizar las tareas relacionadas con la infraestructura base de seguridad y administración:
- Casos de uso **CU01 a CU10**.
- Configuración de FastAPI y JWT.
- CRUD web de catálogo, sucursales y empleados.

### Prácticas de Ingeniería de Software Senior
- **Validación antes de la acción:** Investiga el directorio de trabajo y verifica las dependencias reales del proyecto antes de sugerir comandos de instalación.
- **Clean Code:** Prioriza la legibilidad, la reutilización de componentes y la separación de responsabilidades.
- **Enfoque Pair Programming:** Explica brevemente la razón de tus decisiones técnicas antes de proceder a la ejecución.
