import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURACIÓN DE LA BASE DE DATOS (TAX-ON) ---
def inicializar_bd():
    conn = sqlite3.connect("tax_on_system.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    
    # Tabla de Productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descripcion TEXT NOT NULL,
            unidades TEXT NOT NULL,
            precio_venta REAL NOT NULL,
            precio_compra REAL NOT NULL
        )
    """)
    
    # Tabla de Proformas (Encabezado con estado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proformas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_proforma TEXT UNIQUE,
            fecha TEXT,
            cliente TEXT,
            ruc_cliente TEXT,
            vendedor TEXT,
            subtotal REAL,
            descuento REAL,
            iva REAL,
            total REAL,
            ganancia_neta REAL,
            estado TEXT DEFAULT 'Pendiente'
        )
    """)
    
    # Asegurar compatibilidad si la tabla ya existía sin la columna estado
    cursor.execute("PRAGMA table_info(proformas)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'estado' not in columns:
        cursor.execute("ALTER TABLE proformas ADD COLUMN estado TEXT DEFAULT 'Pendiente'")
    
    # Tabla de Detalle de Proforma
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_proforma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_proforma TEXT,
            codigo TEXT,
            descripcion TEXT,
            unidades TEXT,
            cantidad REAL,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(nro_proforma) REFERENCES proformas(nro_proforma)
        )
    """)
    
    # Crear cuenta Administrador por defecto
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                       ("admin", "1234", "Administrador"))
    
    conn.commit()
    conn.close()

inicializar_bd()

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO ---
st.set_page_config(page_title="TAX-ON | Sistema de Cotizaciones", layout="wide")

# --- ENCABEZADO CON LOGOTIPO PEQUEÑO A LA IZQUIERDA ---
col_logo, col_texto = st.columns([1, 8])
with col_logo:
    try:
        img_logo = Image.open("logo_tax_on.jpg")
        st.image(img_logo, width=70)
    except Exception:
        st.warning("⚠️ Logo no encontrado")

with col_texto:
    st.markdown("### TAX-ON — Sistema de Cotizaciones y Control Financiero")

st.markdown("---")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.menu_actual = "Crear Cotización"

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.subheader("Iniciar Sesión en la plataforma TAX-ON")
    col1, col2 = st.columns([1, 2])
    with col1:
        username_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar a TAX-ON"):
            conn = sqlite3.connect("tax_on_system.db")
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE username = ? AND password = ?", (username_input, password_input))
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado:
                st.session_state.autenticado = True
                st.session_state.usuario = username_input
                st.session_state.rol = resultado[0]
                st.session_state.menu_actual = "Crear Cotización"
                st.success(f"¡Bienvenido a TAX-ON, {username_input}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
else:
    # --- MENÚ LATERAL FIJO ---
    st.sidebar.markdown("### 🏢 TAX-ON Panel")
    st.sidebar.write(f"Conectado: **{st.session_state.usuario}**")
    st.sidebar.write(f"Rol: **{st.session_state.rol}**")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Menú Principal")
    
    if st.sidebar.button("📝 Crear Cotización", use_container_width=True):
        st.session_state.menu_actual = "Crear Cotización"
        
    if st.session_state.rol == "Administrador":
        if st.sidebar.button("📋 Gestión de Cotizaciones", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Cotizaciones"
        if st.sidebar.button("📦 Gestión de Productos", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Productos"
        if st.sidebar.button("👥 Gestión de Usuarios", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Usuarios"
        if st.sidebar.button("📊 Reportes de Ganancias", use_container_width=True):
            st.session_state.menu_actual = "Reportes de Ganancias"
            
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.session_state.rol = None
        st.rerun()
        
    menu = st.session_state.menu_actual
        
    # --- GESTIÓN DE USUARIOS ---
    if menu == "Gestión de Usuarios" and st.session_state.rol == "Administrador":
        st.header("TAX-ON | Administración de Cuentas")
        with st.form("form_crear_usuario"):
            nuevo_user = st.text_input("Nombre de Usuario")
            nuevo_pass = st.text_input("Contraseña", type="password")
            nuevo_rol = st.selectbox("Rol del Usuario", ["Vendedor", "Administrador"])
            btn_crear = st.form_submit_button("Crear Cuenta en TAX-ON")
            
            if btn_crear:
                if nuevo_user and nuevo_pass:
                    try:
                        conn = sqlite3.connect("tax_on_system.db")
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                                       (nuevo_user, nuevo_pass, nuevo_rol))
                        conn.commit()
                        conn.close()
                        st.success(f"¡Usuario '{nuevo_user}' registrado con éxito!")
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya existe.")
                else:
                    st.warning("Completa todos los campos.")
                    
        st.subheader("Usuarios Registrados")
        conn = sqlite3.connect("tax_on_system.db")
        df_usuarios = pd.read_sql_query("SELECT id, username, rol FROM usuarios", conn)
        conn.close()
        st.dataframe(df_usuarios, use_container_width=True)

    # --- GESTIÓN DE PRODUCTOS ---
    elif menu == "Gestión de Productos" and st.session_state.rol == "Administrador":
        st.header("TAX-ON | Catálogo de Productos (Doble Precio y Unidades)")
        with st.form("form_producto"):
            col1, col2 = st.columns(2)
            with col1:
                codigo = st.text_input("Código de Producto (ej. PH03)")
                descripcion = st.text_area("Descripción (ej. WPC PANEL 160*23*2900mm)")
                unidades = st.selectbox("Unidades", ["Pcs", "Bundle", "Metros", "Unidades", "Rollos", "Cajas"])
            with col2:
                p_venta = st.number_input("Precio de Venta ($)", min_value=0.0, format="%.2f")
                p_compra = st.number_input("Precio de Compra / Costo ($)", min_value=0.0, format="%.2f")
                
            btn_guardar_prod = st.form_submit_button("Guardar Producto")
            
            if btn_guardar_prod:
                if codigo and descripcion:
                    conn = sqlite3.connect("tax_on_system.db")
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO productos (codigo, descripcion, unidades, precio_venta, precio_compra)
                            VALUES (?, ?, ?, ?, ?)
                        """, (codigo, descripcion, unidades, p_venta, p_compra))
                        conn.commit()
                        conn.close()
                        st.success(f"Producto '{codigo}' guardado correctamente.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Código y descripción obligatorios.")
                    
        st.subheader("Inventario Actual")
        conn = sqlite3.connect("tax_on_system.db")
        df_productos = pd.read_sql_query("SELECT id, codigo, descripcion, unidades, precio_venta, precio_compra FROM productos", conn)
        conn.close()
        st.dataframe(df_productos, use_container_width=True)

    # --- GESTIÓN DE COTIZACIONES (ESTADOS) ---
    elif menu == "Gestión de Cotizaciones" and st.session_state.rol == "Administrador":
        st.header("TAX-ON | Gestión de Estado de Cotizaciones")
        st.info("Aquí puedes revisar el estado de cada cotización emitida y actualizar si fue aceptada por el cliente.")
        
        conn = sqlite3.connect("tax_on_system.db")
        df_proformas = pd.read_sql_query("SELECT nro_proforma, fecha, cliente, ruc_cliente, vendedor, total, estado FROM proformas", conn)
        conn.close()
        
        if not df_proformas.empty:
            st.dataframe(df_proformas, use_container_width=True)
            
            st.markdown("### Actualizar Estado de Cotización")
            with st.form("form_actualizar_estado"):
                lista_nros = df_proformas['nro_proforma'].tolist()
                proforma_elegida = st.selectbox("Seleccione Nro. de Proforma", lista_nros)
                
                estado_actual_row = df_proformas[df_proformas['nro_proforma'] == proforma_elegida]['estado'].values[0]
                nuevo_estado = st.selectbox("Nuevo Estado", ["Pendiente", "Aceptada", "Rechazada"], index=["Pendiente", "Aceptada", "Rechazada"].index(estado_actual_row) if estado_actual_row in ["Pendiente", "Aceptada", "Rechazada"] else 0)
                
                btn_actualizar = st.form_submit_button("Actualizar Estado")
                
                if btn_actualizar:
                    conn = sqlite3.connect("tax_on_system.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE proformas SET estado = ? WHERE nro_proforma = ?", (nuevo_estado, proforma_elegida))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Cotización {proforma_elegida} actualizada a estado: **{nuevo_estado}**!")
                    st.rerun()
        else:
            st.info("No hay cotizaciones registradas aún.")

    # --- MÓDULO DE COTIZACIONES ---
    elif menu == "Crear Cotización":
        st.header("TAX-ON | Generador de Cotizaciones y Proformas")
        
        conn = sqlite3.connect("tax_on_system.db")
        df_inv = pd.read_sql_query("SELECT codigo, descripcion, unidades, precio_venta FROM productos", conn)
        conn.close()
        
        if df_inv.empty:
            st.warning("⚠️ No hay productos registrados en el sistema. El administrador debe agregarlos primero.")
        else:
            conn = sqlite3.connect("tax_on_system.db")
            cursor = conn.cursor()
            meses_es = {"01":"ENE", "02":"FEB", "03":"MAR", "04":"ABR", "05":"MAY", "06":"JUN", "07":"JUL", "08":"AGO", "09":"SEP", "10":"OCT", "11":"NOV", "12":"DIC"}
            now = datetime.now()
            anio_mes = f"{now.year}-{meses_es.get(now.strftime('%m'), 'OCT')}"
            
            cursor.execute("SELECT COUNT(*) FROM proformas WHERE nro_proforma LIKE ?", (f"{anio_mes}%",))
            count = cursor.fetchone()[0]
            nro_sugerido = f"{anio_mes}-{str(count + 1).zfill(3)}"
            conn.close()

            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            with col_c1:
                cliente = st.text_input("Nombre del Cliente", value="OSWALDO TOMALA ESPINOZA")
            with col_c2:
                ruc_cliente = st.text_input("RUC / Cédula del Cliente", value="0912345678001")
            with col_c3:
                nro_cotizacion = st.text_input("Nro. de Proforma", value=nro_sugerido)
            with col_c4:
                vendedor = st.text_input("Vendedor", value=st.session_state.usuario)
                
            st.markdown(f"**Fecha de Emisión:** {now.strftime('%Y-%m-%d')} | **Tipo de Documento:** Cotización de ventas estándar")
            st.markdown("---")
            st.subheader("Agregar Ítems a la Proforma")
            
            if 'carrito' not in st.session_state:
                st.session_state.carrito = []
                
            col_i1, col_i2, col_i3 = st.columns([2, 1, 1])
            with col_i1:
                prod_seleccionado = st.selectbox("Seleccionar Producto", df_inv['codigo'] + " - " + df_inv['descripcion'])
            with col_i2:
                cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
            with col_i3:
                codigo_sel = prod_seleccionado.split(" - ")[0]
                row_prod = df_inv[df_inv['codigo'] == codigo_sel].iloc[0]
                precio_sugerido = float(row_prod['precio_venta'])
                unidades_prod = row_prod['unidades']
                precio_unitario = st.number_input("Precio de Venta Unitario ($)", min_value=0.0, value=precio_sugerido, format="%.2f")
                
            if st.button("➕ Añadir a la Cotización"):
                desc_sel = row_prod['descripcion']
                subtotal_linea = cantidad * precio_unitario
                st.session_state.carrito.append({
                    "codigo": codigo_sel,
                    "descripcion": desc_sel,
                    "unidades": unidades_prod,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "subtotal": subtotal_linea
                })
                st.success("Ítem añadido correctamente.")
                
            if st.session_state.carrito:
                st.markdown("### Detalle de la Proforma")
                df_carrito = pd.DataFrame(st.session_state.carrito)
                st.dataframe(df_carrito, use_container_width=True)
                
                if st.button("🗑️ Vaciar Cotización"):
                    st.session_state.carrito = []
                    st.rerun()
                    
                st.markdown("---")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    descuento = st.number_input("Descuento Total ($)", min_value=0.0, value=0.0, format="%.2f")
                
                subtotal_acumulado = sum([item['subtotal'] for item in st.session_state.carrito])
                subtotal_con_desc = subtotal_acumulado - descuento
                iva = subtotal_con_desc * 0.15  # IVA 15%
                total_final = subtotal_con_desc + iva
                
                with col_t2:
                    st.markdown(f"#### Subtotal: ${subtotal_acumulado:.2f}")
                    st.markdown(f"#### Descuento: ${descuento:.2f}")
                    st.markdown(f"#### IVA (15%): ${iva:.2f}")
                    st.markdown(f"### TOTAL A PAGAR: ${total_final:.2f}")
                    
                if st.button("💾 Guardar y Generar PDF de la Proforma"):
                    if cliente:
                        conn = sqlite3.connect("tax_on_system.db")
                        cursor = conn.cursor()
                        try:
                            ganancia_total_proforma = 0
                            for item in st.session_state.carrito:
                                cursor.execute("SELECT precio_compra FROM productos WHERE codigo = ?", (item['codigo'],))
                                res_compra = cursor.fetchone()
                                costo_unitario = res_compra[0] if res_compra else 0
                                ganancia_total_proforma += (item['precio_unitario'] - costo_unitario) * item['cantidad']
                            
                            ganancia_neta_final = ganancia_total_proforma - descuento
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO proformas (nro_proforma, fecha, cliente, ruc_cliente, vendedor, subtotal, descuento, iva, total, ganancia_neta, estado)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')
                            """, (nro_cotizacion, now.strftime("%Y-%m-%d"), cliente, ruc_cliente, vendedor, subtotal_acumulado, descuento, iva, total_final, ganancia_neta_final))
                            
                            for item in st.session_state.carrito:
                                cursor.execute("""
                                    INSERT INTO detalle_proforma (nro_proforma, codigo, descripcion, unidades, cantidad, precio_unitario, subtotal)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (nro_cotizacion, item['codigo'], item['descripcion'], item['unidades'], item['cantidad'], item['precio_unitario'], item['subtotal']))
                                
                            conn.commit()
                            conn.close()
                            
                            nombre_archivo_pdf = f"{cliente.upper()} - {nro_cotizacion}.pdf"
                            doc = SimpleDocTemplate(nombre_archivo_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                            elementos = []
                            
                            styles = getSampleStyleSheet()
                            estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A2B4C"), spaceAfter=6)
                            estilo_sub = ParagraphStyle('SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#555555"))
                            
                            elementos.append(Paragraph("<b>TAX-ON — ASESORAMIENTO CONTABLE Y TRIBUTARIO</b>", estilo_titulo))
                            elementos.append(Paragraph("<b>Tipo de documento:</b> Cotización de ventas estándar", estilo_sub))
                            elementos.append(Paragraph(f"<b>Nro:</b> {nro_cotizacion}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Fecha:</b> {now.strftime('%Y-%m-%d')}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Cliente:</b> {cliente} | <b>RUC/Cédula:</b> {ruc_cliente}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Vendedor:</b> {vendedor}", estilo_sub))
                            elementos.append(Spacer(1, 15))
                            
                            data_tabla = [["Nro", "Código", "Descripción", "Unid.", "Cant.", "P. Venta", "Subtotal"]]
                            for idx, item in enumerate(st.session_state.carrito, start=1):
                                data_tabla.append([
                                    str(idx),
                                    item['codigo'],
                                    item['descripcion'],
                                    item['unidades'],
                                    f"{item['cantidad']:.2f}",
                                    f"${item['precio_unitario']:.3f}",
                                    f"${item['subtotal']:.3f}"
                                ])
                                
                            t = Table(data_tabla, colWidths=[30, 55, 205, 45, 45, 60, 70])
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A2B4C")),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0,0), (-1,-1), 8),
                                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ]))
                            elementos.append(t)
                            elementos.append(Spacer(1, 15))
                            
                            elementos.append(Paragraph(f"<b>Subtotal:</b> ${subtotal_acumulado:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Descuentos:</b> ${descuento:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>IVA (15%):</b> ${iva:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>TOTAL:</b> ${total_final:.3f}", estilo_sub))
                            
                            doc.build(elementos)
                            
                            st.success(f"¡Cotización guardada y PDF generado con éxito!")
                            st.markdown(f"📄 Archivo guardado en tu carpeta como: **{nombre_archivo_pdf}**")
                            
                            with open(nombre_archivo_pdf, "rb") as archivo_pdf:
                                st.download_button(
                                    label="📥 Descargar PDF de la Proforma",
                                    data=archivo_pdf,
                                    file_name=nombre_archivo_pdf,
                                    mime="application/pdf"
                                )
                            
                            st.session_state.carrito = []
                        except Exception as e:
                            st.error(f"Error al generar la proforma o PDF: {e}")
                    else:
                        st.warning("Por favor ingresa el nombre del cliente.")

    # --- REPORTES DE GANANCIAS (SOLO ACEPTADAS) ---
    elif menu == "Reportes de Ganancias" and st.session_state.rol == "Administrador":
        st.header("TAX-ON | Reportes Financieros de Ganancia Neta")
        st.info("Mostrando los beneficios netos calculados exclusivamente a partir de las cotizaciones **Aceptadas** por los clientes.")
        
        conn = sqlite3.connect("tax_on_system.db")
        df_todas = pd.read_sql_query("SELECT nro_proforma, fecha, cliente, ruc_cliente, vendedor, total, ganancia_neta, estado FROM proformas", conn)
        conn.close()
        
        if not df_todas.empty:
            st.markdown("### Historial General de Proformas")
            st.dataframe(df_todas, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 💰 Ganancia Neta de Cotizaciones Aceptadas")
            df_aceptadas = df_todas[df_todas['estado'] == 'Aceptada']
            
            if not df_aceptadas.empty:
                st.dataframe(df_aceptadas[['nro_proforma', 'fecha', 'cliente', 'total', 'ganancia_neta']], use_container_width=True)
                ganancia_neta_aceptadas = df_aceptadas['ganancia_neta'].sum()
                st.metric(label="Ganancia Neta Total (Solo Proformas Aceptadas)", value=f"${ganancia_neta_aceptadas:.2f}")
            else:
                st.warning("⚠️ No hay cotizaciones con estado 'Aceptada' en este momento. Ve al módulo de 'Gestión de Cotizaciones' para actualizar el estado de alguna proforma.")
        else:
            st.info("Aún no hay cotizaciones registradas en el sistema.")