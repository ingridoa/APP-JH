import sqlite3
import datetime
import io
import math
import re
import os
import urllib.parse
import streamlit as st
import pandas as pd

# Importación segura de PyPDF
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES
# ==========================================
st.set_page_config(
    page_title="Servicios de Contabilidad - Juan de la Hoz",
    page_icon="💼",
    layout="wide"
)

# Estilos CSS que garantizan visibilidad en computadores y celulares
st.markdown("""
    <style>
    /* Fondo principal claro */
    .stApp { background-color: #F4F7F9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* FORZAR COLOR DE TEXTO VISIBLE EN MÓVILES (Evita textos invisibles por modo oscuro) */
    .stApp, .stMarkdown, p, span, label, h1, h2, h3, h4, h5, h6, div {
        color: #1C3B57 !important;
    }

    /* Textos dentro de formularios y opciones de tipo radio */
    div[data-testid="stRadioButton"] label, div[data-testid="stMarkdownContainer"] p {
        color: #1C3B57 !important;
        font-weight: 600 !important;
    }

    /* Cajas de entrada de texto */
    input, select, textarea {
        color: #000000 !important;
        background-color: #FFFFFF !important;
    }

    /* Contenedor del Encabezado */
    .header-box { 
        background: linear-gradient(135deg, #0A192F 0%, #1E3A5F 100%); 
        padding: 20px 25px; 
        border-radius: 12px; 
        margin-bottom: 20px;
        border-bottom: 3px solid #C5A059;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
    }
    .header-title-text { 
        font-size: 24px; 
        font-weight: 700; 
        color: #FFFFFF !important; 
        margin: 0; 
        letter-spacing: 1px;
    }
    .header-sub-text { 
        font-size: 14px; 
        color: #D1D5DB !important; 
        margin-top: 5px; 
        font-style: italic;
    }
    
    /* Tarjetas de Contenido */
    .folder-card { background-color: #FFFFFF; padding: 20px; border-radius: 10px; border-left: 6px solid #1E3A5F; box-shadow: 0px 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px; }
    .subfolder-card { background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 10px; }
    .section-header { background-color: #0A192F; color: #FFFFFF !important; padding: 10px 15px; border-radius: 6px; font-size: 18px; font-weight: bold; margin-bottom: 15px; margin-top: 10px; border-left: 4px solid #C5A059; }
    .section-header * { color: #FFFFFF !important; }
    .total-box { background-color: #EBF8FF; border: 2px solid #3182CE; padding: 15px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold; color: #2B6CB0 !important; margin-top: 10px; }
    .pay-card { background-color: #FFFFFF; padding: 20px; border-radius: 10px; border: 1px solid #CBD5E0; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONEXIÓN ROBUSTA Y LIMPIA CON SQLITE
# ==========================================
NOMBRE_DB = "contabilidad_v2.db"

def get_db_connection():
    conn = sqlite3.connect(NOMBRE_DB, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn

# ==========================================
# 2. BASE DE DATOS Y AUTO-MIGRACIÓN
# ==========================================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ficha_ingreso_cliente (
            id_interno INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_id TEXT UNIQUE,
            num_cliente TEXT DEFAULT 'N/A',
            num_contable TEXT DEFAULT 'N/A',
            num_remuneraciones TEXT DEFAULT 'N/A',
            fecha_ingreso TEXT DEFAULT '',
            fecha_inicio_actividades TEXT DEFAULT '',
            nombres_cliente TEXT DEFAULT '',
            apellidos_cliente TEXT DEFAULT '',
            nombre_cliente TEXT DEFAULT '',
            run_cliente TEXT NOT NULL,
            clave_sii TEXT DEFAULT '',
            clave_certificado_elect TEXT DEFAULT '',
            nombre_rep_legal TEXT DEFAULT '',
            run_rep_legal TEXT DEFAULT '',
            clave_rep_sii TEXT DEFAULT '',
            clave_unica TEXT DEFAULT '',
            facturador_electronico TEXT DEFAULT 'NO',
            correo_electronico TEXT NOT NULL,
            num_contacto TEXT DEFAULT '',
            remuneraciones_flag TEXT DEFAULT 'NO',
            previred_flag TEXT DEFAULT 'NO',
            run_previred TEXT DEFAULT '',
            clave_previred TEXT DEFAULT '',
            administrativa TEXT DEFAULT '',
            oficina TEXT DEFAULT '',
            honorarios_monto REAL DEFAULT 0,
            servicios_contratados TEXT DEFAULT '',
            observaciones TEXT DEFAULT '',
            estado TEXT DEFAULT 'Activo'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas_cliente (
            id_empresa INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_id_fk TEXT NOT NULL,
            rut_empresa TEXT NOT NULL,
            razon_social TEXT NOT NULL,
            rubro_giro TEXT DEFAULT '',
            fecha_inicio_actividades TEXT DEFAULT '',
            clave_sii TEXT DEFAULT '',
            clave_certificado TEXT DEFAULT '',
            monto_honorarios_base REAL DEFAULT 0,
            FOREIGN KEY (codigo_id_fk) REFERENCES ficha_ingreso_cliente(codigo_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicios_mensuales_cliente (
            id_servicio INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_id_fk TEXT NOT NULL,
            id_empresa_fk INTEGER DEFAULT 0,
            fecha_cobro TEXT NOT NULL,
            fecha_limite TEXT DEFAULT '',
            tipo_cobro TEXT NOT NULL,
            monto_iva REAL DEFAULT 0,
            monto_renta_anual REAL DEFAULT 0,
            monto_imposiciones REAL DEFAULT 0,
            monto_honorarios REAL DEFAULT 0,
            monto_certificados REAL DEFAULT 0,
            monto_otros REAL DEFAULT 0,
            monto_total REAL DEFAULT 0,
            pagado_iva INTEGER DEFAULT 0,
            pagado_renta_anual INTEGER DEFAULT 0,
            pagado_imposiciones INTEGER DEFAULT 0,
            pagado_honorarios INTEGER DEFAULT 0,
            pagado_certificados INTEGER DEFAULT 0,
            pagado_otros INTEGER DEFAULT 0,
            observaciones_honorarios TEXT DEFAULT '',
            estado_pago TEXT DEFAULT 'Pendiente',
            FOREIGN KEY (codigo_id_fk) REFERENCES ficha_ingreso_cliente(codigo_id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def obtener_proximo_codigo_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id_interno) FROM ficha_ingreso_cliente")
    max_id = cursor.fetchone()[0]
    conn.close()
    sig_id = 1 if max_id is None else max_id + 1
    return f"CLI-{sig_id:05d}"

OPCIONES_OFICINAS = ["Oficina de Chillán", "Oficina de Yungay", "Oficina de Concepción"]

# ==========================================
# 3. NAVEGACIÓN Y ENCABEZADO CON LOGO
# ==========================================
if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False
if "admin_email" not in st.session_state:
    st.session_state.admin_email = ""
if "mensaje_exito" not in st.session_state:
    st.session_state.mensaje_exito = ""
if "confirmar_borrado_id" not in st.session_state:
    st.session_state.confirmar_borrado_id = None

ADMINS_AUTORIZADOS = ["juandelahoz@asesoriasdelahoz.com", "admin@juandelahoz.com", "ingri@gmail.com"]

# --- ENCABEZADO SUPERIOR CON LOGO CORPORATIVO ---
col_head_left, col_head_right = st.columns([2.5, 1])

with col_head_left:
    st.markdown("""
        <div class="header-box">
            <div class="header-title-text">PLATAFORMA DE GESTIÓN CONTABLE</div>
            <div class="header-sub-text">Asesores Tributarios & Contables — De la Hoz & Asociados</div>
        </div>
    """, unsafe_allow_html=True)

with col_head_right:
    # Búsqueda adaptativa para el archivo 'logo JH'
    posibles_nombres_logo = [
        "logo JH", "logo JH.jpg", "logo JH.png", "logo JH.jpeg",
        "logo_JH.jpg", "logo_JH.png", "logo juan de la hoz.jpg"
    ]
    logo_encontrado = None
    for nombre in posibles_nombres_logo:
        if os.path.exists(nombre):
            logo_encontrado = nombre
            break
            
    if logo_encontrado:
        st.image(logo_encontrado, use_container_width=True)
    else:
        st.info("💡 Coloca la imagen 'logo JH' en tu carpeta del proyecto y en GitHub.")

menu_principal = st.selectbox("Navegación Principal", ["Inicio", "Quiénes Somos", "Acceso a Plataforma"], label_visibility="collapsed")

if menu_principal == "Inicio":
    st.markdown("<h2>Bienvenido a la Plataforma de Gestión Contable</h2>", unsafe_allow_html=True)

elif menu_principal == "Quiénes Somos":
    st.markdown("<h2>Sobre Nosotros</h2>", unsafe_allow_html=True)

elif menu_principal == "Acceso a Plataforma":
    perfil = st.radio("Seleccione el Tipo de Usuario:", ["Cliente", "Administrador"], horizontal=True)
    st.divider()

    if perfil == "Administrador":
        if not st.session_state.admin_autenticado:
            st.markdown("### 🔐 Acceso de Administración (Google OAuth)")
            with st.form("form_login_admin"):
                e_admin = st.text_input("Correo Google:")
                p_admin = st.text_input("Contraseña:", type="password")
                if st.form_submit_button("🔴 Iniciar Sesión con Google"):
                    if e_admin in ADMINS_AUTORIZADOS or e_admin.endswith("@gmail.com"):
                        st.session_state.admin_autenticado = True
                        st.session_state.admin_email = e_admin
                        st.rerun()
                    else:
                        st.error("Sin permisos de administración.")
        else:
            st.sidebar.markdown(f"👤 **Admin:** {st.session_state.admin_email}")
            if st.sidebar.button("Cerrar Sesión"):
                st.session_state.admin_autenticado = False
                st.rerun()

            st.sidebar.title("☰ Menú Administrador")
            modulo_admin = st.sidebar.radio("Módulos:", ["👥 Clientes", "🧾 Recibos de Dinero", "📊 Consolidado Anual"])

            if modulo_admin == "👥 Clientes":
                st.subheader("👥 Módulo de Gestión de Clientes y Sub-Empresas")

                tab_ingreso, tab_editar, tab_tabla, tab_carpetas = st.tabs([
                    "📝 Ingresar Nuevo Cliente",
                    "✏️ Editar / Eliminar Cliente",
                    "📊 Vista General",
                    "📁 Subcarpetas por Empresa y Cobros"
                ])

                # 1. INGRESAR NUEVO CLIENTE
                with tab_ingreso:
                    if st.session_state.mensaje_exito:
                        st.success(st.session_state.mensaje_exito)
                        st.session_state.mensaje_exito = ""

                    cod_sugerido = obtener_proximo_codigo_id()

                    with st.form("form_nuevo_cliente", clear_on_submit=True):
                        st.markdown('<div class="section-header">📌 1. Antecedentes del Cliente (Titular)</div>', unsafe_allow_html=True)
                        st.text_input("ID Interno de Cliente (Autogenerado):", value=cod_sugerido, disabled=True)

                        c1, c2 = st.columns(2)
                        nombres_cli = c1.text_input("Nombres del Cliente *")
                        apellidos_cli = c2.text_input("Apellidos del Cliente *")

                        c3, c4, c5 = st.columns(3)
                        run_cli = c3.text_input("RUN / RUT Titular *")
                        correo_cli = c4.text_input("Correo Electrónico *")
                        num_contac = c5.text_input("N° Contacto / Teléfono *")

                        c6, c7 = st.columns(2)
                        oficina_resp = c6.selectbox("Oficina Responsable *", OPCIONES_OFICINAS)
                        admin_resp = c7.text_input("Administrativa Responsable *")

                        st.markdown('<div class="section-header">🏢 2. Primera Empresa o Rubro Asociado</div>', unsafe_allow_html=True)

                        c8, c9 = st.columns(2)
                        razon_soc = c8.text_input("Razón Social / Nombre Fantasía Empresa *")
                        rut_emp = c9.text_input("RUT Empresa *")

                        c10, c11 = st.columns(2)
                        rubro_gir = c10.text_input("Rubro / Giro Comercial * (Ej: Calzado, Transporte, etc.)")
                        f_inic_emp = c11.date_input("Fecha Inicio Actividades SII", format="DD/MM/YYYY")

                        c12, c13, c14 = st.columns(3)
                        clv_sii_e = c12.text_input("Clave SII Empresa", type="password")
                        clv_cert_e = c13.text_input("Clave Certificado Electrónico", type="password")
                        hono_base_e = c14.number_input("Honorarios Base Empresa ($ CLP) *", min_value=0.0)

                        obs = st.text_area("Observaciones Adicionales")

                        st.divider()
                        btn_guardar = st.form_submit_button("💾 Registrar Cliente y Crear Empresa Inicial")

                        if btn_guardar:
                            if not (nombres_cli and apellidos_cli and run_cli and correo_cli and razon_soc and rut_emp):
                                st.error("❌ Complete los campos obligatorios del Cliente y su Empresa.")
                            else:
                                nombre_comp_titular = f"{nombres_cli} {apellidos_cli}".strip()
                                
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO ficha_ingreso_cliente (
                                        codigo_id, num_cliente, num_contable, num_remuneraciones,
                                        fecha_ingreso, fecha_inicio_actividades, nombres_cliente, apellidos_cliente,
                                        nombre_cliente, run_cliente, clave_sii, clave_certificado_elect,
                                        nombre_rep_legal, run_rep_legal, clave_rep_sii, clave_unica,
                                        facturador_electronico, correo_electronico, num_contacto, remuneraciones_flag,
                                        previred_flag, run_previred, clave_previred, administrativa, oficina,
                                        honorarios_monto, servicios_contratados, observaciones
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    "TEMP", "N/A", "N/A", "N/A",
                                    str(datetime.date.today()), str(f_inic_emp), nombres_cli, apellidos_cli,
                                    nombre_comp_titular, run_cli, clv_sii_e, clv_cert_e,
                                    nombre_comp_titular, run_cli, clv_sii_e, "",
                                    "SI", correo_cli, num_contac, "NO",
                                    "NO", "", "", admin_resp, oficina_resp,
                                    hono_base_e, "General", obs
                                ))
                                id_gen = cursor.lastrowid
                                cod_un = f"CLI-{id_gen:05d}"
                                cursor.execute("UPDATE ficha_ingreso_cliente SET codigo_id = ? WHERE id_interno = ?", (cod_un, id_gen))

                                cursor.execute("""
                                    INSERT INTO empresas_cliente (
                                        codigo_id_fk, rut_empresa, razon_social, rubro_giro,
                                        fecha_inicio_actividades, clave_sii, clave_certificado, monto_honorarios_base
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    cod_un, rut_emp, razon_soc, rubro_gir,
                                    str(f_inic_emp), clv_sii_e, clv_cert_e, hono_base_e
                                ))
                                conn.commit()
                                conn.close()

                                st.session_state.mensaje_exito = f"✅ Cliente '{nombre_comp_titular}' y empresa '{razon_soc}' registrados exitosamente con ID: {cod_un}"
                                st.rerun()

                # 2. EDITAR / ELIMINAR CLIENTE
                with tab_editar:
                    st.markdown("### ✏️ Gestión, Edición y Bajas de Clientes")
                    
                    conn = get_db_connection()
                    df_edit_list = pd.read_sql_query("SELECT codigo_id, nombres_cliente, apellidos_cliente, run_cliente FROM ficha_ingreso_cliente", conn)
                    conn.close()

                    if not df_edit_list.empty:
                        lista_edit_auto = [f"{row['codigo_id']} | {row['nombres_cliente']} {row['apellidos_cliente']} (RUT: {row['run_cliente']})" for _, row in df_edit_list.iterrows()]
                        cliente_a_editar = st.selectbox("🔍 Seleccione el Cliente:", lista_edit_auto, key="sel_edit_cli")
                        
                        if cliente_a_editar:
                            cod_id_edit = cliente_a_editar.split(" | ")[0]
                            
                            subtab1, subtab2, subtab_del = st.tabs([
                                "📌 Modificar Datos del Cliente",
                                "➕ Registrar Nueva Empresa",
                                "🗑️ Eliminar Cliente de la Plataforma"
                            ])

                            with subtab1:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("SELECT * FROM ficha_ingreso_cliente WHERE codigo_id = ?", (cod_id_edit,))
                                e_data = cursor.fetchone()
                                conn.close()

                                if e_data:
                                    with st.form("form_edit_titular"):
                                        c_e1, c_e2 = st.columns(2)
                                        edit_nom = c_e1.text_input("Nombres", value=e_data[7] if e_data[7] else "")
                                        edit_ape = c_e2.text_input("Apellidos", value=e_data[8] if e_data[8] else "")
                                        c_e3, c_e4 = st.columns(2)
                                        edit_cor = c_e3.text_input("Correo", value=e_data[18] if e_data[18] else "")
                                        edit_tel = c_e4.text_input("Contacto", value=e_data[19] if e_data[19] else "")
                                        
                                        if st.form_submit_button("💾 Guardar Cambios en Titular"):
                                            nom_completo_act = f"{edit_nom} {edit_ape}".strip()
                                            conn = get_db_connection()
                                            cursor = conn.cursor()
                                            cursor.execute("""
                                                UPDATE ficha_ingreso_cliente
                                                SET nombres_cliente=?, apellidos_cliente=?, nombre_cliente=?, correo_electronico=?, num_contacto=?
                                                WHERE codigo_id=?
                                            """, (edit_nom, edit_ape, nom_completo_act, edit_cor, edit_tel, cod_id_edit))
                                            conn.commit()
                                            conn.close()
                                            st.success("✅ Datos del titular actualizados con éxito.")
                                            st.rerun()

                            with subtab2:
                                st.markdown(f"#### Añadir Sub-Empresa / Giro adicional a `{cod_id_edit}`")
                                with st.form("form_nueva_subempresa", clear_on_submit=True):
                                    ce1, ce2 = st.columns(2)
                                    new_razon = ce1.text_input("Razón Social / Nombre Fantasía *")
                                    new_rut = ce2.text_input("RUT Empresa *")
                                    ce3, ce4 = st.columns(2)
                                    new_rubro = ce3.text_input("Rubro / Giro Comercial *")
                                    new_hono = ce4.number_input("Honorarios Base ($ CLP) *", min_value=0.0)

                                    if st.form_submit_button("➕ Vincular Empresa"):
                                        if new_razon and new_rut:
                                            conn = get_db_connection()
                                            cursor = conn.cursor()
                                            cursor.execute("""
                                                INSERT INTO empresas_cliente (codigo_id_fk, rut_empresa, razon_social, rubro_giro, monto_honorarios_base)
                                                VALUES (?, ?, ?, ?, ?)
                                            """, (cod_id_edit, new_rut, new_razon, new_rubro, new_hono))
                                            conn.commit()
                                            conn.close()
                                            st.success(f"✅ Sub-Empresa '{new_razon}' asociada correctamente.")
                                            st.rerun()
                                        else:
                                            st.error("Ingrese Razón Social y RUT.")

                            with subtab_del:
                                st.markdown("#### ⚠️ Zona de Eliminación Definitiva de Cliente")
                                st.warning(f"Atención: Está a punto de eliminar al cliente con ID `{cod_id_edit}`. Esta acción no se puede deshacer.")

                                if st.button("🗑️ Iniciar Proceso de Eliminación", type="primary", key="btn_init_del"):
                                    st.session_state.confirmar_borrado_id = cod_id_edit

                                if st.session_state.confirmar_borrado_id == cod_id_edit:
                                    st.error(f"🚨 **CONFIRMACIÓN REQUERIDA:** ¿Está completamente seguro de que desea eliminar al cliente `{cod_id_edit}`?")
                                    col_del1, col_del2 = st.columns(2)
                                    
                                    with col_del1:
                                        if st.button("⚠️ SÍ, ELIMINAR REGISTRO DEFINITIVAMENTE", key="btn_confirm_yes"):
                                            conn = get_db_connection()
                                            cursor = conn.cursor()
                                            cursor.execute("DELETE FROM servicios_mensuales_cliente WHERE codigo_id_fk = ?", (cod_id_edit,))
                                            cursor.execute("DELETE FROM empresas_cliente WHERE codigo_id_fk = ?", (cod_id_edit,))
                                            cursor.execute("DELETE FROM ficha_ingreso_cliente WHERE codigo_id = ?", (cod_id_edit,))
                                            conn.commit()
                                            conn.close()
                                            
                                            st.session_state.confirmar_borrado_id = None
                                            st.success(f"✅ El cliente `{cod_id_edit}` y todos sus registros han sido borrados de la plataforma.")
                                            st.rerun()

                                    with col_del2:
                                        if st.button("❌ CANCELAR Y CONSERVAR CLIENTE", key="btn_confirm_no"):
                                            st.session_state.confirmar_borrado_id = None
                                            st.info("Operación cancelada. El cliente permanece intacto.")
                                            st.rerun()

                # 3. VISTA GENERAL
                with tab_tabla:
                    conn = get_db_connection()
                    df_vista = pd.read_sql_query("""
                        SELECT c.codigo_id, 
                               COALESCE(c.nombre_cliente, c.nombres_cliente || ' ' || c.apellidos_cliente) as titular, 
                               e.razon_social, e.rubro_giro, e.rut_empresa, c.correo_electronico
                        FROM ficha_ingreso_cliente c
                        LEFT JOIN empresas_cliente e ON c.codigo_id = e.codigo_id_fk
                    """, conn)
                    conn.close()
                    st.dataframe(df_vista, use_container_width=True)

                # 4. SUBCARPETAS DIGITALES Y COBROS
                with tab_carpetas:
                    st.markdown("### 📁 Carpeta Digital y Emisión de Cobros por Sub-Empresa")
                    conn = get_db_connection()
                    df_todos = pd.read_sql_query("SELECT codigo_id, nombres_cliente, apellidos_cliente, run_cliente FROM ficha_ingreso_cliente", conn)
                    conn.close()

                    if not df_todos.empty:
                        lista_auto = [f"{row['codigo_id']} | {row['nombres_cliente']} {row['apellidos_cliente']} (RUT: {row['run_cliente']})" for _, row in df_todos.iterrows()]
                        cliente_sel = st.selectbox("🔍 Buscar Cliente:", lista_auto, key="sel_carpeta_cli")
                        
                        if cliente_sel:
                            cod_id_sel = cliente_sel.split(" | ")[0]
                            
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id_empresa, razon_social, rut_empresa, rubro_giro, monto_honorarios_base FROM empresas_cliente WHERE codigo_id_fk = ?", (cod_id_sel,))
                            empresas_del_cliente = cursor.fetchall()
                            conn.close()

                            if empresas_del_cliente:
                                st.markdown("#### 📂 Empresas / Rubros Asociados a este Cliente:")
                                
                                nombres_tabs = [f"🏢 {emp[1]} ({emp[3]})" for emp in empresas_del_cliente]
                                tabs_empresas = st.tabs(nombres_tabs)

                                for index, tab_emp in enumerate(tabs_empresas):
                                    id_emp, razon, rut_e, rubro, hono_base = empresas_del_cliente[index]
                                    hono_base_val = hono_base if hono_base is not None else 0.0
                                    
                                    with tab_emp:
                                        st.markdown(f"""
                                        <div class="subfolder-card">
                                            <h4>🏢 Subcarpeta: {razon}</h4>
                                            <p><b>RUT Empresa:</b> {rut_e} | <b>Rubro/Giro:</b> {rubro} | <b>Honorarios Base:</b> ${hono_base_val:,.0f} CLP</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        with st.expander(f"➕ Emitir Cobro Mensual para {razon}", expanded=False):
                                            c_f1, c_f2 = st.columns(2)
                                            fecha_cobro_sel = c_f1.date_input("📅 Fecha de Emisión *", value=datetime.date.today(), format="DD/MM/YYYY", key=f"fc_{id_emp}")
                                            fecha_limite_sel = c_f2.date_input("⏰ Fecha Límite de Pago *", value=datetime.date.today() + datetime.timedelta(days=15), format="DD/MM/YYYY", key=f"fl_{id_emp}")

                                            opciones_totales = ["IVA", "Renta Anual", "Imposiciones", "Honorarios", "Certificados", "Otros"]
                                            servicios_a_aperturar = st.multiselect("Servicios a incluir en el cobro:", opciones_totales, default=["Honorarios"], key=f"ms_{id_emp}")

                                            monto_iva, monto_renta, monto_prev, monto_hono_cobro, monto_cert, monto_otros = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

                                            if "Honorarios" in servicios_a_aperturar:
                                                monto_hono_cobro = st.number_input("Honorarios ($ CLP):", value=float(hono_base_val), key=f"mh_{id_emp}")
                                            if "IVA" in servicios_a_aperturar:
                                                monto_iva = st.number_input("IVA ($ CLP):", min_value=0.0, key=f"mi_{id_emp}")
                                            if "Renta Anual" in servicios_a_aperturar:
                                                monto_renta = st.number_input("Renta ($ CLP):", min_value=0.0, key=f"mr_{id_emp}")
                                            if "Imposiciones" in servicios_a_aperturar:
                                                monto_prev = st.number_input("Imposiciones ($ CLP):", min_value=0.0, key=f"mp_{id_emp}")
                                            if "Certificados" in servicios_a_aperturar:
                                                monto_cert = st.number_input("Certificados ($ CLP):", min_value=0.0, key=f"mc_{id_emp}")
                                            if "Otros" in servicios_a_aperturar:
                                                monto_otros = st.number_input("Otros ($ CLP):", min_value=0.0, key=f"mo_{id_emp}")

                                            total_consolidado = monto_iva + monto_renta + monto_prev + monto_hono_cobro + monto_cert + monto_otros

                                            if st.button(f"📤 Guardar Cobro de {razon}", key=f"btn_save_{id_emp}"):
                                                if total_consolidado > 0:
                                                    conn = get_db_connection()
                                                    cursor = conn.cursor()
                                                    cursor.execute("""
                                                        INSERT INTO servicios_mensuales_cliente (
                                                            codigo_id_fk, id_empresa_fk, fecha_cobro, fecha_limite, tipo_cobro,
                                                            monto_iva, monto_renta_anual, monto_imposiciones, monto_honorarios,
                                                            monto_certificados, monto_otros, monto_total
                                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                    """, (
                                                        cod_id_sel, id_emp, str(fecha_cobro_sel), str(fecha_limite_sel), "Mensual",
                                                        monto_iva, monto_renta, monto_prev, monto_hono_cobro, monto_cert, monto_otros, total_consolidado
                                                    ))
                                                    conn.commit()
                                                    conn.close()
                                                    st.success(f"✅ Cobro por ${total_consolidado:,.0f} registrado para la empresa {razon}.")
                                                    st.rerun()
                            else:
                                st.warning("Este cliente no tiene empresas asociadas.")

    # ======================================
    # ENTORNO CLIENTE MULTIEMPRESA
    # ======================================
    else:
        st.subheader("🔑 Portal del Cliente - Mis Empresas y Pagos Parciales")
        email_cliente = st.text_input("Ingrese su Correo Registrado (Google/Gmail):")

        if email_cliente:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT codigo_id, nombres_cliente, apellidos_cliente FROM ficha_ingreso_cliente WHERE correo_electronico = ?", (email_cliente,))
            cli_found = cursor.fetchone()
            conn.close()

            if cli_found:
                st.success(f"Bienvenido(a), **{cli_found[1]} {cli_found[2]}** (ID: `{cli_found[0]}`)")

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id_empresa, razon_social, rubro_giro, rut_empresa FROM empresas_cliente WHERE codigo_id_fk = ?", (cli_found[0],))
                mis_empresas = cursor.fetchall()
                conn.close()

                if mis_empresas:
                    st.markdown("### 🏢 Seleccione su Empresa para revisar o abonar cobros:")
                    tabs_cli_emp = st.tabs([f"🏢 {emp[1]} ({emp[2]})" for emp in mis_empresas])

                    for idx, t_emp in enumerate(tabs_cli_emp):
                        id_e, r_soc, rub, rut_e = mis_empresas[idx]
                        
                        with t_emp:
                            st.info(f"**Empresa:** {r_soc} | **RUT:** {rut_e} | **Giro:** {rub}")

                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT id_servicio, fecha_cobro, fecha_limite, monto_iva, monto_renta_anual, monto_imposiciones,
                                       monto_honorarios, monto_certificados, monto_otros, monto_total,
                                       pagado_iva, pagado_renta_anual, pagado_imposiciones, pagado_honorarios, pagado_certificados, pagado_otros,
                                       estado_pago
                                FROM servicios_mensuales_cliente
                                WHERE codigo_id_fk = ? AND id_empresa_fk = ? AND estado_pago != 'PAGADO TOTAL'
                            """, (cli_found[0], id_e))
                            cobros_empresa = cursor.fetchall()
                            conn.close()

                            if cobros_empresa:
                                for c in cobros_empresa:
                                    id_serv, f_cobro, f_limite, m_iva, m_renta, m_prev, m_hono, m_cert, m_otros, m_total, p_iva, p_renta, p_prev, p_hono, p_cert, p_otros, st_pago = c

                                    st.markdown(f"""
                                    <div class="pay-card">
                                        <h4>📅 Periodo: {f_cobro} | ⏰ Límite: <span style="color:red;">{f_limite}</span></h4>
                                        <p><b>Estado:</b> {st_pago}</p>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    monto_abono_actual = 0.0
                                    pagos_nuevos = {}
                                    col_p1, col_p2 = st.columns(2)

                                    with col_p1:
                                        if m_hono > 0:
                                            if p_hono == 0:
                                                st.checkbox(f"💼 Honorarios Contables: ${m_hono:,.0f} CLP (OBLIGATORIO)", value=True, disabled=True, key=f"c_h_{id_serv}")
                                                monto_abono_actual += m_hono
                                                pagos_nuevos['hono'] = 1
                                            else:
                                                st.success(f"💼 Honorarios: ${m_hono:,.0f} CLP [PAGADO]")

                                        if m_iva > 0:
                                            if p_iva == 0:
                                                if st.checkbox(f"🧾 IVA (SII): ${m_iva:,.0f} CLP", value=False, key=f"c_i_{id_serv}"):
                                                    monto_abono_actual += m_iva
                                                    pagos_nuevos['iva'] = 1
                                            else:
                                                st.success(f"🧾 IVA: ${m_iva:,.0f} CLP [PAGADO]")

                                    with col_p2:
                                        if m_prev > 0:
                                            if p_prev == 0:
                                                if st.checkbox(f"🏛️ Imposiciones: ${m_prev:,.0f} CLP", value=False, key=f"c_p_{id_serv}"):
                                                    monto_abono_actual += m_prev
                                                    pagos_nuevos['prev'] = 1
                                            else:
                                                st.success(f"🏛️ Imposiciones: ${m_prev:,.0f} CLP [PAGADO]")

                                    st.markdown(f"""
                                    <div class="total-box">
                                        Monto A Pagar: ${monto_abono_actual:,.0f} CLP
                                    </div>
                                    """, unsafe_allow_html=True)

                                    if st.button(f"💳 Proceder al Pago de {r_soc} (${monto_abono_actual:,.0f} CLP)", key=f"btn_pay_{id_serv}"):
                                        up_hono = 1 if ('hono' in pagos_nuevos or p_hono == 1) else 0
                                        up_iva = 1 if ('iva' in pagos_nuevos or p_iva == 1) else 0
                                        up_prev = 1 if ('prev' in pagos_nuevos or p_prev == 1) else 0

                                        total_items = (1 if m_hono>0 else 0) + (1 if m_iva>0 else 0) + (1 if m_prev>0 else 0)
                                        pagados_items = up_hono + up_iva + up_prev
                                        nuevo_estado = "PAGADO TOTAL" if pagados_items >= total_items else "PAGADO PARCIAL"

                                        conn = get_db_connection()
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            UPDATE servicios_mensuales_cliente
                                            SET pagado_honorarios = ?, pagado_iva = ?, pagado_imposiciones = ?, estado_pago = ?
                                            WHERE id_servicio = ?
                                        """, (up_hono, up_iva, up_prev, nuevo_estado, id_serv))
                                        conn.commit()
                                        conn.close()

                                        st.balloons()
                                        st.success(f"¡Abono de ${monto_abono_actual:,.0f} CLP procesado!")
                                        st.rerun()
                            else:
                                st.info(f"La empresa {r_soc} no registra cobros pendientes.")
                else:
                    st.info("No registra empresas asociadas.")
            else:
                st.error("El correo no está registrado.")