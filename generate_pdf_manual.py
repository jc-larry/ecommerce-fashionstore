"""Script para generar el documento PDF ejecutivo con todos los actores, credenciales, portales y casos de uso de FashionStore."""
import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

def generate_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor('#1E293B')   # Slate 800
    accent_color = colors.HexColor('#0284C7')    # Sky 600
    success_color = colors.HexColor('#16A34A')   # Green 600
    light_bg = colors.HexColor('#F8FAFC')        # Slate 50
    header_bg = colors.HexColor('#0F172A')       # Slate 900
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=0,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=accent_color,
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1E293B')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0369A1')
    )

    story = []

    # ENCABEZADO
    story.append(Paragraph("FASHIONSTORE S.R.L. — GUÍA MAESTRA DE ACTORES, PORTALES Y ACCESOS", title_style))
    story.append(Paragraph("Sistemas de Información II · Metodología PUDS / UML · Santa Cruz de la Sierra, Bolivia", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=0, spaceAfter=10))

    # 1. TABLA DE USUARIOS Y CREDENCIALES
    story.append(Paragraph("1. Tabla Maestra de Cuentas, Credenciales y Accesos por Rol", h1_style))
    story.append(Paragraph("A continuación se detallan las cuentas operativas configuradas para cada actor del sistema, con su respectiva contraseña predeterminada, rol de seguridad y enlace de acceso:", body_style))

    users_data = [
        [
            Paragraph("<b>Actor / Rol</b>", table_header_style),
            Paragraph("<b>Correo Electrónico</b>", table_header_style),
            Paragraph("<b>Contraseña</b>", table_header_style),
            Paragraph("<b>Sucursal / Entidad</b>", table_header_style),
            Paragraph("<b>Ruta / Portal Asignado</b>", table_header_style)
        ],
        [
            Paragraph("<b>Administrador General</b><br/>(SUPERADMIN)", table_cell_bold),
            Paragraph("admin@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Todas (Oficina Central)", table_cell_style),
            Paragraph("<b>/admin/dashboard</b><br/>Panel Global, Kárdex, Auditoría", table_cell_style)
        ],
        [
            Paragraph("<b>Encargada Sucursal</b><br/>(ENCARGADO)", table_cell_bold),
            Paragraph("encargada.equipetrol@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Sucursal Equipetrol (Santa Cruz)", table_cell_style),
            Paragraph("<b>/admin/reservations-board</b><br/>Perchero Probador, Citas y Stock", table_cell_style)
        ],
        [
            Paragraph("<b>Encargada Sucursal</b><br/>(ENCARGADO)", table_cell_bold),
            Paragraph("encargada.ventura@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Sucursal Ventura Mall (Santa Cruz)", table_cell_style),
            Paragraph("<b>/admin/reservations-board</b><br/>Gestión de Vestidores y Citas", table_cell_style)
        ],
        [
            Paragraph("<b>Cajero de Tienda</b><br/>(CAJERO)", table_cell_bold),
            Paragraph("cajero.equipetrol@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Sucursal Equipetrol (Santa Cruz)", table_cell_style),
            Paragraph("<b>/admin/pos</b> & <b>/admin/shifts</b><br/>Punto de Venta y Arqueo de Caja", table_cell_style)
        ],
        [
            Paragraph("<b>Cajera de Tienda</b><br/>(CAJERO)", table_cell_bold),
            Paragraph("cajera.ventura@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Sucursal Ventura Mall (Santa Cruz)", table_cell_style),
            Paragraph("<b>/admin/pos</b> & <b>/admin/shifts</b><br/>Facturación y Cobro de Saldos", table_cell_style)
        ],
        [
            Paragraph("<b>Proveedor Textil</b><br/>(PROVEEDOR)", table_cell_bold),
            Paragraph("proveedor.textiles@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Textiles & Hilados Andinos S.R.L.", table_cell_style),
            Paragraph("<b>/proveedor</b><br/>Portal de Proveedor (Ofertas, Stock, OC)", table_cell_style)
        ],
        [
            Paragraph("<b>Repartidor / Conductor</b><br/>(REPARTIDOR)", table_cell_bold),
            Paragraph("repartidor.moto@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("Delivery Santa Cruz (1° al 4° Anillo)", table_cell_style),
            Paragraph("<b>/repartidor</b><br/>Portal de Repartidor (Rutas, Mapa, GPS)", table_cell_style)
        ],
        [
            Paragraph("<b>Cliente Final</b><br/>(CLIENTE)", table_cell_bold),
            Paragraph("cliente@fashionstore.com", code_style),
            Paragraph("Password123!", code_style),
            Paragraph("E-Commerce / Tienda Virtual", table_cell_style),
            Paragraph("<b>/tienda</b> | <b>/tienda/vestidor</b><br/>Probador Virtual, Reservas, PayPal", table_cell_style)
        ]
    ]

    t_users = Table(users_data, colWidths=[110, 140, 75, 105, 110])
    t_users.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_users)
    story.append(Spacer(1, 12))

    # 2. DESCRIPCIÓN DE PORTALES Y FLUJOS POR ACTOR
    story.append(Paragraph("2. Módulos y Funcionalidades por Actor", h1_style))

    story.append(Paragraph("<b>A. Portal de Repartidor (/repartidor) — Rol REPARTIDOR (CU05, CU29, CU30)</b>", h2_style))
    story.append(Paragraph("• <b>Indicadores en Vivo:</b> Total de entregas completadas en la jornada, kilómetros recorridos y honorarios devengados en Bolivianos (calculados a Bs. 1.99 por kilómetro).<br/>"
                           "• <b>Gestión de Despachos:</b> Bandeja de pedidos con filtros rápidos (<i>Por Recoger</i>, <i>En Ruta</i>, <i>Entregados</i>).<br/>"
                           "• <b>Mapa Satelital de Ruta:</b> Renderizado interactivo con georreferenciación de la sucursal de origen y el domicilio del cliente en Santa Cruz, con enlace directo para apertura en Google Maps / Waze.<br/>"
                           "• <b>Flujo Operativo de Estados:</b> 1. <i>Retirar en Sucursal</i> (DISPATCHED) → 2. <i>Iniciar Ruta / En Camino</i> (IN_TRANSIT) → 3. <i>Confirmar Entrega</i> (DELIVERED) o <i>Reportar Incidencia</i> (FAILED).<br/>"
                           "• <b>Contacto con Cliente:</b> Enlace instantáneo a llamada telefónica y chat de WhatsApp.", body_style))

    story.append(Paragraph("<b>B. Portal de Proveedor (/proveedor) — Rol PROVEEDOR (CU08, CU10)</b>", h2_style))
    story.append(Paragraph("• <b>Pestaña 'Mi Perfil':</b> Edición y actualización de datos de contacto (nombre de contacto, correo, teléfono y dirección física).<br/>"
                           "• <b>Pestaña 'Mis Productos':</b> Consulta en tiempo real del stock disponible por sucursal de las prendas suministradas por su empresa, sin acceso a información sensible o de costos del negocio.<br/>"
                           "• <b>Pestaña 'Mis Compras':</b> Historial completo de órdenes de compra emitidas al proveedor con estado de facturación.<br/>"
                           "• <b>Ofertas al Administrador:</b> Registro de nuevas propuestas de prendas con costos y stock sugerido, además de gestión de solicitudes de reposición vinculadas a sucursales de Santa Cruz.", body_style))

    story.append(Paragraph("<b>C. Tablero Kanban de Reservas y Probador — Rol ENCARGADO (/admin/reservations-board) (CU26, CU27, CU28)</b>", h2_style))
    story.append(Paragraph("• <b>Visibilidad de Seña Online:</b> Distintivo destacado para el operador que indica <i>'Seña 50% Pagada Online (Ref: PAYPAL / TARJETA)'</i> con el monto abonado y el saldo restante en caja.<br/>"
                           "• <b>Gestión de Citas:</b> Control de tolerancia de 15 minutos, reprogramación y transición de prendas (<i>Pendiente</i> → <i>Prendas en Perchero</i> → <i>Listo en Probador</i> → <i>Venta Concretada</i>).<br/>"
                           "• <b>Garantía de Stock:</b> Bloqueo automático de inventario por 48 horas tras el abono de la seña.", body_style))

    story.append(Paragraph("<b>D. Punto de Venta POS y Caja — Rol CAJERO (/admin/pos, /admin/shifts) (CU19, CU20, CU23)</b>", h2_style))
    story.append(Paragraph("• <b>Apertura y Arqueo de Caja:</b> Registro de fondo inicial, conteo al cierre y cálculo de diferencias.<br/>"
                           "• <b>Facturación con Deducción de Seña:</b> Al concretar una reserva, el sistema descuenta automáticamente el 50% abonado previamente y factura el saldo pendiente en efectivo, tarjeta o QR.", body_style))

    story.append(Paragraph("<b>E. Experiencia de Cliente — Rol CLIENTE (/tienda, /tienda/vestidor, /tienda/reservas)</b>", h2_style))
    story.append(Paragraph("• <b>Probador Virtual Biométrico (VTON):</b> Visualización de prendas amoldadas sobre fotografía o avatar con medidas anatómicas.<br/>"
                           "• <b>Simulador PayPal Sandbox:</b> Modal interactivo con conversión BOB/USD (T.C. 6.96), billetera simulada, animación de autorización bancaria y emisión inmediata de voucher de confirmación.<br/>"
                           "• <b>Facturación y Devoluciones (CU20, CU22):</b> Registro del ID de transacción PayPal en la factura para procesar reembolsos automáticos en caso de cambios o devoluciones.", body_style))

    story.append(Spacer(1, 10))

    # 3. MATRIZ PUDS / UML
    story.append(Paragraph("3. Matriz de Casos de Uso Implementados (Metodología PUDS / UML)", h1_style))
    
    cu_data = [
        [
            Paragraph("<b>CU</b>", table_header_style),
            Paragraph("<b>Nombre del Caso de Uso</b>", table_header_style),
            Paragraph("<b>Paquete</b>", table_header_style),
            Paragraph("<b>Actores</b>", table_header_style),
            Paragraph("<b>Estado de Verificación</b>", table_header_style)
        ],
        [Paragraph("CU05", table_cell_bold), Paragraph("Gestionar Repartidores de Delivery", table_cell_style), Paragraph("envios_y_logistica", table_cell_style), Paragraph("Admin, Repartidor", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU06", table_cell_bold), Paragraph("Gestionar Sucursales (Exclusivo Santa Cruz)", table_cell_style), Paragraph("catalogo_y_tiendas", table_cell_style), Paragraph("Admin General", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU08", table_cell_bold), Paragraph("Gestionar Proveedores y Ofertas de Prendas", table_cell_style), Paragraph("inventario_y_proveedores", table_cell_style), Paragraph("Admin, Proveedor", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU10", table_cell_bold), Paragraph("Registrar Ingreso de Mercadería por Sucursal", table_cell_style), Paragraph("inventario_y_proveedores", table_cell_style), Paragraph("Almacenero, Admin", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU18", table_cell_bold), Paragraph("Pasarela de Pagos (PayPal Sandbox, Tarjeta, QR)", table_cell_style), Paragraph("ventas_y_pagos", table_cell_style), Paragraph("Cliente, Cajero", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU20", table_cell_bold), Paragraph("Facturación Fiscal con QR y Código de Control", table_cell_style), Paragraph("ventas_y_pagos", table_cell_style), Paragraph("Cajero, Sistema", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU22", table_cell_bold), Paragraph("Devoluciones y Reembolsos a Pasarela PayPal", table_cell_style), Paragraph("ventas_y_pagos", table_cell_style), Paragraph("Encargado, Cajero", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU26", table_cell_bold), Paragraph("Reservar Prenda con Cobro de Seña del 50%", table_cell_style), Paragraph("reservas_y_citas", table_cell_style), Paragraph("Cliente", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU27", table_cell_bold), Paragraph("Monitoreo de Citas y Perchero de Probadores", table_cell_style), Paragraph("reservas_y_citas", table_cell_style), Paragraph("Encargada Tienda", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU29", table_cell_bold), Paragraph("Despacho y Auto-asignación de Repartidores", table_cell_style), Paragraph("envios_y_logistica", table_cell_style), Paragraph("Repartidor", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU30", table_cell_bold), Paragraph("Trazabilidad y Estados de Entrega en Mapa", table_cell_style), Paragraph("envios_y_logistica", table_cell_style), Paragraph("Repartidor, Cliente", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
        [Paragraph("CU32", table_cell_bold), Paragraph("Probador Virtual Biométrico con IA (VTON)", table_cell_style), Paragraph("inteligente_y_analitica", table_cell_style), Paragraph("Cliente", table_cell_style), Paragraph("<font color='#16A34A'><b>100% Verificado</b></font>", table_cell_style)],
    ]

    t_cu = Table(cu_data, colWidths=[40, 190, 110, 90, 110])
    t_cu.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_cu)
    story.append(Spacer(1, 14))

    # PIE DE DOCUMENTO
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceBefore=5, spaceAfter=8))
    story.append(Paragraph("<b>FashionStore S.R.L. · Santa Cruz de la Sierra, Bolivia</b> · Documento generado automáticamente para evaluación y auditoría.", subtitle_style))

    doc.build(story)
    print(f"[OK] Documento PDF generado exitosamente en: {output_filename}")

if __name__ == '__main__':
    out_path = os.path.abspath("MANUAL_ACTORES_Y_PORTALES_FASHIONSTORE.pdf")
    generate_pdf(out_path)
