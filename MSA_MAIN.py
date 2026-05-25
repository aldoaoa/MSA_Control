import streamlit as st
from supabase import create_client, Client
import datetime
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Gestión de Metrología", page_icon="🔬", layout="wide")

# Inicializar conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- GESTIÓN DE SESIÓN (LOGIN) ---
if "user" not in st.session_state:
    st.session_state.user = None

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.rerun()
    except Exception as e:
        st.error(f"Detalle del error: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# ==========================================
#        MÓDULO MSA (CÓDIGO ORIGINAL)
# ==========================================
def mostrar_resultado_equipo(id_equipo):
    st.markdown("---")
    with st.spinner("Buscando en la base de datos MSA..."):
        respuesta = supabase.table('equipos_msa').select("*").eq('id_equipo', id_equipo).execute()
        
    if respuesta.data:
        equipo = respuesta.data[0]
        estatus = equipo['estatus']
        
        if estatus == 'VIGENTE':
            st.success(f"### 🟢 Estatus: {estatus}")
        elif estatus == 'POR VENCER' or estatus == 'EN PROCESO':
            st.warning(f"### 🟡 Estatus: {estatus}")
        else:
            st.error(f"### 🔴 Estatus: {estatus}")
            
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Datos del Equipo")
            st.write(f"**ID:** `{equipo['id_equipo']}`")
            st.write(f"**Descripción:** {equipo['descripcion']}")
            st.write(f"**Marca:** {equipo['marca']} | **Modelo:** {equipo['modelo']}")
            st.write(f"**Serie:** {equipo['serie']}")
            
        with c2:
            st.markdown("#### Control MSA")
            st.write(f"**Ubicación:** {equipo['ubicacion']}")
            st.write(f"**Estudio requerido:** {equipo['estudio']}")
            st.write(f"**Último Informe:** {equipo['informe_reciente']}")
            st.write(f"**Vencimiento:** {equipo['fecha_vencimiento']}")
            
        st.markdown("---")
        st.markdown("#### 📁 Archivo del Estudio (Red Local)")
        ruta_servidor = equipo.get('link_servidor')
        if ruta_servidor and str(ruta_servidor).strip() not in ['None', '', 'S/D', 'N/A']:
            st.caption("Copia la ruta de abajo y pégala en tu Explorador de Windows para abrir la carpeta directamente:")
            st.code(ruta_servidor, language="text")
        else:
            st.warning("⚠️ Este equipo no tiene registrada una ruta de servidor local para sus archivos de estudio.")
    else:
        st.error(f"❌ No se encontró ningún equipo registrado con el ID: **{id_equipo}**")

def modulo_busqueda_msa():
    tab_escaner, tab_manual = st.tabs(["📷 Escáner QR", "⌨️ Búsqueda Manual"])
    with tab_escaner:
        st.info("Enfoca el código QR del equipo.")
        imagen_camara = st.camera_input("Escáner QR MSA", key="camara_busqueda_msa")
        if imagen_camara is not None:
            with st.spinner("Analizando código QR..."):
                bytes_data = imagen_camara.getvalue()
                cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                codigos_qr = decode(cv2_img)
                if codigos_qr:
                    id_escaneado = codigos_qr[0].data.decode('utf-8').strip()
                    st.success(f"✅ Código detectado: **{id_escaneado}**")
                    mostrar_resultado_equipo(id_escaneado)
                else:
                    st.error("❌ No se detectó ningún código QR.")

    with tab_manual:
        id_busqueda = st.text_input("ID del equipo (Ej. BCS-QRO-LAB-MIC001):", key="texto_busqueda_msa")
        if st.button("🔍 Buscar Equipo MSA", type="primary", use_container_width=True, key="btn_buscar_msa"):
            if id_busqueda:
                mostrar_resultado_equipo(id_busqueda.strip())
            else:
                st.warning("⚠️ Por favor, ingresa un ID válido.")

def modulo_altas_bajas_msa():
    st.info("Módulo original de altas y bajas de MSA... (Código omitido para brevedad visual, aquí va exactamente tu función actual modulo_altas_bajas)")
    # NOTA: Inserta aquí el contenido exacto de tu función modulo_altas_bajas original

def modulo_informes_msa():
    st.info("Módulo original de informes de MSA... (Código omitido para brevedad visual, aquí va exactamente tu función actual modulo_informes)")
    # NOTA: Inserta aquí el contenido exacto de tu función modulo_informes original

def mostrar_dashboard_msa():
    st.subheader("📊 Estado General del Laboratorio (MSA)")
    with st.spinner("Cargando inventario consolidado..."):
        res = supabase.table('equipos_msa').select('id_equipo, descripcion, estudio, fecha_creacion, fecha_vencimiento, estatus').execute()
    if res.data:
        df_dash = pd.DataFrame(res.data)
        total = len(df_dash)
        vigentes = len(df_dash[df_dash['estatus'].str.upper() == 'VIGENTE'])
        por_vencer = len(df_dash[df_dash['estatus'].str.upper() == 'POR VENCER'])
        bajas = len(df_dash[df_dash['estatus'].str.upper() == 'BAJA'])
        vencidos = len(df_dash[df_dash['estatus'].str.upper() == 'VENCIDO'])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔬 Total Equipos", total)
        c2.metric("🟢 Vigentes", vigentes)
        c3.metric("🟡 Por Vencer", por_vencer)
        c4.metric("🔴 Críticos / Bajas", vencidos + bajas)
        
        st.markdown("---")
        df_visual = df_dash.rename(columns={'id_equipo': 'ID Equipo', 'descripcion': 'Descripción', 'estudio': 'Estudio', 'fecha_creacion': 'Fecha Último Estudio', 'fecha_vencimiento': 'Fecha Vencimiento', 'estatus': 'Estatus'})
        st.dataframe(df_visual, use_container_width=True, hide_index=True)


# ==========================================
#     NUEVO MÓDULO: CALENDARIO CALIBRACIÓN
# ==========================================
def mostrar_resultado_calibracion(nuevo_id):
    st.markdown("---")
    with st.spinner("Buscando en Calendario de Calibración..."):
        respuesta = supabase.table('calendario_calibracion').select("*").eq('nuevo_id', nuevo_id).execute()
        
    if respuesta.data:
        equipo = respuesta.data[0]
        estatus = equipo['estatus']
        
        if estatus == 'VIGENTE':
            st.success(f"### 🟢 Estatus: {estatus}")
        elif estatus == 'POR VENCER' or estatus == 'EN PROCESO':
            st.warning(f"### 🟡 Estatus: {estatus}")
        else:
            st.error(f"### 🔴 Estatus: {estatus}")
            
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### Identificación")
            st.write(f"**Nuevo ID:** `{equipo['nuevo_id']}`")
            st.write(f"**ID Obsoleto:** {equipo['id_obsoleto']}")
            st.write(f"**Descripción:** {equipo['descripcion']}")
            st.write(f"**Marca/Modelo:** {equipo['marca']} / {equipo['modelo']}")
            st.write(f"**Serie:** {equipo['serie']}")
            
        with c2:
            st.markdown("#### Operación")
            st.write(f"**Ubicación:** {equipo['ubicacion']}")
            st.write(f"**Operación:** {equipo['operacion']}")
            st.write(f"**Alcance:** {equipo['alcance_operacion']}")
            st.write(f"**Control:** {equipo['control']}")
            st.write(f"**Responsable:** {equipo['responsable']}")

        with c3:
            st.markdown("#### Calibración")
            st.write(f"**Proveedor:** {equipo['proveedor']}")
            st.write(f"**Vigencia:** {equipo['vigencia']} meses")
            st.write(f"**Último Informe:** {equipo['informe_cal']}")
            st.write(f"**Fecha Cal.:** {equipo['fecha_cal']}")
            st.write(f"**Vencimiento:** {equipo['fecha_venc']}")
            
        st.markdown("---")
        st.markdown("#### 📁 Link de Respaldo")
        if equipo.get('link'):
            st.code(equipo.get('link'), language="text")
        else:
            st.warning("No hay link registrado.")
    else:
        st.error(f"❌ No se encontró el equipo con ID: **{nuevo_id}**")

def modulo_busqueda_calibracion():
    tab_escaner, tab_manual = st.tabs(["📷 Escáner QR", "⌨️ Búsqueda Manual"])
    with tab_escaner:
        st.info("Enfoca el código QR del equipo.")
        imagen_camara = st.camera_input("Escáner QR Calibración", key="camara_busqueda_cal")
        if imagen_camara is not None:
            with st.spinner("Analizando..."):
                bytes_data = imagen_camara.getvalue()
                cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                codigos_qr = decode(cv2_img)
                if codigos_qr:
                    id_escaneado = codigos_qr[0].data.decode('utf-8').strip()
                    mostrar_resultado_calibracion(id_escaneado)
                else:
                    st.error("❌ No se detectó ningún código QR.")

    with tab_manual:
        id_busqueda = st.text_input("Nuevo ID del equipo:", key="texto_busqueda_cal")
        if st.button("🔍 Buscar en Calibración", type="primary", use_container_width=True, key="btn_buscar_cal"):
            if id_busqueda:
                mostrar_resultado_calibracion(id_busqueda.strip())

def modulo_altas_bajas_calibracion():
    accion = st.radio("Acción:", ["➕ Alta de Equipo", "🔻 Modificar Estatus"], horizontal=True, key="radio_acc_cal")
    st.markdown("---")
    
    if accion == "➕ Alta de Equipo":
        with st.form("form_alta_calibracion", clear_on_submit=True):
            st.subheader("Registrar Equipo en Calendario")
            c1, c2, c3 = st.columns(3)
            with c1:
                nuevo_id = st.text_input("Nuevo ID *")
                id_obsoleto = st.text_input("ID Obsoleto")
                descripcion = st.text_input("Descripción *")
                marca = st.text_input("Marca")
                modelo = st.text_input("Modelo")
                serie = st.text_input("Serie")
            with c2:
                ubicacion = st.text_input("Ubicación")
                operacion = st.text_input("Operación")
                alcance = st.text_input("Alcance de Operación")
                control = st.text_input("Control")
                responsable = st.text_input("Responsable")
                link = st.text_input("Link (Documento/Carpeta)")
            with c3:
                proveedor = st.text_input("Proveedor")
                vigencia = st.number_input("Vigencia (Meses)", min_value=1, value=12)
                informe_cal = st.text_input("Informe de Cal. Inicial")
                fecha_cal = st.date_input("Fecha de Calibración Inicial")
                estatus = st.selectbox("Estatus Inicial", ["VIGENTE", "POR VENCER", "VENCIDO", "EN PROCESO", "BAJA", "INACTIVO"], key="estatus_alta_cal")

            enviado = st.form_submit_button("💾 Guardar en Calibración", type="primary", use_container_width=True)
            
            if enviado:
                if not nuevo_id or not descripcion:
                    st.error("⚠️ Nuevo ID y Descripción son obligatorios.")
                else:
                    fecha_base = pd.to_datetime(fecha_cal)
                    fecha_vencimiento = fecha_base + pd.DateOffset(months=vigencia)
                    
                    nuevo_registro = {
                        "nuevo_id": nuevo_id.strip(), "id_obsoleto": id_obsoleto.strip(),
                        "descripcion": descripcion.strip(), "marca": marca.strip(), "modelo": modelo.strip(), "serie": serie.strip(),
                        "ubicacion": ubicacion.strip(), "operacion": operacion.strip(), "alcance_operacion": alcance.strip(),
                        "control": control.strip(), "responsable": responsable.strip(), "link": link.strip(),
                        "proveedor": proveedor.strip(), "vigencia": vigencia, "informe_cal": informe_cal.strip(),
                        "fecha_cal": fecha_base.strftime('%Y-%m-%d'), "fecha_venc": fecha_vencimiento.strftime('%Y-%m-%d'),
                        "estatus": estatus
                    }
                    try:
                        supabase.table("calendario_calibracion").insert(nuevo_registro).execute()
                        st.success(f"✅ Equipo {nuevo_id} registrado en Calibración.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    else:
        st.subheader("Actualizar Estatus (Calibración)")
        id_mod = st.text_input("Nuevo ID del equipo a modificar:")
        if st.button("Buscar para Modificar"):
            st.session_state['id_mod_cal'] = id_mod.strip()
            
        if 'id_mod_cal' in st.session_state:
            res = supabase.table('calendario_calibracion').select('descripcion, estatus').eq('nuevo_id', st.session_state['id_mod_cal']).execute()
            if res.data:
                eq = res.data[0]
                with st.form("form_mod_cal"):
                    nuevo_est = st.selectbox("Estatus", ["VIGENTE", "POR VENCER", "VENCIDO", "EN PROCESO", "BAJA"], index=["VIGENTE", "POR VENCER", "VENCIDO", "EN PROCESO", "BAJA"].index(eq['estatus']))
                    if st.form_submit_button("Actualizar"):
                        supabase.table('calendario_calibracion').update({'estatus': nuevo_est}).eq('nuevo_id', st.session_state['id_mod_cal']).execute()
                        st.success("✅ Estatus actualizado.")
                        del st.session_state['id_mod_cal']
                        st.rerun()

def modulo_informes_calibracion():
    st.subheader("📝 Registrar Nueva Calibración")
    id_equipo = st.text_input("Nuevo ID del Equipo:").strip()
    
    if id_equipo:
        res = supabase.table('calendario_calibracion').select('descripcion, vigencia').eq('nuevo_id', id_equipo).execute()
        if res.data:
            equipo = res.data[0]
            st.success(f"📦 Equipo confirmado: **{equipo['descripcion']}**")
            
            with st.form("form_informe_calibracion"):
                c1, c2 = st.columns(2)
                with c1:
                    nuevo_informe = st.text_input("No. Informe de Calibración *")
                    fecha_calibracion = st.date_input("Fecha de Calibración *", value=datetime.date.today())
                with c2:
                    proveedor = st.text_input("Proveedor del Servicio")
                    vigencia_meses = st.number_input("Vigencia (Meses) *", min_value=1, value=int(equipo['vigencia']))
                
                enviado = st.form_submit_button("💾 Actualizar Fechas", type="primary", use_container_width=True)
                
                if enviado and nuevo_informe:
                    f_base = pd.to_datetime(fecha_calibracion)
                    f_venc = f_base + pd.DateOffset(months=vigencia_meses)
                    
                    datos_act = {
                        "informe_cal": nuevo_informe.strip(),
                        "fecha_cal": f_base.strftime('%Y-%m-%d'),
                        "fecha_venc": f_venc.strftime('%Y-%m-%d'),
                        "vigencia": vigencia_meses,
                        "estatus": "VIGENTE"
                    }
                    if proveedor: datos_act["proveedor"] = proveedor.strip()
                    
                    supabase.table('calendario_calibracion').update(datos_act).eq('nuevo_id', id_equipo).execute()
                    st.success("✅ Calibración registrada. Vencimiento actualizado.")
                    st.rerun()

def mostrar_dashboard_calibracion():
    st.subheader("📊 Calendario de Calibración")
    res = supabase.table('calendario_calibracion').select('nuevo_id, descripcion, ubicacion, proveedor, fecha_venc, estatus').execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔬 Total Instrumentos", len(df))
        c2.metric("🟢 Vigentes", len(df[df['estatus'] == 'VIGENTE']))
        c3.metric("🟡 Por Vencer", len(df[df['estatus'] == 'POR VENCER']))
        
        # --- AQUÍ ESTÁ EL CAMBIO ---
        # Usamos .isin() para incluir múltiples estatus en el mismo contador
        c4.metric("🔴 Vencidos/Inactivos", len(df[df['estatus'].isin(['VENCIDO', 'BAJA', 'INACTIVO'])]))
        
        st.markdown("---")
        df_visual = df.rename(columns={'nuevo_id': 'Nuevo ID', 'descripcion': 'Descripción', 'ubicacion': 'Ubicación', 'proveedor': 'Proveedor', 'fecha_venc': 'Vencimiento', 'estatus': 'Estatus'})
        st.dataframe(df_visual, use_container_width=True, hide_index=True)


# ==========================================
#              ENRUTADOR PRINCIPAL
# ==========================================
with st.sidebar:
    st.title("⚙️ Navegación")
    # SELECTOR PRINCIPAL DE MÓDULO
    modulo_activo = st.radio("Selecciona un Módulo:", ["Control MSA", "Calendario de Calibración"])
    st.markdown("---")
    
    if st.session_state.user is None:
        st.header("Acceso Administrador")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", use_container_width=True):
            login(email, password)
    else:
        st.success("Sesión Activa")
        if st.button("Cerrar Sesión", use_container_width=True):
            logout()

# RENDERIZADO DE VISTAS SEGÚN MÓDULO Y SESIÓN
if st.session_state.user is None:
    st.title(f"🔬 Consulta - {modulo_activo}")
    st.markdown("---")
    if modulo_activo == "Control MSA":
        modulo_busqueda_msa()
    else:
        modulo_busqueda_calibracion()
else:
    st.title(f"⚙️ Panel de Control - {modulo_activo}")
    tab_dash, tab_consulta, tab_altas, tab_informe = st.tabs([
        "📊 Dashboard", "🔍 Consulta y Escáner", "➕ Altas/Bajas", "📝 Registrar Informe"
    ])
    
    if modulo_activo == "Control MSA":
        with tab_dash: mostrar_dashboard_msa()
        with tab_consulta: modulo_busqueda_msa()
        with tab_altas: modulo_altas_bajas_msa()
        with tab_informe: modulo_informes_msa()
    else:
        with tab_dash: mostrar_dashboard_calibracion()
        with tab_consulta: modulo_busqueda_calibracion()
        with tab_altas: modulo_altas_bajas_calibracion()
        with tab_informe: modulo_informes_calibracion()
