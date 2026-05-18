import streamlit as st
import pandas as pd
import numpy as np  # <-- AGREGA ESTA LÍNEA
from supabase import create_client, Client
import dateparser

# Configuración de página
st.set_page_config(page_title="Migración MSA", page_icon="⚙️")
st.title("⚙️ Migración de Datos MSA a Supabase")

# Explicación breve
st.markdown("""
Sube tus archivos CSV exportados desde Excel para actualizar la base de datos de Metrología.
Asegúrate de subir el archivo de **Equipos** y el de **Informes**.
""")

# 1. Conexión segura a Supabase usando st.secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error conectando a Supabase. Revisa tus secretos en Streamlit Cloud.")
    st.stop()

# 2. Subida de archivos
col1, col2 = st.columns(2)
with col1:
    archivo_equipos = st.file_uploader("Sube el CSV de Equipos", type=["csv"])
with col2:
    archivo_informes = st.file_uploader("Sube el CSV de Informes", type=["csv"])

# 3. Botón de ejecución
if st.button("🚀 Ejecutar Migración", type="primary"):
    if not archivo_equipos or not archivo_informes:
        st.warning("⚠️ Por favor, sube ambos archivos CSV antes de continuar.")
    else:
        with st.spinner("Procesando y enviando datos a Supabase..."):
            try:
# Función global para traducir CUALQUIER fecha al formato de Supabase
                # Funciones globales de limpieza
                def limpiar_fecha(fecha_str):
                    if pd.isna(fecha_str) or str(fecha_str).strip() in ['', 'NaT', 'None']:
                        return None
                    try:
                        dt = dateparser.parse(str(fecha_str), languages=['es'])
                        return dt.strftime('%Y-%m-%d') if dt else None
                    except:
                        return None

                def limpiar_entero(val):
                    if pd.isna(val) or str(val).strip().upper() in ['', 'NONE', 'NAN', 'NAT', 'S/D', 'N/A', '-']:
                        return None
                    try:
                        return int(float(val))
                    except:
                        return None

                # ==========================================
                # PROCESAMIENTO DE EQUIPOS
                # ==========================================
                st.info("Iniciando procesamiento de Equipos MSA...")
                
                archivo_equipos.seek(0)
                df_temp_eq = pd.read_csv(archivo_equipos, header=None)
                fila_header_eq = df_temp_eq[df_temp_eq.apply(lambda r: 'ID' in r.astype(str).str.strip().values, axis=1)].index[0]
                
                archivo_equipos.seek(0)
                df_equipos = pd.read_csv(archivo_equipos, skiprows=fila_header_eq)
                df_equipos.columns = df_equipos.columns.str.strip()
                df_equipos = df_equipos.dropna(subset=['ID'])
                
                # ---> ¡NUEVA LÍNEA! Eliminamos IDs duplicados, conservando el último <---
                df_equipos = df_equipos.drop_duplicates(subset=['ID'], keep='last')

                if 'FECHA DE CREACION' in df_equipos.columns:
                    df_equipos['FECHA DE CREACION'] = df_equipos['FECHA DE CREACION'].apply(limpiar_fecha)
                if 'FECHA DE VENC.' in df_equipos.columns:
                    df_equipos['FECHA DE VENC.'] = df_equipos['FECHA DE VENC.'].apply(limpiar_fecha)
                if 'VIGENCIA' in df_equipos.columns:
                    df_equipos['VIGENCIA'] = df_equipos['VIGENCIA'].apply(limpiar_entero)

                datos_equipos = df_equipos.rename(columns={
                    'ID': 'id_equipo',
                    'UBICACIÓN': 'ubicacion',
                    'DESCRIPCION': 'descripcion',
                    'ESTUDIO': 'estudio',
                    'PROYECTO': 'proyecto',
                    'MARCA': 'marca',
                    'MODELO': 'modelo',
                    'SERIE': 'serie',
                    'VIGENCIA': 'vigencia_meses',
                    'INFORME': 'informe_reciente',
                    'FECHA DE CREACION': 'fecha_creacion',
                    'FECHA DE VENC.': 'fecha_vencimiento',
                    'ESTATUS': 'estatus',
                    'LINK': 'link_servidor'  # <-- NUEVA LÍNEA MAPEO
                })

                columnas_validas_eq = [
                    'id_equipo', 'ubicacion', 'descripcion', 'estudio', 'proyecto', 
                    'marca', 'modelo', 'serie', 'vigencia_meses', 'informe_reciente', 
                    'fecha_creacion', 'fecha_vencimiento', 'estatus'
                ]
                datos_equipos = datos_equipos[columnas_validas_eq]

                datos_equipos = datos_equipos.astype(object).replace({np.nan: None, pd.NA: None})
                records_equipos = datos_equipos.to_dict(orient='records')
                
                res_eq = supabase.table('equipos_msa').upsert(records_equipos).execute()
                st.success(f"✅ {len(res_eq.data)} equipos procesados sin duplicados y subidos con éxito.")

                # ==========================================
                # PROCESAMIENTO DE INFORMES
                # ==========================================
                st.info("Iniciando procesamiento de Informes...")
                
                archivo_informes.seek(0)
                df_temp_inf = pd.read_csv(archivo_informes, header=None)
                fila_header_inf = df_temp_inf[df_temp_inf.apply(lambda r: 'CONSECUTIVO' in r.astype(str).str.strip().values, axis=1)].index[0]
                
                archivo_informes.seek(0)
                df_informes = pd.read_csv(archivo_informes, skiprows=fila_header_inf)
                df_informes.columns = df_informes.columns.str.strip()
                df_informes = df_informes.dropna(subset=['CONSECUTIVO'])
                
                # ---> ¡NUEVA LÍNEA! Eliminamos consecutivos duplicados, conservando el último <---
                df_informes = df_informes.drop_duplicates(subset=['CONSECUTIVO'], keep='last')

                if 'FECHA' in df_informes.columns:
                    df_informes['FECHA'] = df_informes['FECHA'].apply(limpiar_fecha)

                datos_informes = df_informes.rename(columns={
                    'CONSECUTIVO': 'consecutivo',
                    'FECHA': 'fecha',
                    'PROYECTO': 'proyecto',
                    'UBICACION': 'ubicacion',
                    'ESTUDIO': 'estudio',
                    'COMENTARIO': 'comentario'
                })

                columnas_validas_eq = [
                    'id_equipo', 'ubicacion', 'descripcion', 'estudio', 'proyecto', 
                    'marca', 'modelo', 'serie', 'vigencia_meses', 'informe_reciente', 
                    'fecha_creacion', 'fecha_vencimiento', 'estatus', 'link_servidor' # <-- NUEVA LÍNEA FILTRO
                ]
                datos_informes = datos_informes[columnas_validas_inf]

                datos_informes = datos_informes.astype(object).replace({np.nan: None, pd.NA: None})
                records_informes = datos_informes.to_dict(orient='records')

                res_inf = supabase.table('informes_msa').upsert(records_informes).execute()
                st.success(f"✅ {len(res_inf.data)} informes procesados sin duplicados y subidos con éxito.")
                
                st.balloons()
            except Exception as e:
                st.error(f"❌ Ocurrió un error durante la migración: {e}")
