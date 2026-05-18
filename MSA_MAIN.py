import streamlit as st
from supabase import create_client, Client
import datetime
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Control MSA - Metrología", page_icon="🔬", layout="wide")

# Inicializar conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def vista_publica():
    st.title("🔬 Consulta de Equipos MSA")
    st.markdown("---")
    
    # Dividimos en dos pestañas para que la interfaz móvil sea más limpia
    tab_escaner, tab_manual = st.tabs(["📷 Escáner QR", "⌨️ Búsqueda Manual"])
    
    with tab_escaner:
        st.info("Enfoca el código QR del equipo y toma la foto para consultar su estatus.")
        imagen_camara = st.camera_input("Escáner QR")
        
        if imagen_camara is not None:
            with st.spinner("Analizando código QR..."):
                # 1. Convertir la imagen de Streamlit a un formato de OpenCV
                bytes_data = imagen_camara.getvalue()
                cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                
                # 2. Decodificar usando pyzbar
                codigos_qr = decode(cv2_img)
                
                if codigos_qr:
                    # Extraer el texto del primer QR encontrado
                    id_escaneado = codigos_qr[0].data.decode('utf-8').strip()
                    st.success(f"✅ Código detectado: **{id_escaneado}**")
                    
                    # 3. Llamar a la función de consulta
                    mostrar_resultado_equipo(id_escaneado)
                else:
                    st.error("❌ No se detectó ningún código QR. Intenta mejorar la iluminación o el enfoque.")

    with tab_manual:
        st.info("Ingresa el ID manualmente si la etiqueta está dañada.")
        id_busqueda = st.text_input("ID del equipo (Ej. BCS-QRO-LAB-MIC001):", key="buscador_publico")
        
        if st.button("🔍 Buscar Equipo", type="primary", use_container_width=True):
            if id_busqueda:
                mostrar_resultado_equipo(id_busqueda.strip())
            else:
                st.warning("⚠️ Por favor, ingresa un ID válido.")

def mostrar_resultado_equipo(id_equipo):
    st.markdown("---")
    with st.spinner("Buscando en la base de datos..."):
        # Consulta a Supabase
        respuesta = supabase.table('equipos_msa').select("*").eq('id_equipo', id_equipo).execute()
        
    if respuesta.data:
        equipo = respuesta.data[0]
        
        # Lógica visual para el estatus y fechas
        estatus = equipo['estatus']
        fecha_venc = equipo['fecha_vencimiento']
        
        # Tarjeta visual con colores dinámicos
        if estatus == 'VIGENTE':
            st.success(f"### 🟢 Estatus: {estatus}")
        elif estatus == 'POR VENCER' or estatus == 'EN PROCESO':
            st.warning(f"### 🟡 Estatus: {estatus}")
        else:
            st.error(f"### 🔴 Estatus: {estatus}")
            
        # Layout en dos columnas para los datos del equipo
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
            st.write(f"**Vencimiento:** {fecha_venc}")
            
    else:
        st.error(f"❌ No se encontró ningún equipo registrado con el ID: **{id_equipo}**")
        
# --- GESTIÓN DE SESIÓN (LOGIN) ---
if "user" not in st.session_state:
    st.session_state.user = None

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.rerun()
    except Exception as e:
        # Aquí imprimimos el error exacto que nos devuelve Supabase
        st.error(f"Detalle del error: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- MÓDULO REUTILIZABLE DE BÚSQUEDA ---
def modulo_busqueda():
    tab_escaner, tab_manual = st.tabs(["📷 Escáner QR", "⌨️ Búsqueda Manual"])
    
    with tab_escaner:
        st.info("Enfoca el código QR del equipo y toma la foto para consultar su estatus.")
        imagen_camara = st.camera_input("Escáner QR", key="camara_busqueda") # Key única
        
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
                    st.error("❌ No se detectó ningún código QR. Intenta mejorar la iluminación o el enfoque.")

    with tab_manual:
        st.info("Ingresa el ID manualmente si la etiqueta está dañada.")
        id_busqueda = st.text_input("ID del equipo (Ej. BCS-QRO-LAB-MIC001):", key="texto_busqueda")
        
        if st.button("🔍 Buscar Equipo", type="primary", use_container_width=True):
            if id_busqueda:
                mostrar_resultado_equipo(id_busqueda.strip())
            else:
                st.warning("⚠️ Por favor, ingresa un ID válido.")

# (La función mostrar_resultado_equipo se queda exactamente igual que la versión anterior)

# --- VISTAS DE LA APLICACIÓN ---
def vista_publica():
    st.title("🔬 Consulta de Equipos MSA")
    st.markdown("---")
    modulo_busqueda()

def vista_admin():
    st.title("⚙️ Panel de Control Metrología")
    
    # Agregamos la pestaña de consulta al panel de admin
    tab_dash, tab_consulta, tab_altas, tab_informe = st.tabs([
        "📊 Dashboard", "🔍 Consulta y Escáner", "➕ Altas/Bajas", "📝 Registrar Informe"
    ])
    
    with tab_dash:
        mostrar_dashboard()
        
    with tab_consulta:
        modulo_busqueda()
    
    with tab_altas:
        st.write("Formulario para dar de alta nuevos equipos o darlos de baja.")
        # Aquí irá el CRUD de equipos
        
    with tab_informe:
        st.write("Formulario para registrar un nuevo estudio y actualizar la fecha de vencimiento.")
        # Aquí irá el registro de informes

def mostrar_dashboard():
    st.subheader("Resumen de Equipos")
    
    with st.spinner("Cargando métricas..."):
        # Traemos solo la columna estatus para hacer el conteo rápido
        res = supabase.table('equipos_msa').select('estatus').execute()
        
    if res.data:
        df_dash = pd.DataFrame(res.data)
        
        total = len(df_dash)
        vigentes = len(df_dash[df_dash['estatus'].str.upper() == 'VIGENTE'])
        por_vencer = len(df_dash[df_dash['estatus'].str.upper() == 'POR VENCER'])
        bajas = len(df_dash[df_dash['estatus'].str.upper() == 'BAJA'])
        vencidos = len(df_dash[df_dash['estatus'].str.upper() == 'VENCIDO'])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 Total Equipos", total)
        c2.metric("🟢 Vigentes", vigentes)
        c3.metric("🟡 Por Vencer", por_vencer)
        c4.metric("🔴 Vencidos / Bajas", vencidos + bajas)
        
        st.markdown("---")
        st.write("*(Aquí podemos agregar un gráfico de barras o una tabla filtrada con los equipos críticos próximos a vencer)*")
    else:
        st.info("No hay datos suficientes para mostrar el dashboard.")

# --- ENRUTADOR PRINCIPAL ---
with st.sidebar:
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

# Mostrar la vista correspondiente según el estado de la sesión
if st.session_state.user is None:
    vista_publica()
else:
    vista_admin()
