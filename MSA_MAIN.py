import streamlit as st
from supabase import create_client, Client
import datetime

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
    
    # Usamos un contenedor centrado para la búsqueda
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("💡 **Tip:** Puedes escribir el ID o usar un escáner QR.")
        # El text_input es perfecto para escáneres físicos tipo pistola
        id_busqueda = st.text_input("ID del equipo (Ej. BCS-QRO-LAB-MIC001):", key="buscador_publico")
        
        if st.button("🔍 Buscar Equipo", type="primary", use_container_width=True):
            if id_busqueda:
                # Limpiamos espacios accidentales
                id_limpio = id_busqueda.strip()
                mostrar_resultado_equipo(id_limpio)
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

# --- VISTAS DE LA APLICACIÓN ---
def vista_publica():
    st.title("🔬 Consulta de Equipos MSA")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Búsqueda Rápida")
        # Aquí luego integraremos el componente de la cámara (streamlit-qrcode-scanner)
        id_busqueda = st.text_input("Ingresa o escanea el ID del equipo (Ej. BCS-QRO-LAB-MIC001):")
        if st.button("Buscar Equipo", type="primary", use_container_width=True):
            if id_busqueda:
                mostrar_resultado_equipo(id_busqueda)
            else:
                st.warning("Por favor, ingresa un ID válido.")

def mostrar_resultado_equipo(id_equipo):
    # Consulta a Supabase
    respuesta = supabase.table('equipos_msa').select("*").eq('id_equipo', id_equipo).execute()
    
    if respuesta.data:
        equipo = respuesta.data[0]
        st.success("✅ Equipo localizado")
        
        # Tarjeta de información
        st.write(f"**Descripción:** {equipo['descripcion']}")
        st.write(f"**Ubicación:** {equipo['ubicacion']}")
        st.write(f"**Marca/Modelo:** {equipo['marca']} / {equipo['modelo']}")
        st.write(f"**Estudio MSA:** {equipo['estudio']}")
        
        # Lógica visual para el estatus
        estatus = equipo['estatus']
        if estatus == 'VIGENTE':
            st.info(f"🟢 Estatus: **{estatus}** (Vence: {equipo['fecha_vencimiento']})")
        elif estatus == 'POR VENCER':
            st.warning(f"🟡 Estatus: **{estatus}** (Vence: {equipo['fecha_vencimiento']})")
        else:
            st.error(f"🔴 Estatus: **{estatus}**")
    else:
        st.error("No se encontró ningún equipo con ese ID en la base de datos.")

def vista_admin():
    st.title("⚙️ Panel de Control Metrología")
    st.markdown(f"Bienvenido. Has iniciado sesión correctamente.")
    
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Altas/Bajas", "📝 Registrar Informe"])
    
    with tab1:
        st.write("Aquí pondremos indicadores: Equipos por vencer, métricas generales, etc.")
    
    with tab2:
        st.write("Formulario para dar de alta nuevos equipos o darlos de baja.")
        
    with tab3:
        st.write("Formulario para registrar un nuevo estudio y actualizar la fecha de vencimiento.")

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
