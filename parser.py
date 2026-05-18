# ==========================================
                # PROCESAMIENTO DE EQUIPOS
                # ==========================================
                st.info("Iniciando procesamiento de Equipos MSA...")
                
                # skiprows=3 ignora las 3 líneas de leyenda (Vigente, Baja, etc.)
                df_equipos = pd.read_csv(archivo_equipos, skiprows=3)
                df_equipos.columns = df_equipos.columns.str.strip()
                df_equipos = df_equipos.dropna(subset=['ID'])

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
                    'ESTATUS': 'estatus'
                })

                # MAGIA: Filtramos la tabla para quedarnos SOLO con las columnas válidas,
                # descartando cualquier "Unnamed: X" que Excel haya colado.
                columnas_validas_eq = [
                    'id_equipo', 'ubicacion', 'descripcion', 'estudio', 'proyecto', 
                    'marca', 'modelo', 'serie', 'vigencia_meses', 'informe_reciente', 
                    'fecha_creacion', 'fecha_vencimiento', 'estatus'
                ]
                datos_equipos = datos_equipos[columnas_validas_eq]

                datos_equipos = datos_equipos.astype(object).replace({np.nan: None, pd.NA: None})
                records_equipos = datos_equipos.to_dict(orient='records')
                
                res_eq = supabase.table('equipos_msa').upsert(records_equipos).execute()
                st.success(f"✅ {len(res_eq.data)} equipos insertados/actualizados correctamente.")

                # ==========================================
                # PROCESAMIENTO DE INFORMES
                # ==========================================
                st.info("Iniciando procesamiento de Informes...")
                
                # skiprows=1 ignora la primera fila que dice "LISTADO DE MSA"
                df_informes = pd.read_csv(archivo_informes, skiprows=1)
                df_informes.columns = df_informes.columns.str.strip()
                df_informes = df_informes.dropna(subset=['CONSECUTIVO'])

                def limpiar_fecha(fecha_str):
                    try:
                        dt = dateparser.parse(str(fecha_str), languages=['es'])
                        return dt.strftime('%Y-%m-%d') if dt else None
                    except:
                        return None

                df_informes['FECHA'] = df_informes['FECHA'].apply(limpiar_fecha)

                datos_informes = df_informes.rename(columns={
                    'CONSECUTIVO': 'consecutivo',
                    'FECHA': 'fecha',
                    'PROYECTO': 'proyecto',
                    'UBICACION': 'ubicacion',
                    'ESTUDIO': 'estudio',
                    'COMENTARIO': 'comentario'
                })

                # Filtramos columnas basura de los informes también
                columnas_validas_inf = [
                    'consecutivo', 'fecha', 'proyecto', 'ubicacion', 'estudio', 'comentario'
                ]
                datos_informes = datos_informes[columnas_validas_inf]

                datos_informes = datos_informes.astype(object).replace({np.nan: None, pd.NA: None})
                records_informes = datos_informes.to_dict(orient='records')

                res_inf = supabase.table('informes_msa').upsert(records_informes).execute()
                st.success(f"✅ {len(res_inf.data)} informes insertados/actualizados correctamente.")
                
                st.balloons()