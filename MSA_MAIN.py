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
            
        # --- NUEVA SECCIÓN: ACCESO A CARPETA LOCAL ---
        st.markdown("---")
        st.markdown("#### 📁 Archivo del Estudio (Red Local)")
        
        ruta_servidor = equipo.get('link_servidor')
        if ruta_servidor and str(ruta_servidor).strip() not in ['None', '', 'S/D', 'N/A']:
            st.caption("Por políticas de seguridad del navegador desde la nube, copia la ruta de abajo y pégala en tu Explorador de Windows para abrir la carpeta directamente:")
            # Muestra la ruta con un botón integrado de copiado a la derecha
            st.code(ruta_servidor, language="text")
        else:
            st.warning("⚠️ Este equipo no tiene registrada una ruta de servidor local para sus archivos de estudio.")
            
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

def modulo_informes():
    st.subheader("📝 Registrar Nuevo Informe MSA")
    
    id_equipo = st.text_input("ID del Equipo (Ej. BCS-QRO-LAB-MIC001):").strip()
    
    if id_equipo:
        with st.spinner("Consultando datos actuales del equipo..."):
            # AGREGAMOS 'link_servidor' a la consulta SELECT
            res_eq = supabase.table('equipos_msa').select('descripcion, marca, modelo, vigencia_meses, link_servidor').eq('id_equipo', id_equipo).execute()
        
        if res_eq.data:
            equipo = res_eq.data[0]
            vigencia_default = equipo.get('vigencia_meses') if equipo.get('vigencia_meses') else 12
            # Obtenemos el link actual (si es nulo, dejamos texto vacío)
            link_default = equipo.get('link_servidor') if equipo.get('link_servidor') else ""
            
            st.success(f"📦 Equipo confirmado: **{equipo['descripcion']}** ({equipo['marca']} {equipo['modelo']})")
            
            with st.form("form_registro_informe", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    consecutivo = st.text_input("Consecutivo del Informe (Ej. BCS-EST-133-26) *")
                    fecha_informe = st.date_input("Fecha del Estudio *", value=datetime.date.today())
                    studio = st.text_input("Tipo de Estudio (Ej. GRRA, GRRV, LINEALIDAD)")
                    
                with col2:
                    proyecto = st.text_input("Proyecto")
                    ubicacion = st.text_input("Ubicación en Planta")
                    vigencia_estudio = st.number_input(
                        "Vigencia para esta validación (Meses) *", 
                        min_value=1, 
                        value=int(vigencia_default), 
                        step=1
                    )
                
                # Nuevo campo dentro del formulario de informes, precargado con el valor maestro
                link_servidor_estudio = st.text_input(
                    "🔗 Ruta de Carpeta Local para este Estudio", 
                    value=str(link_default),
                    help="Modifica esta ruta si los archivos de este nuevo informe se guardaron en otra carpeta del servidor."
                )
                
                comentario = st.text_area("Comentarios / Observaciones")
                st.markdown("*Campos obligatorios")
                enviado = st.form_submit_button("💾 Guardar Informe y Actualizar Vencimiento", type="primary", use_container_width=True)
                
                if enviado:
                    if not consecutivo:
                        st.error("⚠️ El Consecutivo del Informe es obligatorio.")
                    else:
                        try:
                            fecha_base = pd.to_datetime(fecha_informe)
                            fecha_vencimiento = fecha_base + pd.DateOffset(months=vigencia_estudio)
                            
                            fecha_vencimiento_str = fecha_vencimiento.strftime('%Y-%m-%d')
                            fecha_informe_str = fecha_base.strftime('%Y-%m-%d')
                            
                            # 1. Registrar el informe en la tabla 'informes_msa'
                            nuevo_informe = {
                                "consecutivo": consecutivo.strip(),
                                "fecha": fecha_informe_str,
                                "proyecto": proyecto.strip() if proyecto else None,
                                "ubicacion": ubicacion.strip() if ubicacion else None,
                                "estudio": studio.strip() if studio else None,
                                "comentario": comentario.strip() if comentario else id_equipo
                            }
                            supabase.table('informes_msa').insert(nuevo_informe).execute()
                            
                            # 2. Actualizar el equipo maestro (incluyendo la nueva ruta si cambió)
                            datos_actualizar_eq = {
                                "informe_reciente": consecutivo.strip(),
                                "fecha_vencimiento": fecha_vencimiento_str,
                                "vigencia_meses": vigencia_estudio,
                                "link_servidor": link_servidor_estudio.strip() if link_servidor_estudio else None, # <-- ACTUALIZA EL LINK MAESTRO
                                "estatus": "VIGENTE"
                            }
                            supabase.table('equipos_msa').update(datos_actualizar_eq).eq('id_equipo', id_equipo).execute()
                            
                            st.success(f"✅ Informe **{consecutivo.strip()}** guardado correctamente.")
                            st.info(f"🔄 Equipo **{id_equipo}** actualizado a VIGENTE. Próximo vencimiento: **{fecha_vencimiento_str}**.")
                            
                            if vigencia_estudio != vigencia_default:
                                st.warning(f"⚙️ Nota: La vigencia por defecto del equipo ha sido actualizada a {vigencia_estudio} meses.")
                                
                            st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al procesar la actualización: {e}")
        else:
            st.error(f"❌ El ID de equipo **{id_equipo}** no está registrado.")

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

def modulo_altas_bajas():
    accion = st.radio("Selecciona la acción a realizar:", ["➕ Alta de Equipo", "🔻 Modificar Estatus / Baja"], horizontal=True)
    st.markdown("---")
    
    if accion == "➕ Alta de Equipo":
        st.subheader("Registrar Nuevo Equipo")
        
        with st.form("form_alta_equipo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                id_equipo = st.text_input("ID del Equipo (Ej. BCS-QRO-LAB-MIC002) *")
                descripcion = st.text_input("Descripción (Ej. MICROMETRO) *")
                marca = st.text_input("Marca")
                modelo = st.text_input("Modelo")
                serie = st.text_input("Número de Serie")
                
            with col2:
                ubicacion = st.text_input("Ubicación (Ej. 1. LABORATORIO)")
                estudio = st.text_input("Estudio Requerido (Ej. GRRV)")
                proyecto = st.text_input("Proyecto")
                vigencia = st.number_input("Vigencia (Meses)", min_value=1, value=12, step=1)
                estatus = st.selectbox("Estatus Inicial", ["VIGENTE", "POR VENCER", "VENCIDO", "EN PROCESO", "BAJA"])
            
            # Campo ancho para rutas largas de red local
            link_servidor = st.text_input("🔗 Ruta a la Carpeta Local en Servidor (Opcional)", 
                                          help="Ejemplo: \\\\servidor_local\\compartido\\msa\\micrometro_002\\")
            
            st.markdown("*Campos obligatorios")
            enviado = st.form_submit_button("💾 Guardar Equipo", type="primary", use_container_width=True)
            
            if enviado:
                if not id_equipo or not descripcion:
                    st.error("⚠️ El ID y la Descripción son obligatorios para el alta.")
                else:
                    nuevo_equipo = {
                        "id_equipo": id_equipo.strip(),
                        "descripcion": descripcion.strip(),
                        "marca": marca.strip() if marca else None,
                        "modelo": modelo.strip() if modelo else None,
                        "serie": serie.strip() if serie else None,
                        "ubicacion": ubicacion.strip() if ubicacion else None,
                        "estudio": estudio.strip() if estudio else None,
                        "proyecto": proyecto.strip() if proyecto else None,
                        "vigencia_meses": vigencia,
                        "estatus": estatus,
                        "link_servidor": link_servidor.strip() if link_servidor else None, # <-- NUEVO CAMPO
                        "fecha_creacion": datetime.date.today().strftime('%Y-%m-%d')
                    }
                    try:
                        supabase.table("equipos_msa").insert(nuevo_equipo).execute()
                        st.success(f"✅ Equipo **{id_equipo}** registrado exitosamente en el inventario.")
                    except Exception as e:
                        st.error(f"❌ Error al guardar. Es posible que el ID ya exista. Detalle: {e}")
                        
    else:
        # (La sección de Modificar Estatus / Baja se queda exactamente igual)
        st.subheader("Actualizar Estatus o Dar de Baja")
        id_busqueda = st.text_input("Ingresa el ID del equipo a modificar:")
        
        if st.button("Buscar Equipo"):
            if id_busqueda:
                st.session_state['id_modificar'] = id_busqueda.strip()
        
        if 'id_modificar' in st.session_state:
            id_mod = st.session_state['id_modificar']
            res = supabase.table('equipos_msa').select('descripcion, marca, modelo, estatus').eq('id_equipo', id_mod).execute()
            
            if res.data:
                equipo = res.data[0]
                st.info(f"Modificando: **{equipo['descripcion']}** ({equipo['marca']} {equipo['modelo']})")
                opciones_estatus = ["VIGENTE", "POR VENCER", "VENCIDO", "EN PROCESO", "BAJA"]
                estatus_actual = equipo['estatus'] if equipo['estatus'] in opciones_estatus else "VIGENTE"
                indice_actual = opciones_estatus.index(estatus_actual)
                
                with st.form("form_modificar_estatus"):
                    nuevo_estatus = st.selectbox("Actualizar Estatus", opciones_estatus, index=indice_actual)
                    btn_actualizar = st.form_submit_button("Actualizar Estatus", type="primary")
                    
                    if btn_actualizar:
                        try:
                            supabase.table('equipos_msa').update({'estatus': nuevo_estatus}).eq('id_equipo', id_mod).execute()
                            st.success(f"✅ Estatus de **{id_mod}** actualizado a **{nuevo_estatus}**.")
                            del st.session_state['id_modificar']
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {e}")
            else:
                st.warning("⚠️ No se encontró ningún equipo con ese ID.")
                
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
        modulo_altas_bajas()
        # Aquí irá el CRUD de equipos
        
    with tab_informe:
        modulo_informes()
        # Aquí irá el registro de informes

def mostrar_dashboard():
    st.subheader("📊 Estado General del Laboratorio")
    
    with st.spinner("Cargando inventario consolidado..."):
        # Traemos los datos clave para el listado completo
        res = supabase.table('equipos_msa').select('id_equipo, descripcion, estudio, fecha_creacion, fecha_vencimiento, estatus').execute()
        
    if res.data:
        df_dash = pd.DataFrame(res.data)
        
        # Conteos para las métricas fijas
        total = len(df_dash)
        vigentes = len(df_dash[df_dash['estatus'].str.upper() == 'VIGENTE'])
        por_vencer = len(df_dash[df_dash['estatus'].str.upper() == 'POR VENCER'])
        bajas = len(df_dash[df_dash['estatus'].str.upper() == 'BAJA'])
        vencidos = len(df_dash[df_dash['estatus'].str.upper() == 'VENCIDO'])
        
        # Despliegue de tarjetas de KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔬 Total Equipos", total)
        c2.metric("🟢 Vigentes", vigentes)
        c3.metric("🟡 Por Vencer", por_vencer)
        c4.metric("🔴 Críticos / Bajas", vencidos + bajas)
        
        st.markdown("---")
        st.subheader("📋 Inventario y Control de Vencimientos")
        
        # Renombramos las columnas del DataFrame para que se vea profesional en la UI
        df_visual = df_dash.rename(columns={
            'id_equipo': 'ID Equipo',
            'descripcion': 'Descripción',
            'estudio': 'Estudio',
            'fecha_creacion': 'Fecha Último Estudio',
            'fecha_vencimiento': 'Fecha Vencimiento',
            'estatus': 'Estatus'
        })
        
        # Mostramos la tabla completa. Streamlit permite ordenar columnas y buscar texto nativamente aquí.
        st.dataframe(
            df_visual, 
            use_container_width=True, 
            hide_index=True
        )
        
    else:
        st.info("No se encontraron registros de equipos para mostrar en el listado.")
        
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
