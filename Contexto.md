# Universidad Autónoma Gabriel René Moreno
### Facultad de Ingeniería en Ciencias de la Computación y Telecomunicaciones

**GRUPO # 29**

## Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual mediante Realidad Aumentada

**Integrantes:**
* Condori Diaz Marilyn Esther - 224051237
* Larrazabal Rojas Julio Cesar - 223049255

**Materia:** Sistemas de Información II

*Santa Cruz de la Sierra - 2026*

---

## Índice

* **1. PERFIL**
  * **1.1 INTRODUCCIÓN**
  * **1.2 OBJETIVOS**
    * 1.2.1 Objetivo General
    * 1.2.2 Objetivos Específicos
  * **1.3 DESCRIPCIÓN DEL PROBLEMA**
    * 1.3.1 Ausencia de un catálogo digital estructurado y comercialización dependiente de redes sociales
    * 1.3.2 Imposibilidad de previsualizar la prenda sobre el propio cuerpo antes de decidir la compra
    * 1.3.3 Desplazamientos físicos prolongados y tiempo perdido en la búsqueda de prendas
    * 1.3.4 Variabilidad de tallas entre fabricantes y ausencia de una referencia objetiva de calce
    * 1.3.5 Ausencia de un mecanismo que articule la reserva anticipada con la prueba física en tienda
    * 1.3.6 Gestión del inventario y las ventas sin trazabilidad digital
    * 1.3.7 Desarticulación entre los canales web, móvil y el componente de inteligencia artificial
  * **1.4 ALCANCE**
    * 1.4.1 Módulo de Autenticación y Gestión de Usuarios
    * 1.4.2 Módulo de Catálogo de Productos
    * 1.4.3 Módulo de Vestidor Virtual con Realidad Aumentada
    * 1.4.4 Módulo de Carrito de Compras y Pasarela de Pago
    * 1.4.5 Módulo de Reservas para Prueba en Tienda Física
    * 1.4.6 Módulo de Gestión de Inventario
    * 1.4.7 Módulo de Ventas y Pedidos
    * 1.4.8 Módulo de Envíos y Despacho
    * 1.4.9 Módulo Diferenciador: Inteligencia Artificial

* **Parte I – Fundamentación Teórica**
  * **Marco Conceptual: Comercio Electrónico Aumentado y Gestión Multisucursal**
    * a) Comercio Electrónico (E-Commerce)
    * Realidad Aumentada Aplicada al Vestidor Virtual
    * Gestión de Inventario: Stock Mínimo, Stock Máximo y Costeo por Promedio Ponderado
    * Modalidades de Compra: Reserva Presencial y Compra Digital
    * a. Experiencia como usuario/comprador
      * i. Amazon
      * ii. Alibaba
      * iii. Shopify
    * b. Experiencia como desarrollador
      * i. Magento
      * ii. PrestaShop
      * iii. WooCommerce
    * b) Pasarelas de Pago Electrónico y Puntos de Venta (POS)
    * c) Deliveries
      * a. Cómo funcionan los deliverys: Yaigo–Yummy
      * b. Cómo se calculan los pagos de una entrega
  * **Marco Metodológico: Ingeniería de Software**
    * d) Proceso Unificado de Desarrollo de Software (PUDS)
    * e) Lenguaje Unificado de Modelado (UML 2.5+)
  * **Marco Tecnológico y de Infraestructura**
    * Backend: Python como Lenguaje de Servidor
    * Angular como Framework de Frontend Web
    * Flutter y Dart para el Desarrollo de la Aplicación Móvil
    * PostgreSQL como Motor de Persistencia Relacional
    * Inteligencia Artificial Integrada mediante API: Recomendación, Chatbot y Procesamiento de Lenguaje Natural
    * Infraestructura Cloud, API REST y Restricciones sobre Frameworks de E-Commerce Preconstruidos
  * **Requisitos Funcionales**
  * **Requisitos No Funcionales**

* **Parte II – Proceso de Desarrollo**
  * **Captura de requisitos**
    * Identificación de actores y casos de uso
    * Priorizar casos de uso
    * Detallar casos de uso
  * **Análisis**
  * **Diseño**
  * **Implementación**
  * **Pruebas**
  * **Bibliografía**

---

## 1. PERFIL

### 1.1 INTRODUCCIÓN
El comercio electrónico de indumentaria enfrenta actualmente una limitación estructural: la imposibilidad de que la persona compradora verifique, antes de la compra, cómo le queda una prenda sobre su propio cuerpo. Esta limitación es particularmente relevante en el contexto boliviano, donde una porción significativa de la comercialización de ropa se realiza de manera informal a través de transmisiones en vivo ("lives") en redes sociales, en las que las vendedoras muestran la mercadería nueva por temporada y gestionan los pedidos de forma manual, sin un catálogo digital estructurado ni un mecanismo de trazabilidad entre la publicación, el pedido y el cobro.

Bajo este escenario, el presente proyecto propone el desarrollo de una Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual mediante Realidad Aumentada. La plataforma digitaliza el catálogo de prendas de la tienda y añade, como elemento diferenciador, un módulo de vestidor virtual que emplea realidad aumentada para permitir a la persona usuaria visualizar sobre sí misma distintas prendas, colores y modelos antes de decidir una compra o, alternativamente, antes de trasladarse físicamente a la tienda a probárselas.

El proyecto se desarrollará conforme a tres frentes tecnológicos indicados por la cátedra: una aplicación web, una aplicación móvil y un componente de inteligencia artificial, distribuidos según el stack tecnológico definido por el equipo: backend en Python con FastAPI, frontend web en Angular (TypeScript), aplicación móvil en Flutter (Dart) y base de datos relacional en PostgreSQL. El segmento específico de mercado que atenderá la tienda será sobre ropa en general (ropa de mujer, hombre, niños o público general).

---

### 1.2 OBJETIVOS

#### 1.2.1 Objetivo General
Desarrollar una plataforma de comercio electrónico para tienda de ropa con vestidor virtual mediante realidad aumentada.

#### 1.2.2 Objetivos Específicos
1. Recolectar los requisitos funcionales y no funcionales del sistema a partir de la caracterización del rubro, identificando los actores involucrados.
2. Analizar los requisitos recolectados para definir los casos de uso del sistema, diferenciando las funcionalidades que corresponderán al canal web de aquellas que corresponderán al canal móvil.
3. Diseñar la arquitectura del sistema y el modelo de base de datos relacional en PostgreSQL, garantizando la integridad referencial entre los módulos de catálogo, vestidor virtual, carrito, pagos, reservas e inventario.
4. Implementar el backend del sistema utilizando Python con el framework FastAPI, exponiendo los servicios necesarios para el catálogo, el carrito de compras, las reservas y la integración de la pasarela de pago.
5. Implementar el frontend web del sistema utilizando Angular (TypeScript), destinado preferentemente a la administración del catálogo y del inventario de la tienda.
6. Implementar la aplicación móvil del sistema utilizando Flutter (Dart), destinada preferentemente a la persona compradora, incluyendo el acceso a la cámara del dispositivo requerido por el módulo de vestidor virtual con realidad aumentada.
7. Desarrollar el módulo de vestidor virtual mediante realidad aumentada, que permita previsualizar prendas del catálogo sobre la imagen de la persona usuaria.
8. Integrar una pasarela de pago electrónico para la confirmación de compras directas realizadas desde el dispositivo móvil de la persona usuaria.
9. Desarrollar el mecanismo de reserva de prendas para prueba física en tienda, que permita a la persona usuaria seleccionar prendas y agendar un horario de visita, evitando así la búsqueda física prolongada descrita como problema por la docente.
10. Definir e implementar el alcance funcional del componente de inteligencia artificial, como motor de sugerencias y creación de reportes.
11. Realizar pruebas funcionales de los módulos del sistema y gestionar el control de versiones mediante un repositorio Git, conforme a las buenas prácticas de gestión de configuración de software.

---

### 1.3 DESCRIPCIÓN DEL PROBLEMA

#### 1.3.1 Ausencia de un catálogo digital estructurado y comercialización dependiente de redes sociales
El primer problema identificado es de naturaleza estructural: la tienda no cuenta con un catálogo digital propio, sino que publica su mercadería nueva a través de transmisiones en vivo por redes sociales cada vez que cambia la temporada —por ejemplo, al liquidar ropa de invierno con la llegada de la primavera—. Este mecanismo funciona como escaparate temporal, no como catálogo persistente: una vez finalizada la transmisión, la información sobre qué prendas existen, en qué tallas y a qué precio deja de estar disponible de forma organizada para quien no presenció la publicación en el momento exacto en que ocurrió.

La consecuencia directa de este esquema es que la selección de prendas, la captura de datos de contacto y la coordinación del pedido se resuelven de manera manual dentro de la dinámica misma de la transmisión, normalmente por mensajería directa. No existe, en este proceso, un sistema de información que centralice la oferta vigente de la tienda, lo que impide tanto a la persona compradora buscar o filtrar productos como a la tienda mantener un registro consistente de lo que efectivamente ofrece en un momento dado.

#### 1.3.2 Imposibilidad de previsualizar la prenda sobre el propio cuerpo antes de decidir la compra
Un segundo problema, de carácter central para este proyecto, es la ausencia de cualquier mecanismo que permita a la persona compradora anticipar cómo le quedará una prenda antes de adquirirla o de trasladarse a probársela. La compra a través de redes sociales se sostiene casi exclusivamente sobre fotografías del producto, sin posibilidad de contrastar esa imagen con el propio cuerpo de la persona interesada.

Esta carencia empuja a la persona compradora hacia dos únicos caminos: comprar bajo incertidumbre, asumiendo el riesgo de que la prenda no le siente como esperaba, o desplazarse físicamente para probársela antes de decidir. Ninguna de las dos opciones resulta satisfactoria: la primera genera devoluciones y reclamos, y la segunda reintroduce el costo de tiempo y desplazamiento que la venta por redes sociales pretendía evitar.

#### 1.3.3 Desplazamientos físicos prolongados y tiempo perdido en la búsqueda de prendas
Directamente asociado al problema anterior, se identifica una pérdida considerable de tiempo cuando la verificación del calce solo puede resolverse de manera presencial. Es común que una persona recorra más de una tienda física en una misma jornada sin concretar ninguna compra, dedicando un tiempo considerable a la prueba de distintas prendas antes de tomar una decisión.

Este comportamiento, señalado explícitamente por la docente como parte del caso de estudio, varía de una persona a otra según sus propias preferencias y nivel de exigencia al momento de elegir una prenda; sin embargo, en todos los casos evidencia la misma causa raíz: la ausencia de una herramienta que permita descartar o preseleccionar opciones antes de llegar a la tienda, concentrando el tiempo de visita física únicamente en la confirmación final.

#### 1.3.4 Variabilidad de tallas entre fabricantes y ausencia de una referencia objetiva de calce
Un cuarto problema, que agrava a los dos anteriores, es la falta de estandarización de tallas entre fabricantes. Una misma talla nominal —por ejemplo, un número de calzado o una talla de prenda de vestir— puede corresponder a dimensiones reales distintas según la procedencia o el fabricante del producto, lo que introduce un margen de error que ninguna ficha de producto basada solo en texto o fotografía logra despejar.

Esta variabilidad explica, en gran medida, por qué la prueba física continúa siendo percibida como indispensable bajo el esquema actual: la persona compradora no confía en que la talla indicada por la tienda coincida con la talla que efectivamente necesita, y prefiere verificarlo de manera directa antes de comprometerse con la compra.

#### 1.3.5 Ausencia de un mecanismo que articule la reserva anticipada con la prueba física en tienda
En el escenario actual no existe una forma de que la persona interesada seleccione con anticipación un conjunto de prendas —en una talla y un color determinados— y agende un horario para acudir a probárselas directamente en la tienda física, de modo que la mercadería ya esté disponible y preparada a su llegada. Al no existir este mecanismo, la persona compradora debe repetir en la tienda física todo el proceso de búsqueda y selección que, en principio, ya había resuelto mentalmente al ver la publicación en redes sociales.

Esta ausencia tiene un efecto compuesto: además de no ahorrar tiempo a la persona compradora, tampoco permite a la tienda anticipar la demanda de un horario determinado ni preparar con antelación las prendas que probablemente se solicitarán, perdiendo así una oportunidad de organización interna que un sistema de reservas resolvería de manera directa.

#### 1.3.6 Gestión del inventario y las ventas sin trazabilidad digital
Un sexto problema corresponde a la forma en que se gestionan el abastecimiento, el inventario y las ventas. Al realizarse la compra de mercadería a los proveedores, la actualización de existencias y el registro de pedidos de manera manual e informal —mensajes directos y transmisiones en vivo—, no existe trazabilidad digital entre lo comprado a proveedores, lo publicado, lo reservado y lo efectivamente vendido. En consecuencia, la plataforma sí contempla la gestión de proveedores y el registro de ingresos de mercadería (órdenes de compra), valorando el inventario mediante el método de promedio ponderado, de modo que cada movimiento de stock —entrada por compra, salida por venta o bloqueo por reserva— quede registrado y sea auditable.

La falta de trazabilidad dificulta que la tienda conozca, en un momento dado, cuánta mercadería de una prenda específica sigue disponible, cuánta ha sido reservada y cuánta ha sido vendida, lo que incrementa el riesgo de comprometer en una venta una prenda que ya no existe en inventario o que se encuentra retenida por una reserva pendiente.

#### 1.3.7 Desarticulación entre los canales web, móvil y el componente de inteligencia artificial
Finalmente, se identifica la ausencia de una plataforma unificada que integre, de manera conjunta, un canal web, un canal móvil y un componente de inteligencia artificial. La docente indicó explícitamente que el sistema debía trabajar sobre estos tres frentes tecnológicos, sin que el esquema de venta actual disponga de ninguno de ellos: no existe aplicación móvil ni web propia de la tienda, y tampoco existe ningún uso de inteligencia artificial dentro del proceso de venta descrito.

Esta desarticulación consolida, en un plano tecnológico, todas las problemáticas anteriores: sin un canal digital propio, la tienda permanece dependiente de plataformas de terceros (las redes sociales) para su operación comercial, sin control sobre la presentación de su catálogo, la trazabilidad de sus ventas ni la experiencia de previsualización que un vestidor virtual con realidad aumentada podría ofrecer.

En síntesis, las problemáticas descritas —ausencia de catálogo digital, imposibilidad de previsualización, desplazamientos físicos prolongados, variabilidad de tallas, falta de un mecanismo de reserva, ausencia de trazabilidad de inventario y ventas, y desarticulación tecnológica— comparten una misma causa raíz: la inexistencia de una plataforma digital propia de la tienda que integre catálogo, previsualización, compra, reserva e inventario en un único sistema. La plataforma propuesta en este documento busca dar respuesta integral a esta problemática.

---

### 1.4 ALCANCE

#### 1.4.1 Módulo de Autenticación y Gestión de Usuarios
Administra el acceso de las personas clientas y del personal de la tienda a la plataforma, distinguiendo perfiles con distinto nivel de privilegio. Módulo indispensable porque el carrito, las reservas y los pagos requieren asociar cada operación a una persona identificada.
* Auto-registro e inicio de sesión de personas clientas tanto desde la aplicación móvil como desde el sitio web (como en cualquier tienda de comercio electrónico, el cliente puede comprar y consultar su cuenta por ambos canales).
* Gestión de cuentas del personal administrativo (Encargado, Cajero) desde el canal web, a cargo del Superadmin. El personal nunca se auto-registra: sus cuentas siempre las crea el Superadmin.
* Recuperación de credenciales mediante enlace temporal enviado por correo electrónico (válido 5 minutos). El enlace es la **única vía**: la pantalla de nueva contraseña solo se abre al tocarlo, con el token incluido en la URL; nunca se ingresa un código a mano.
* Diferenciación de roles: Superadmin, Encargado de sucursal, Cajero y Cliente, cada uno con sus accesos.
* Navegación del catálogo público sin necesidad de cuenta (usuario visitante); la cuenta solo es obligatoria para reservar, comprar o usar el vestidor virtual.

#### 1.4.2 Módulo de Catálogo de Productos
Centraliza la información de las prendas disponibles en la tienda, sustituyendo la publicación informal por transmisiones en vivo por una fuente única, buscable y permanentemente disponible del inventario comercializable.
* Listado y búsqueda de prendas por categoría, talla y color.
* Ficha de producto con imágenes de referencia, precio y variantes disponibles.
* Alta, edición y baja de prendas desde el canal web administrativo.
* Filtrado por temporada, en línea con la dinámica estacional descrita en clase.

#### 1.4.3 Módulo de Vestidor Virtual con Realidad Aumentada
Permite previsualizar una o varias prendas del catálogo sobre la imagen de la persona usuaria antes de decidir una compra directa o una visita física a la tienda.
* Superposición de la prenda seleccionada sobre la imagen captada por la cámara del dispositivo móvil.
* Comparación entre variantes de color o modelo de una misma prenda.
* Acceso directo desde la ficha de producto del catálogo.
* Registro de las prendas probadas virtualmente durante la sesión.

#### 1.4.4 Módulo de Carrito de Compras, Medios de Pago y Facturación
Reúne las prendas seleccionadas para compra directa y gestiona su cobro. La tienda opera de
forma **presencial (formal, con patente municipal e impuestos) y en línea** al mismo tiempo,
por lo que el cobro es **agnóstico al canal**: cualquier transacción confirmada —electrónica o
en caja— se registra de manera unificada.
* Adición, eliminación y modificación de cantidades de prendas en el carrito; bloqueo automático de ítems con existencia cero.
* Cálculo automático del subtotal y el total de la compra.
* **Medios de pago modelados por herencia (generalización):** `MedioDePago` ⭅ Efectivo, Tarjeta, QR y Crédito. El QR es el medio más usado en el contexto boliviano y solo opera de forma local.
* Pasarela electrónica (Stripe / QR) para la compra remota y Punto de Venta (POS) para el pago presencial en caja.
* **Comprobante fiscal:** emisión de **Factura** (con IVA 13 % y código de control) o **Nota de Entrega**, modeladas como `Comprobante` ⭅ Factura / NotaDeEntrega.
* Actualización del estado del pedido tras la confirmación del pago.

#### 1.4.5 Módulo de Reservas para Prueba en Tienda Física
Habilita a la persona usuaria a seleccionar con anticipación un conjunto de prendas y agendar un horario de visita a la tienda física, de modo que la mercadería esté disponible a su llegada y se reduzca el tiempo de búsqueda.
* Selección de prendas, tallas y colores a reservar.
* Agenda de fecha y horario de visita.
* Panel de reservas pendientes para el personal de la tienda.
* Confirmación de compra posterior a la prueba física, mediante el módulo de pago.

#### 1.4.6 Módulo de Gestión de Inventario y Proveedores
Mantiene actualizado el registro de existencias por prenda, talla, color y sucursal, alimentándose de las compras registradas a los proveedores y de los movimientos de venta y reserva.
* Registro de proveedores de ropa (NIT, contacto) y su vinculación con las variantes que abastecen.
* Registro de ingresos de mercadería (órdenes de compra) que incrementan el stock de la sucursal destino, indicando el **costo unitario del lote**.
* **Valoración del inventario por costo promedio ponderado (Ciclo 1):** el sistema calcula el **capital invertido** en mercadería usando el **prorrateo** de las compras (no el último costo unitario). Ejemplo: dos unidades compradas a 10 y a 14 valen 24, no 28 (costo promedio 12).
* **Ajustes de inventario (Ciclo 1):** registro de mermas, daños y pérdidas que reducen las existencias dejando un movimiento auditable en el libro mayor.
* Registro y actualización de existencias por variante de producto y por sucursal.
* Alerta de stock mínimo/agotado.
* Descuento automático de inventario ante una venta directa o una reserva confirmada, y liberación automática del stock bloqueado al cancelarse una reserva.
* Consulta de disponibilidad desde el canal web administrativo.

#### 1.4.7 Módulo de Ventas y Pedidos
Consolida el registro de toda venta concretada, distinguiendo entre la compra directa desde el carrito y la compra posterior a una reserva atendida, dando trazabilidad a un proceso que hoy se gestiona de manera informal.
* Registro diferenciado de ventas directas y ventas vía reserva.
* Historial de pedidos por persona clienta.
* Consulta administrativa del estado de cada pedido.
* Vinculación de cada pedido con su respectivo movimiento de inventario.

#### 1.4.8 Módulo de Envíos y Despacho
Gestiona el traslado de las prendas adquiridas mediante compra directa hacia el domicilio indicado por la persona clienta, cubriendo la etapa final del proceso de compra en línea.
* Registro de la dirección de destino del pedido.
* Actualización del estado del envío: Preparación, En camino o Entregado.
* Consulta del estado de envío por parte de la persona clienta.
* Vinculación del envío con el pedido y el pago confirmado.

#### 1.4.9 Módulo Diferenciador: Inteligencia Artificial y Analítica
* Motor de recomendación de prendas o tallas impulsada con IA a partir del historial de reservas y compras de la persona usuaria.
* **Búsqueda y reportes por comando de voz (NLP):** el usuario formula una consulta hablada
  (p. ej. *"quiero las camisas que llegaron en septiembre, talla M, color blanco"*) y el
  sistema la traduce a una consulta estructurada ejecutable contra la base de datos.
* **Dashboard y reportes gerenciales:** gráficos de ventas e inventario, kardex, productos más
  vendidos, ingresos por sucursal y rendimiento de cajeros, exportables a PDF/CSV.

---

## Parte I – Fundamentación Teórica

El presente capítulo establece los fundamentos conceptuales, metodológicos y tecnológicos que sustentan el desarrollo de la Plataforma Inteligente de Comercio Electrónico para Cadena de Tiendas de Ropa (FashionStore), un sistema web y móvil que integra un vestidor virtual mediante realidad aumentada, mecanismos de pago electrónico y presencial, gestión multisucursal de inventario y funcionalidades de inteligencia artificial orientadas a la recomendación de prendas y la generación de reportes por comando de voz. El marco teórico se estructura en tres dimensiones complementarias: el marco conceptual, que delimita el dominio del problema (comercio electrónico, realidad aumentada, gestión de inventarios y medios de pago); el marco metodológico, que define el proceso de ingeniería de software adoptado para la construcción incremental del sistema; y el marco tecnológico, que describe las herramientas y plataformas seleccionadas para su implementación.

---

### Marco Conceptual: Comercio Electrónico Aumentado y Gestión Multisucursal

#### a) Comercio Electrónico (E-Commerce)
El comercio electrónico, o e-commerce, se define como el conjunto de transacciones comerciales de compra, venta e intercambio de bienes y servicios realizadas a través de medios electrónicos, principalmente internet (Laudon & Traver, 2021). A diferencia de un catálogo digital estático, una plataforma de comercio electrónico integra funcionalidades transaccionales completas: gestión de catálogo, carrito de compra, procesamiento de pago, control de inventario y logística de entrega, todas ellas operando sobre una arquitectura común.

En el caso de FashionStore, el modelo de negocio corresponde a una plataforma multisucursal de tipo B2C (Business-to-Consumer), en la cual una misma cadena comercial administra de forma centralizada la operación de varios puntos de venta físicos, permitiendo que un cliente consulte la disponibilidad de una prenda en distintas sucursales y que la organización mantenga sincronizado el inventario entre ellas. Esta característica introduce el concepto de omnicanalidad, entendido como la integración coherente de los canales de interacción con el cliente (aplicación móvil, sitio web responsivo y tienda física) de modo que la experiencia de compra sea continua independientemente del canal utilizado.

#### Realidad Aumentada Aplicada al Vestidor Virtual
La realidad aumentada (RA) es una tecnología que superpone elementos generados por computadora —imágenes, modelos tridimensionales o información contextual— sobre la percepción del entorno físico real, en tiempo real y de forma interactiva (Azuma, 1997). A diferencia de la realidad virtual, que sustituye completamente el entorno del usuario, la realidad aumentada complementa la escena real con capas digitales adicionales, habitualmente a través de la cámara de un dispositivo móvil.

Dentro del dominio de la moda y el retail, esta tecnología da lugar al concepto de vestidor virtual (virtual try-on), una funcionalidad que permite a un usuario visualizar cómo le quedaría una prenda —color, corte o modelo— sin necesidad de probársela físicamente. Este mecanismo responde directamente a un problema identificado en el proceso de compra tradicional de ropa: el tiempo invertido en desplazarse entre tiendas y probar múltiples prendas antes de decidir una compra, agravado por la falta de estandarización de tallas entre fabricantes. El vestidor virtual no elimina por completo la necesidad de probarse la prenda de forma física —dado que las tallas varían según el fabricante—, pero permite al cliente preseleccionar las prendas de su interés antes de acudir a la tienda, optimizando así el tiempo de decisión.

#### Gestión de Inventario: Stock Mínimo, Stock Máximo y Costeo por Promedio Ponderado
La gestión de inventarios constituye una función crítica en cualquier plataforma de comercio electrónico, dado que la disponibilidad real del producto condiciona la posibilidad de concretar una venta. Los modelos clásicos de administración de inventarios (Chase, Jacobs & Aquilano, 2018) definen el stock mínimo como el nivel de existencias por debajo del cual se activa una orden de reposición ante uno o más proveedores, y el stock máximo como el límite superior de almacenamiento que evita la sobreinversión de capital en mercadería de baja rotación.

Este segundo concepto resulta especialmente relevante para FashionStore: la adquisición de mercadería a bajo costo por parte de un proveedor no constituye por sí sola una decisión acertada si el producto no presenta rotación, ya que el capital inmovilizado en inventario no vendido representa una inversión estancada. Para valorar financieramente el inventario ante fluctuaciones de precio de compra entre proveedores, se emplea el método de costeo por promedio ponderado, el cual calcula el costo unitario de un artículo como el promedio de los costos de adquisición ponderado por las cantidades compradas en cada lote, permitiendo una valoración más representativa que el simple registro del último precio de compra.

#### Modalidades de Compra: Reserva Presencial y Compra Digital
El modelo de negocio de FashionStore contempla dos modalidades de adquisición no excluyentes. La primera, la compra digital, corresponde al proceso transaccional íntegramente remoto: selección de la prenda en el catálogo, confirmación en el carrito de compra y pago a través de una pasarela electrónica, sin que el cliente visite la tienda física. La segunda, la reserva para prueba presencial, corresponde a un mecanismo híbrido en el cual el cliente preselecciona un conjunto de prendas mediante el vestidor virtual y agenda una fecha y hora para acudir a una sucursal a probárselas físicamente antes de confirmar la compra. Este segundo esquema se sustenta conceptualmente en los sistemas de reserva de citas (appointment scheduling), en los que el bloqueo temporal de un recurso en este caso, la disponibilidad de las prendas y la atención del personal de sucursal, reduce la incertidumbre operativa y mejora la experiencia del cliente al evitar tiempos de espera o la indisponibilidad del producto al momento de su visita.

#### a. Experiencia como usuario/comprador

##### i. Amazon
Amazon funciona como un marketplace híbrido: una parte de sus ingresos proviene de la venta minorista directa y otra de los servicios que presta a vendedores externos. Su modelo de negocio combina el comercio minorista masivo, los servicios a terceros dentro del marketplace, la membresía por suscripción (Prime), la publicidad en línea y la computación en la nube a través de AWS. Desde la perspectiva del comprador, el catálogo integra productos vendidos directamente por Amazon junto con productos de miles de vendedores independientes, distinguibles por la indicación de quién despacha y quién vende el artículo. La experiencia de compra se apoya en un buscador de productos, un checkout simplificado, reseñas de otros usuarios y, para los miembros de Prime, envíos acelerados. De hecho, los vendedores externos han representado de manera sostenida alrededor del 60 % de todos los productos vendidos en Amazon, lo que evidencia que gran parte del catálogo que percibe el usuario no proviene directamente de Amazon, sino de un ecosistema de terceros que utiliza su infraestructura logística y de pagos.

##### ii. Alibaba
A diferencia de Amazon, "Alibaba" no es una única tienda sino un grupo de plataformas con modelos de negocio distintos entre sí, lo cual resulta clave para comprender su funcionamiento desde el punto de vista del usuario:
* **Alibaba.com:** Portal de comercio electrónico B2B internacional que conecta a fabricantes y mayoristas con importadores de otros países, orientado a compras de volumen y no al consumidor final. Es el portal original con el que Jack Ma fundó la compañía en 1999.
* **1688.com:** Plataforma B2B doméstica dentro de China, dedicada a transacciones entre fabricantes y mayoristas locales, de negocio a negocio dentro del propio país.
* **Taobao:** Plataforma C2C dirigida al consumidor chino, en la que predominan tiendas de particulares o pequeños comercios minoristas; es la plataforma "madre" y la de mayor tamaño a nivel global para la venta a consumidor en China.
* **Tmall:** Plataforma B2C desprendida de Taobao, orientada a marcas reconocidas y a un consumidor con mayor poder adquisitivo, con más de 500 millones de usuarios activos distribuidos en más de 3.700 categorías de producto.
* **AliExpress:** Plataforma orientada al comprador internacional, con vendedores que pueden ser empresas o particulares.

Como usuario, esta segmentación implica que “comprar en Alibaba" no es una experiencia única: el flujo de un importador que negocia con un fabricante en Alibaba.com es sustancialmente distinto al de un comprador final que adquiere un producto de manera inmediata en AliExpress o Tmall. En cuanto a su modelo de ingresos, Alibaba obtiene una parte de sus ganancias mediante comisiones sobre las transacciones de Tmall y, adicionalmente, mediante la venta de publicidad y posicionamiento por palabras clave dentro de Taobao y Tmall, en un esquema similar a la subasta de palabras clave de los motores de búsqueda.

##### iii. Shopify
A diferencia de Amazon y Alibaba, Shopify no es un marketplace en el que el usuario navegue un catálogo centralizado, sino una plataforma de comercio (SaaS) que permite a comerciantes independientes crear su propia tienda en línea. Para el usuario final, comprar en una tienda "Shopify" significa interactuar con un sitio propio de la marca, cuyo checkout está optimizado por Shopify para maximizar la conversión y admite decenas de métodos de pago, entre ellos tarjeta de crédito y pagos en línea a través de más de 250 pasarelas alternativas como Stripe o PayPal. Desde la perspectiva del comerciante, Shopify resuelve de forma integrada el alojamiento, la pasarela de pago, el certificado de seguridad y la integración con canales de venta externos (redes sociales), con planes de suscripción mensual escalonados según el tamaño del negocio.

#### b. Experiencia como desarrollador
Estas tres herramientas corresponden a sistemas de gestión de contenido (CMS) para comercio electrónico, orientados a que un equipo de desarrollo construya y despliegue su propia tienda en línea, a diferencia de Shopify, que es una solución cerrada de tipo SaaS.

##### i. Magento
Magento es una plataforma de comercio electrónico de código abierto, desarrollada sobre arquitectura LAMP (Linux, Apache, MySQL/MariaDB y PHP) utilizando el framework Zend, y fue adquirida por eBay en 2010, lo que le dio el respaldo de una de las compañías líderes del comercio electrónico. Está orientada a tiendas grandes con catálogos extensos y alta necesidad de personalización: su versión de pago tiene un costo aproximado de 15.500 dólares anuales e incluye asesoría personalizada por parte de los desarrolladores del producto. Su proceso de instalación y configuración es más extenso que el de sus alternativas, precisamente porque ofrece una cantidad mayor de opciones configurables de fábrica —gestión avanzada de precios, multi-tienda, multi-idioma—, lo que la vuelve más robusta pero también más costosa de implementar y mantener, siendo recomendable para empresas con presupuestos de desarrollo amplios.

##### ii. PrestaShop
PrestaShop es igualmente una solución de código abierto, construida sobre PHP con gestión de datos en MySQL, diseñada para crear, administrar y lanzar tiendas en línea sin costo de licencia. Su núcleo gratuito se complementa con un extenso catálogo de módulos y plantillas que permiten ampliar sus funcionalidades según las necesidades del negocio, contando con más de 10.000 extensiones disponibles. Se la considera una alternativa intermedia entre WooCommerce y Magento: requiere menos recursos de servidor que Magento, pero ofrece de fábrica funcionalidades avanzadas de catálogo y gestión de stock que WooCommerce no trae por defecto, por lo que suele recomendarse para tiendas con catálogos amplios que no requieren necesariamente la escala de Magento.

##### iii. WooCommerce
WooCommerce no es una plataforma independiente, sino un plugin de comercio electrónico para WordPress, desarrollado originalmente en Estados Unidos y adquirido por Automattic en 2015. Su principal ventaja para un equipo de desarrollo es la simplicidad de instalación: al ser un plugin, se configura sobre un sitio WordPress ya existente sin requerir un servidor especializado ni conocimientos avanzados de programación, a diferencia de PrestaShop y Magento, que suelen requerir la intervención de un desarrollador.

Su limitación principal es que muchas funcionalidades que otras plataformas incluyen por defecto (como ser: gestión avanzada de variantes, multidivisa, reportes) deben añadirse mediante plugins adicionales, lo que puede derivar en una arquitectura menos cohesionada a medida que la tienda crece.

#### b) Pasarelas de Pago Electrónico y Puntos de Venta (POS)
Una pasarela de pago (payment gateway) es un servicio que autoriza y procesa de forma segura transacciones electrónicas entre un comprador y un vendedor, encargándose de la tokenización de los datos sensibles de la tarjeta y del cumplimiento del estándar de seguridad PCI DSS (Payment Card Industry Data Security Standard). Plataformas como PayPal y Stripe centralizan esta responsabilidad, liberando al sistema desarrollado de la necesidad de almacenar directamente datos de tarjetas.

De forma complementaria, un Punto de Venta o POS (Point of Sale) es el subsistema mediante el cual se registra y cobra una transacción en el momento y lugar en que el cliente adquiere físicamente el producto. En el caso de FashionStore, la coexistencia de ambos mecanismos —pasarela digital para la compra remota y POS para el pago presencial en caja tras una reserva— exige que el módulo de ventas del sistema sea agnóstico respecto al canal de cobro, registrando de manera unificada cualquier transacción confirmada, ya sea electrónica o presencial, para mantener la consistencia del inventario y de los reportes financieros.

#### c) Deliveries

##### a. Cómo funcionan los deliverys: Yaigo–Yummy
Yaigo es una startup boliviana de delivery y comercio electrónico, fundada en 2015 bajo la premisa de integrar en una sola plataforma al cliente, al comercio afiliado y al repartidor. Su propuesta de valor es la siguiente: el cliente solicita un pedido en restaurantes, supermercados, farmacias u otros comercios afiliados, y la aplicación coordina en tiempo real la recolección y entrega. Operativamente, los repartidores reciben el pedido asignado por el sistema, se dirigen al comercio de origen, retiran la mercadería y la entregan en el domicilio indicado por el cliente, mientras la aplicación mantiene informados tanto al comercio como al cliente sobre el estado del pedido en tiempo real.

En 2021, Yaigo fue adquirida por Yummy, una superapp de delivery y transporte con operaciones previas en Venezuela, Perú y Chile. Esta adquisición permitió a Yummy expandir su presencia hacia Bolivia y Paraguay, en un momento en que Yaigo ya se había consolidado como la aplicación de delivery más descargada de Bolivia, atendiendo más de 5.000 pedidos diarios y una facturación mensual superior al millón de dólares. Evolucionó típicamente de una aplicación de delivery de nicho hacia un modelo de superapp multivertical (comida, farmacia, supermercado y transporte de pasajeros integrados en una sola plataforma).

##### b. Cómo se calculan los pagos de una entrega
El cálculo de la tarifa que paga el cliente final por el servicio de delivery, y el cálculo del pago que recibe el repartidor por realizarlo, son dos cuestiones relacionadas pero distintas:
* **Tarifa al cliente:** El esquema más común es una tarifa escalonada por distancia: una tarifa base cubre un primer tramo corto, y a partir de allí el costo se incrementa proporcionalmente por cada kilómetro adicional recorrido. Un ejemplo documentado del propio mercado boliviano es el de Yaigo en la ciudad de Sucre, donde la tarifa básica es de 7 bolivianos para una distancia de cero a 1,5 kilómetros desde el punto de referencia, incrementándose en 3 bolivianos por cada kilómetro adicional recorrido. Este mismo principio es el que describe el concepto de tarifa por anillos, en el que el costo aumenta un monto fijo a medida que la entrega cruza anillos de distancia sucesivos respecto del punto de origen.
* **Pago al repartidor:** De forma paralela, el monto que percibe el repartidor por cada entrega suele calcularse también en función de la distancia efectivamente recorrida, computada en dos tramos: desde el punto de inicio del recorrido del repartidor hasta el punto de recogida del pedido, y desde el punto de recogida hasta el punto de entrega final, aplicando una tarifa por kilómetro fijada por la empresa que, en el mercado boliviano, se ha ubicado en un rango cercano a 1,98–1,99 bolivianos por kilómetro, siendo la distancia el mecanismo principal de cálculo y control de la remuneración del repartidor.

*Otros factores del cálculo:* Además de la distancia, pueden incorporar variables adicionales: el peso o volumen del paquete, el tamaño de la entrega y la frecuencia o el tipo de servicio contratado (entrega estándar frente a una entrega prioritaria o programada para una franja horaria específica, como sería el caso de agendar una reserva).

---

### Marco Metodológico: Ingeniería de Software

#### d) Proceso Unificado de Desarrollo de Software (PUDS)
El desarrollo del proyecto adopta el Proceso Unificado de Desarrollo de Software (PUDS), un marco de trabajo disciplinado que organiza el desarrollo en torno a tres principios fundamentales (Jacobson, Booch & Rumbaugh, 2000): estar dirigido por casos de uso, que actúan como el artefacto primario que guía la captura de requisitos, el análisis y el diseño; estar centrado en la arquitectura, de modo que las decisiones estructurales se establecen tempranamente para reducir el riesgo técnico; y ser iterativo e incremental, construyendo el software mediante ciclos sucesivos que producen incrementos funcionales verificables.

Para este proyecto, el PUDS se aplica de manera interna y se organiza en tres iteraciones, cada una de las cuales recorre de forma abreviada las cinco disciplinas del proceso: captura de requisitos, análisis, diseño, implementación y prueba. Cada iteración incorpora un subconjunto priorizado de casos de uso, de manera que al final de cada ciclo se dispone de un incremento operativo del sistema, evaluable de forma independiente antes de iniciar el ciclo siguiente.

#### e) Lenguaje Unificado de Modelado (UML 2.5+)
El Lenguaje Unificado de Modelado (UML), en su versión 2.5 o superior, constituye el estándar internacional (ISO/IEC 19501) empleado para visualizar, especificar y documentar los artefactos del sistema (Rumbaugh, Jacobson & Booch, 2007). Su empleo permite representar de forma no ambigua tanto la estructura estática de la plataforma (diagramas de clases, de componentes y de despliegue) como su comportamiento dinámico (diagramas de casos de uso, de actividades y de secuencia), constituyendo el vínculo formal entre los requisitos identificados (por ejemplo, el flujo de reserva de prendas o el proceso de pago en el punto de caja) y su correspondiente solución técnica. La documentación generada mediante UML no es un artefacto accesorio, sino la evidencia formal de las decisiones de ingeniería que sustentan la defensa del proyecto.

---

### Marco Tecnológico y de Infraestructura

#### Backend: Python como Lenguaje de Servidor
Python, habitualmente combinado con el framework FastAPI para la construcción de servicios web asíncronos y de alto rendimiento, considerada tecnológicamente válida para el proyecto, y representa la herramienta con la que se construirá la lógica de negocio, la validación de datos y la exposición de servicios mediante una interfaz de programación de aplicaciones (API REST).

#### Angular como Framework de Frontend Web
Angular es un framework de desarrollo frontend basado en TypeScript, mantenido por Google, que implementa una arquitectura de componentes con enlace de datos bidireccional (two-way data binding) e inyección de dependencias nativas. Su adopción para la interfaz web de FashionStore permite construir una aplicación de página única (Single Page Application, SPA) capaz de renderizar de forma reactiva el catálogo de prendas, el carrito de compra y los paneles administrativos, además de facilitar el diseño responsivo requerido para que determinadas funcionalidades —como la compra digital— puedan operar indistintamente en escritorio y en dispositivos móviles a través del navegador.

#### Flutter y Dart para el Desarrollo de la Aplicación Móvil
Flutter, framework de código abierto desarrollado por Google y basado en el lenguaje Dart, permite la construcción de aplicaciones móviles nativas para Android e iOS a partir de una única base de código. Su motor de renderizado propio garantiza una experiencia de usuario fluida y consistente entre plataformas, característica particularmente relevante para las funcionalidades que este proyecto declara como obligatoriamente móviles: el acceso a la cámara del dispositivo para el vestidor virtual con realidad aumentada, la reserva de prendas y la captura de comandos de voz para la generación de reportes mediante inteligencia artificial.

#### PostgreSQL como Motor de Persistencia Relacional
PostgreSQL es un sistema de gestión de bases de datos relacional de código abierto que garantiza las propiedades ACID (Atomicidad, Consistencia, Aislamiento y Durabilidad), condición indispensable para un sistema que gestiona simultáneamente inventario compartido entre sucursales, reservas con bloqueo temporal de disponibilidad y transacciones de pago. El uso de un motor transaccional robusto evita condiciones de carrera en escenarios críticos, como el descuento concurrente de stock cuando dos clientes intentan adquirir la última unidad disponible de una prenda en distintas sucursales.

#### Inteligencia Artificial Integrada mediante API: Recomendación, Chatbot y Procesamiento de Lenguaje Natural
La capa de inteligencia artificial de la plataforma se implementa mediante la integración de servicios externos de IA a través de API, sin requerir el entrenamiento de modelos propios. Esta capa contempla tres funcionalidades diferenciadas: un motor de recomendación de prendas, que segmenta el catálogo a partir de las preferencias explícitamente declaradas o inferidas del cliente (por ejemplo, tipo de tela, color o temporada), reduciendo la necesidad de navegar manualmente por catálogos extensos; un asistente conversacional o chatbot, de carácter opcional dentro del alcance del proyecto, orientado a resolver consultas frecuentes; y un módulo de procesamiento de lenguaje natural (NLP) aplicado a comandos de voz, que permite a un usuario formular una consulta hablada (por ejemplo, una búsqueda de producto o la solicitud de un reporte administrativo) para que el sistema la traduzca en una instrucción estructurada ejecutable contra la base de datos, siguiendo un esquema similar al de los denominados reportes generativos.

#### Infraestructura Cloud, API REST y Restricciones sobre Frameworks de E-Commerce Preconstruidos
El despliegue de la plataforma se realiza obligatoriamente sobre infraestructura en la nube, quedando explícitamente excluido el uso de entornos de ejecución local (localhost) como entrega final, contemplado### Requisitos Funcionales

#### Módulo: Autenticación y Seguridad
*   **RF01:** Permitir el auto-registro de clientes en la plataforma web o móvil.
*   **RF02:** Autenticar usuarios con tokens seguros JWT (JSON Web Tokens).
*   **RF03:** Recuperar credenciales de acceso enviando enlaces temporales vía correo electrónico.
*   **RF04:** Bloquear cuentas de forma temporal tras 5 intentos fallidos de inicio de sesión.
*   **RF05:** Crear, editar y dar de baja cuentas de personal administrativo.
*   **RF06:** Gestionar roles (Superadmin, Encargado, Cajero, Cliente) y sus respectivos accesos.
*   **RF07:** Auditar accesos registrando el historial de ingresos de empleados.

#### Módulo: Sucursales y Temporadas
*   **RF08:** Registrar múltiples sucursales con dirección geográfica y datos de contacto.
*   **RF09:** Asignar encargados exclusivos a cada sucursal física.
*   **RF10:** Desactivar de forma temporal operaciones en una sucursal específica.
*   **RF11:** Permitir al encargado de tienda habilitar o suspender la atención de reservas.
*   **RF12:** Configurar temporadas comerciales (Primavera, Verano, Otoño, Invierno).
*   **RF13:** Asociar productos a colecciones temporales de moda.
*   **RF14:** Parametrizar catálogo de colores (código HEX y nombre).
*   **RF15:** Registrar catálogo de tallas según categorías de prendas.

#### Módulo: Gestión del Catálogo de Ropa
*   **RF16:** Registrar prendas base (nombre, descripción, categoría, precio de venta).
*   **RF17:** Crear variantes de prendas asociando combinaciones de talla y color.
*   **RF18:** Asignar un código de SKU único a cada variante física del producto.
*   **RF19:** Subir imágenes ilustrativas de variantes desde el panel del administrador.
*   **RF20:** Ocultar prendas del catálogo público de manera temporal.
*   **RF21:** Aplicar descuentos y promociones en porcentajes a prendas seleccionadas.
*   **RF22:** Agrupar variantes en una única vista unificada para el catálogo del cliente.

#### Módulo: Gestión de Proveedores e Ingreso de Mercadería
*   **RF23:** Registrar proveedores de ropa con información de contacto y NIT.
*   **RF24:** Vincular variantes del catálogo con su respectivo proveedor de origen.
*   **RF25:** Generar registros de órdenes de compra destinadas a proveedores.
*   **RF26:** Registrar la entrada física de mercadería y actualizar las existencias.
*   **RF27:** Calcular el costo del inventario utilizando el método de **promedio ponderado**.

#### Módulo: Gestión de Inventario
*   **RF28:** Controlar y reportar las existencias físicas en tiempo real de forma independiente por sucursal.
*   **RF29:** Configurar alertas de stock mínimo para evitar desabastecimiento.
*   **RF30:** Notificar al administrador en su panel cuando el stock cruce el límite mínimo.
*   **RF31:** Establecer límites de stock máximo por variante.
*   **RF32:** Descontar existencias físicas tras registrarse una compra digital.
*   **RF33:** Restar lógico (bloquear existencias) al programarse una reserva física temporal.
*   **RF34:** Registrar la transferencia física de mercadería de una sucursal origen a otra destino.
*   **RF35:** Liberar el stock bloqueado automáticamente al cancelarse una reserva de prendas.

#### Módulo: Consultas y Filtros (Cliente)
*   **RF36:** Mostrar el catálogo público de prendas en la aplicación móvil de clientes.
*   **RF37:** Filtrar prendas por rango de precio, color, talla y temporada.
*   **RF38:** Buscar prendas introduciendo caracteres de texto en el buscador.
*   **RF39:** Mostrar disponibilidad por variantes en las distintas sucursales.
*   **RF40:** Agregar prendas al listado de favoritos del cliente.
*   **RF41:** Habilitar vista responsive en tabletas y pantallas de computadoras.
*   **RF42:** Capturar voz del usuario para realizar búsquedas (Móvil).
*   **RF43:** Traducir comando de voz a filtros utilizando Procesamiento de Lenguaje Natural (NLP).

#### Módulo: Vestidor Virtual (RA)
*   **RF44:** Acceder a la cámara en tiempo real desde la aplicación de Flutter.
*   **RF45:** Solicitar confirmación de permisos del sistema operativo para uso de cámara.
*   **RF46:** Superponer la imagen virtual de la prenda seleccionada sobre la silueta humana captada.
*   **RF47:** Cambiar la variante de color de la prenda en el vestidor virtual con un tap.
*   **RF48:** Capturar y guardar en la galería del móvil fotos de la simulación del vestidor.

#### Módulo: Reservas de Prendas
*   **RF49:** Seleccionar múltiples variantes de prendas en una canasta de reserva de prueba.
*   **RF50:** Elegir la sucursal física donde se acudirá a probar la ropa.
*   **RF51:** Validar el stock antes de permitir reservar las prendas seleccionadas.
*   **RF52:** Programar fecha y horario de visita en rangos de atención permitidos.
*   **RF53:** Registrar la reserva en el buzón de la sucursal seleccionada.
*   **RF54:** Visualizar reservas del día desde el panel del encargado.
*   **RF55:** Cambiar el estado de la reserva a "Lista" tras apartar la ropa físicamente.
*   **RF56:** Permitir la cancelación manual de reservas por el cliente.

#### Módulo: Carrito y Checkout Digital
*   **RF57:** Agregar variantes del catálogo al carrito digital del cliente.
*   **RF58:** Calcular subtotales, recargo por envío (si aplica) y total a pagar.
*   **RF59:** Validar stock una última vez antes de procesar el pago.
*   **RF60:** Seleccionar modalidad de entrega: Envío a Domicilio o Retiro en Tienda.
*   **RF61:** Procesar transacciones digitales mediante la pasarela Stripe (Modo Prueba).
*   **RF62:** Guardar estado de la transacción y generar orden de compra.
*   **RF63:** Emitir y enviar comprobante de pago digital al correo del cliente.

#### Módulo: Punto de Venta (POS Presencial)
*   **RF64:** Buscar reservas en el sistema ingresando el ID de reserva del cliente en tienda.
*   **RF65:** Facturar prendas de la reserva tras la prueba física en vestidor presencial.
*   **RF66:** Añadir otros artículos adicionales del catálogo directamente en caja.
*   **RF67:** Procesar transacciones en caja registrando pagos en efectivo o tarjeta física.
*   **RF68:** Generar la factura oficial y emitir el ticket de venta.
*   **RF69:** Registrar cambios de tallas o devoluciones directas en tienda.

#### Módulo: Envíos (Delivery)
*   **RF70:** Capturar la dirección del domicilio de entrega.
*   **RF71:** Calcular el recargo de envío según el método seleccionado o zona (distancia).
*   **RF72:** Mostrar pedidos pendientes de despacho al personal logístico.
*   **RF73:** Cambiar el estado de envío a "En camino" al despachar el pedido.
*   **RF74:** Permitir al cliente rastrear el estado logístico del pedido.
*   **RF75:** Confirmar estado como "Entregado" y cerrar ciclo de compra.

#### Módulo: Inteligencia Artificial
*   **RF76:** Registrar el comportamiento de navegación e historial de compras del cliente.
*   **RF77:** Recomendar prendas personalizadas en el inicio de la app según perfil.
*   **RF78:** Sugerir alternativas de prendas similares en caso de falta de existencias.
*   **RF79:** Disponer de un chatbot integrado en la aplicación móvil y web.
*   **RF80:** Configurar el chatbot para responder preguntas recurrentes sobre la tienda.

#### Módulo: Reportes y Dashboards
*   **RF81:** Presentar gráficos dinámicos de ventas agregadas a nivel global.
*   **RF82:** Filtrar estadísticas del dashboard por sucursal.
*   **RF83:** Reportar las ventas consolidadas por temporada de catálogo.
*   **RF84:** Reportar valoración monetaria del inventario general.
*   **RF85:** Descargar listados e informes de ventas en hojas de cálculo (CSV).
*   **RF86:** Capturar voz del administrador en la app móvil para consultas de reportes.
*   **RF87:** Generar gráficos estadísticos en pantalla interpretando comandos de voz del administrador.

#### Módulo: Notificaciones
*   **RF88:** Enviar correos de confirmación al agendar reservas.
*   **RF89:** Notificar por SMS o push al cliente cuando su pedido digital sea enviado.
*   **RF90:** Mostrar pantallas amigables de error evitando revelar trazas de código al usuario final.

---

### Requisitos No Funcionales

*   **RNF01 (Seguridad):** Las contraseñas en la base de datos deben encriptarse usando algoritmos de hash seguros (BCrypt/Argon2).
*   **RNF02 (Rendimiento):** Las respuestas del catálogo de prendas deben demorar menos de 1.5 segundos bajo cargas normales de usuarios.
*   **RNF03 (Escalabilidad):** La estructura del base de datos debe admitir la adición ilimitada de nuevas sucursales sin requerir refactorización del código.
*   **RNF04 (Usabilidad):** Las interfaces deben ser intuitivas y adaptables a escritorio, tablet y celular.
*   **RNF05 (Mantenibilidad):** El código del backend FastAPI debe organizarse siguiendo un patrón de arquitectura por capas (controladores, servicios, repositorios).
*   **RNF06 (Compatibilidad):** La aplicación de Flutter debe ser compatible con versiones de Android 8.0+ e iOS 13+.
*   **RNF07 (Seguridad Transaccional):** Toda transacción de pago digital debe utilizar cifrado TLS 1.3 y tokens no reutilizables provistos por Stripe.
*   **RNF08 (Disponibilidad / Despliegue):** El sistema debe estar desplegado en producción en servidores de la nube (GCP) con acceso mediante HTTPS público.
*   **RNF09 (Restricción Tecnológica):** Queda prohibido el uso de CMS o frameworks de comercio electrónico preconstruidos como Shopify, Magento o WooCommerce.
*   **RNF10 (Metodología):** El ciclo de desarrollo de software debe regirse bajo las disciplinas del Proceso Unificado de Desarrollo de Software (PUDS) dividido en 3 iteraciones.
*   **RNF11 (Modelado):** Los diagramas estáticos y dinámicos del sistema deben modelarse bajo el estándar de notación UML 2.5+.
*   **RNF12 (Control de Versiones):** El código del proyecto debe estar gestionado en repositorios de GitHub con ramas separadas y despliegues automatizados hacia Google Cloud.

---

## Parte II – Proceso de Desarrollo

### Captura de requisitos

#### Identificación de actores y casos de uso

##### Actores

Se distinguen tres grupos de actores, conforme al modelado UML: los **actores humanos primarios** (personas que inician los casos de uso principales), los **actores humanos de apoyo** (participan en fases concretas de un proceso) y los **actores del sistema / externos** (servicios o disparadores automáticos que interactúan con la plataforma sin intervención humana directa). Esta separación es la que se usa habitualmente al modelar plataformas de comercio electrónico, donde parte del comportamiento la disparan servicios externos (pasarela de pago, IA) o el propio paso del tiempo.

**A. Actores humanos primarios**

1. **Visitante (usuario anónimo, no autenticado):** persona que navega el sitio web o la app sin haber iniciado sesión. Puede consultar el catálogo público y las fichas de producto. Para reservar, comprar, marcar favoritos o usar el vestidor virtual debe registrarse o iniciar sesión (se convierte en Cliente). Es un actor obligatorio en cualquier e-commerce: la mayor parte del tráfico de una tienda en línea proviene de visitantes que aún no tienen cuenta.
2. **Cliente:** persona registrada que consulta y filtra el catálogo, usa el vestidor virtual, agenda reservas, arma el carrito, paga por pasarela, rastrea sus envíos y consulta su historial de pedidos. Accede tanto por la app móvil como por el sitio web.
3. **Superadmin (Administrador del sistema):** posee los mayores privilegios. Gestiona usuarios y roles, sucursales, catálogo (categorías, tallas, colores, temporadas), proveedores, empleados, parámetros del inventario y consulta la bitácora de auditoría y los dashboards globales. Es el único que da de alta a otros miembros del personal.
4. **Encargado de sucursal:** responsable de la operación de una sucursal. Gestiona la disponibilidad y los movimientos de inventario de su tienda, registra ingresos de mercadería, habilita o suspende la atención de reservas, consulta y prepara las reservas del día (marcarlas como "Lista") y confirma la recepción del cliente.
5. **Cajero:** registra los cobros presenciales en el punto de caja físico (efectivo o tarjeta), factura las prendas de una reserva tras la prueba en vestidor, añade artículos adicionales en caja, emite el ticket/comprobante y registra cambios o devoluciones directas en tienda.
6. **Proveedor:** empresa o persona que abastece de ropa a la cadena. Se registra en el sistema con su NIT y datos de contacto; sus prendas se vinculan a las variantes del catálogo y se referencian en las órdenes de compra / ingresos de mercadería.

**B. Actores humanos de apoyo**

7. **Repartidor (personal de reparto / delivery):** persona que retira el pedido en la sucursal y lo entrega en el domicilio del cliente. Consulta los pedidos pendientes de despacho, cambia el estado del envío ("En camino", "Entregado") y su remuneración se calcula por distancia recorrida (tarifa por anillos/kilómetro). *(Participa a partir del Ciclo 3, Módulo de Envíos.)*

**C. Actores del sistema / externos**

8. **Pasarela de pago (Stripe / PayPal):** sistema externo que autoriza y confirma las transacciones de las compras digitales, devolviendo un token no reutilizable y el resultado del cobro. La plataforma nunca almacena datos de tarjeta: delega esa responsabilidad en la pasarela (cumplimiento PCI DSS). Es un actor porque el flujo de checkout no se completa hasta que la pasarela responde.
9. **Servicio de Inteligencia Artificial (API externa de IA):** servicio externo consumido por API que provee la recomendación de prendas/tallas a partir del historial del cliente, la interpretación de comandos de voz (NLP) para búsquedas y reportes generativos, y, opcionalmente, el chatbot de ayuda. No se entrenan modelos propios.
10. **Servicio de correo electrónico (SMTP):** sistema externo que entrega los correos de la plataforma: enlace de recuperación de contraseña (5 min), confirmación de reservas y comprobante de pago digital.
11. **Reloj del sistema / Temporizador (actor "Tiempo"):** actor no humano que dispara los casos de uso ejecutados por vencimiento de un plazo, sin que nadie los solicite: expiración del token de recuperación (5 min) y del JWT (60 min), cierre de sesión por inactividad (15 min), liberación automática del stock bloqueado al vencer una reserva y actualización automática del inventario (triggers del sistema).

##### Lista maestra de casos de uso (40 CU)

La plataforma opera **tienda física formal + tienda online** de forma simultánea; por eso el
backlog cubre tanto la venta presencial en caja (POS, arqueo, factura/nota de entrega con
IVA 13 % y código de control) como la venta digital (carrito, pasarela, envío). Los reportes y
CRUD granulares se agrupan en un solo caso de uso cuando comparten actor y flujo.

**Paquete 1 — `seguridad_y_usuarios`**
* **CU01:** Iniciar sesión en la plataforma (cliente, administrador, encargado, cajero)
* **CU02:** Cerrar sesión activa
* **CU03:** Recuperar credenciales de acceso (enlace temporal por correo, 5 min)
* **CU04:** Auto-registro de cliente en la plataforma
* **CU05:** Gestionar perfiles, roles y clientes (CRUD de personal interno y de clientes)
* **CU36:** Consultar bitácora de auditoría del sistema

**Paquete 2 — `catalogo_y_tiendas`**
* **CU06:** Gestionar sucursales de la cadena (alta, edición, desactivación)
* **CU07:** Gestionar catálogo de prendas (categorías, tallas, colores multivaluados, temporadas, variantes + SKU)
* **CU09:** Gestionar empleados de sucursal (cajeros y encargados)
* **CU11:** Consultar catálogo de prendas (listado + búsqueda por texto + filtro por categoría)
* **CU12:** Buscar y filtrar el catálogo por criterios múltiples (precio, talla, color) y consultar disponibilidad física por sucursal
* **CU13:** Gestionar promociones: cupones de descuento y ofertas de temporada
* **CU14:** Gestionar lista de deseos (wishlist) y reseñas de prendas del cliente

**Paquete 3 — `inventario_y_proveedores`**
* **CU08:** Gestionar proveedores de mercadería
* **CU10:** Registrar compras e ingresos de mercadería de proveedores (costo unitario del lote)
* **CU37:** Consultar valoración de inventario / capital invertido (costo **promedio ponderado**)
* **CU38:** Gestionar ajustes de inventario (mermas, daños, pérdidas)
* **CU15:** Gestionar inventario general y transferencias entre sucursales (+ actualización automática por trigger)
* **CU16:** Configurar y notificar alertas de stock (mínimo/máximo)

**Paquete 4 — `ventas_y_pagos`**
* **CU17:** Gestionar carrito de compra digital (bloqueo automático si existencia = 0)
* **CU18:** Procesar venta / checkout con herencia de medios de pago (Efectivo, Tarjeta, QR, Crédito)
* **CU19:** Procesar venta presencial (directa) en caja (POS)
* **CU20:** Emitir comprobante: factura y nota de entrega (IVA 13 %, código de control)
* **CU21:** Generar cotización
* **CU22:** Gestionar devoluciones y cambios de prendas
* **CU23:** Gestionar arqueo de caja (apertura y cierre diario del cajero)
* **CU24:** Consultar historial de compras (cliente)
* **CU25:** Convertir una reserva en venta confirmada

**Paquete 5 — `reservas_y_citas`**
* **CU26:** Agendar reserva de prendas para prueba física
* **CU27:** Gestionar bandeja de reservas entrantes (preparar / atender)
* **CU28:** Cancelar reserva de prendas (libera el stock bloqueado)

**Paquete 6 — `envios_y_logistica`**
* **CU29:** Gestionar envíos a domicilio (Delivery), despacho y método de envío / recojo en sucursal
* **CU30:** Consultar y rastrear el estado de un pedido o envío
* **CU31:** Gestionar zonas de cobertura y tarifas de envío (anillos / km)

**Paquete 7 — `inteligente_y_analitica`**
* **CU32:** Realizar prueba de prenda en Vestidor Virtual (Realidad Aumentada) y guardar capturas
* **CU33:** Solicitar recomendaciones de prendas o tallas personalizadas (IA) + chatbot asistente (opcional)
* **CU34:** Buscar prendas en el catálogo mediante comandos de voz (NLP)
* **CU35:** Generar reportes gerenciales (kardex, más vendidos, ingresos por sucursal, rendimiento de cajeros; export PDF/CSV; por comando de voz)
* **CU39:** Consultar Dashboard de ventas e inventario global

**Paquete 8 — `notificaciones`**
* **CU40:** Notificar en tiempo real el estado de una reserva o pedido (push) y enviar comprobantes / confirmaciones por correo

> **Numeración canónica.** Esta lista de **40 casos de uso** es la **única numeración
> oficial** del proyecto. Todos los demás documentos (`PaquetesUML.md`, `Ciclo1.md`,
> `BaseDeDatos.md`) usan estos mismos números. El archivo `Listado_General_Casos_Uso.md`
> queda **obsoleto**; su contenido se absorbió aquí y el mapa de equivalencias está en
> `Ciclo1.md` §6.3.
>
> **Alcance por ciclo.** **Ciclo 1:** CU01–CU11, CU36, CU37, CU38 (14 CU).
> **Ciclo 2:** CU12–CU24. **Ciclo 3:** CU25–CU35, CU39, CU40.
>
> **Diferimiento de la consulta de catálogo del cliente.** En el **Ciclo 1** se implementa
> **CU11** en su forma básica: el cliente (y el visitante anónimo) ve el listado de prendas
> visibles con búsqueda por texto y filtro por categoría, en web y móvil. El **filtrado
> avanzado por precio/talla/color y la disponibilidad por sucursal (CU12)** requieren stock
> cargado por sucursal y una interfaz de filtros más rica, por lo que se difieren al **Ciclo 2**.

---

#### Priorizar casos de uso

| ID | Caso de uso | Paquete | Móvil | Web | Prioridad | Ciclo |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **CU01** | Iniciar sesión en la plataforma (cliente y personal) | seguridad_y_usuarios | X | X | Alta | Ciclo 1 |
| **CU02** | Cerrar sesión activa | seguridad_y_usuarios | X | X | Alta | Ciclo 1 |
| **CU03** | Recuperar credenciales de acceso (enlace por correo, 5 min) | seguridad_y_usuarios | X | X | Media | Ciclo 1 |
| **CU04** | Auto-registro de cliente en la plataforma | seguridad_y_usuarios | X | X | Alta | Ciclo 1 |
| **CU05** | Gestionar perfiles, roles y clientes | seguridad_y_usuarios | | X | Alta | Ciclo 1 |
| **CU06** | Gestionar sucursales de la cadena | catalogo_y_tiendas | | X | Alta | Ciclo 1 |
| **CU07** | Gestionar catálogo de prendas (categorías, tallas, colores multivaluados, temporadas, variantes+SKU) | catalogo_y_tiendas | | X | Alta | Ciclo 1 |
| **CU08** | Gestionar proveedores de mercadería | inventario_y_proveedores | | X | Media | Ciclo 1 |
| **CU09** | Gestionar empleados de sucursal (cajeros y encargados) | catalogo_y_tiendas | | X | Media | Ciclo 1 |
| **CU10** | Registrar compras e ingresos de mercadería de proveedores | inventario_y_proveedores | | X | Media | Ciclo 1 |
| **CU11** | Consultar catálogo de prendas (listado + búsqueda por texto y filtro por categoría) | catalogo_y_tiendas | X | X | Alta | Ciclo 1 |
| **CU37** | Consultar valoración de inventario / capital invertido (costo promedio ponderado) | inventario_y_proveedores | | X | Alta | Ciclo 1 |
| **CU38** | Gestionar ajustes de inventario (mermas, daños, pérdidas) | inventario_y_proveedores | | X | Media | Ciclo 1 |
| **CU36** | Consultar bitácora de auditoría del sistema | seguridad_y_usuarios | | X | Media | Ciclo 1 |
| **CU12** | Buscar y filtrar catálogo (precio, talla, color) + disponibilidad por sucursal | catalogo_y_tiendas | X | X | Alta | Ciclo 2 |
| **CU13** | Gestionar promociones: cupones y ofertas de temporada | catalogo_y_tiendas | | X | Media | Ciclo 2 |
| **CU14** | Gestionar wishlist y reseñas de prendas (cliente) | catalogo_y_tiendas | X | X | Baja | Ciclo 2 |
| **CU15** | Gestionar inventario general y transferencias entre sucursales (+ trigger) | inventario_y_proveedores | | X | Alta | Ciclo 2 |
| **CU16** | Configurar y notificar alertas de stock (mínimo/máximo) | inventario_y_proveedores | | X | Media | Ciclo 2 |
| **CU17** | Gestionar carrito de compra digital (bloqueo si existencia = 0) | ventas_y_pagos | X | X | Alta | Ciclo 2 |
| **CU18** | Procesar venta / checkout con herencia de medios de pago (Efectivo, Tarjeta, QR, Crédito) | ventas_y_pagos | X | X | Alta | Ciclo 2 |
| **CU19** | Procesar venta presencial (directa) en caja (POS) | ventas_y_pagos | | X | Alta | Ciclo 2 |
| **CU20** | Emitir factura y nota de entrega (IVA 13 %, código de control) | ventas_y_pagos | X | X | Alta | Ciclo 2 |
| **CU21** | Generar cotización | ventas_y_pagos | | X | Baja | Ciclo 2 |
| **CU22** | Gestionar devoluciones y cambios de prendas | ventas_y_pagos | | X | Media | Ciclo 2 |
| **CU23** | Gestionar arqueo de caja (apertura y cierre diario del cajero) | ventas_y_pagos | | X | Alta | Ciclo 2 |
| **CU24** | Consultar historial de compras (cliente) | ventas_y_pagos | X | X | Media | Ciclo 2 |
| **CU25** | Convertir una reserva en venta confirmada | ventas_y_pagos | | X | Alta | Ciclo 3 |
| **CU26** | Agendar reserva de prendas para prueba física | reservas_y_citas | X | | Alta | Ciclo 3 |
| **CU27** | Gestionar bandeja de reservas entrantes (preparar / atender) | reservas_y_citas | | X | Alta | Ciclo 3 |
| **CU28** | Cancelar reserva de prendas (libera stock bloqueado) | reservas_y_citas | X | X | Alta | Ciclo 3 |
| **CU29** | Gestionar envíos/despacho (Delivery) y método de envío / recojo en sucursal | envios_y_logistica | | X | Media | Ciclo 3 |
| **CU30** | Consultar y rastrear estado de un pedido o envío | envios_y_logistica | X | X | Media | Ciclo 3 |
| **CU31** | Gestionar zonas de cobertura y tarifas de envío (anillos / km) | envios_y_logistica | | X | Media | Ciclo 3 |
| **CU32** | Prueba en Vestidor Virtual (RA) y guardar capturas | inteligente_y_analitica | X | | Alta | Ciclo 3 |
| **CU33** | Recomendaciones de prendas/tallas (IA) + chatbot asistente (opcional) | inteligente_y_analitica | X | X | Media | Ciclo 3 |
| **CU34** | Buscar prendas mediante comandos de voz (NLP) | inteligente_y_analitica | X | | Media | Ciclo 3 |
| **CU35** | Generar reportes gerenciales (kardex, más vendidos, ingresos/sucursal, rendimiento de cajeros; PDF/CSV; por voz) | inteligente_y_analitica | X | X | Media | Ciclo 3 |
| **CU39** | Consultar Dashboard de ventas e inventario global | inteligente_y_analitica | | X | Media | Ciclo 3 |
| **CU40** | Notificar estado en tiempo real (push) y enviar comprobantes / confirmaciones por correo | notificaciones | X | | Media | Ciclo 3 |
---

#### Detallar casos de uso
*(Sección reservada para el desarrollo detallado de la especificación de casos de uso en las siguientes fases del proyecto)*

---

### Análisis
*(Sección reservada para diagramas de análisis, diagramas de clases de análisis y especificaciones del modelo conceptual)*

---

### Diseño
*(Sección reservada para la arquitectura de software, diagramas de secuencia de diseño, diagramas de clases de diseño y diseño físico de la base de datos)*

---

### Implementación
*(Sección reservada para la descripción de los módulos de software implementados, código fuente estructurado y configuraciones de despliegue)*

---

### Pruebas
*(Sección reservada para el registro y resultados de las pruebas unitarias, de integración y de aceptación de usuario)*

---

## Bibliografía

* Azuma, R. T. (1997). *A Survey of Augmented Reality*. Presence: Teleoperators and Virtual Environments.
* Chase, R. B., Jacobs, F. R., & Aquilano, N. J. (2018). *Administración de operaciones: producción y cadena de suministros*. McGraw-Hill.
* Jacobson, I., Booch, G., & Rumbaugh, J. (2000). *El Proceso Unificado de Desarrollo de Software*. Addison Wesley / Pearson Educación.
* Laudon, K. C., & Traver, C. G. (2021). *E-commerce: Business, Technology, Society*. Pearson.
* Ries, E. (2011). *The Lean Startup*. Crown Business.
* Rumbaugh, J., Jacobson, I., & Booch, G. (2007). *El Lenguaje Unificado de Modelado, UML: Manual de referencia*. Pearson Educación.
* Actualidad E-commerce. (2019). *Cómo funciona Alibaba, ¿Qué es y cómo obtiene sus beneficios?*
* Libélula. (2026). *libélula.bo | Pasarela multicanal de pagos y facturación*.
* Correo del Sur. (2019). *Yaigo Delivery transaccionó 30 mil dólares en dos meses*.
* Diseño de Páginas Web Santa Cruz. (2025). *Pasarelas de pago en Bolivia: comparativa entre Livees y Libélula*.
* UMSA. (s.f.). *Explotación y precarización del trabajo en las plataformas de delivery*.
* Feedough. (2025). *Alibaba Business Model | How Does Alibaba Make Money?*
