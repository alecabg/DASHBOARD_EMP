import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_authenticator as stauth
import io

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard Finotex", layout="wide", page_icon="📊")

# --- 1. SEGURIDAD ---
hashed_password = "$2b$12$PKSOehzLrF7oZQVkKVE4ZulhZtYmYYEqY.J/J0sQNll.jrLCusKyq"
credentials = {"usernames": {"jorgecaballero@finotex.com": {"name": "Jorge Caballero", "password": hashed_password}}}
authenticator = stauth.Authenticate(credentials, "hr_cookie", "sig_123", cookie_expiry_days=1)

authenticator.login(location='main')

if st.session_state["authentication_status"]:
    
    def load_data(file):
        if file is None: return None
        df = pd.read_excel(file)
        df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        
        # Mapeo de nombres para asegurar gráficas
        for col in df.columns:
            c_low = col.lower()
            if "sueldo" in c_low and "bruto" in c_low: df.rename(columns={col: "Sueldo Mensual (bruto)"}, inplace=True)
            if "sexo" in c_low: df.rename(columns={col: "Sexo"}, inplace=True)
            if "civil" in c_low: df.rename(columns={col: "Edo. Civil"}, inplace=True)
            if "antig" in c_low: df.rename(columns={col: "Antigüedad"}, inplace=True)
            if "mot" in c_low and "baja" in c_low: df.rename(columns={col: "MOT. BAJA"}, inplace=True)
            if "edad" in c_low: df.rename(columns={col: "Edad"}, inplace=True)
            if "hijos" in c_low: df.rename(columns={col: "Hijos"}, inplace=True)

        cols_to_fix = ["Sexo", "Edo. Civil", "Departamento", "Puesto", "Area", "MOT. BAJA", "Hijos"]
        for c in cols_to_fix:
            if c in df.columns:
                df[c] = df[c].fillna("Sin Dato").astype(str).str.strip().replace(['', 'nan', 'None'], 'Sin Dato')
        
        return df

    with st.sidebar:
        st.title(f"Bienvenido, {st.session_state['name']}")
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.divider()
        st.header("1. Cargar Datos")
        uploaded_file = st.file_uploader("Sube el Excel de RRHH", type=["xlsx"])
        
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            st.header("2. Filtros")
            if "Edad" in df_raw.columns:
                min_age, max_age = int(df_raw["Edad"].min()), int(df_raw["Edad"].max())
                age_range = st.slider("Rango de Edad", min_age, max_age, (min_age, max_age))
            
            depto = st.multiselect("Departamento", options=df_raw.get("Departamento", pd.Series([])).unique())
            
            df_selection = df_raw.copy()
            if "Edad" in df_raw.columns:
                df_selection = df_selection[(df_selection["Edad"] >= age_range[0]) & (df_selection["Edad"] <= age_range[1])]
            if depto:
                df_selection = df_selection[df_selection["Departamento"].isin(depto)]
        else:
            df_selection = None

    if df_selection is not None:
        st.title("📊 Panel de Control de Recursos Humanos")
        st.markdown("###") 
        
        # KPIs
        t_emp, t_pay = len(df_selection), df_selection["Sueldo Mensual (bruto)"].sum()
        avg_age = df_selection["Edad"].mean() if "Edad" in df_selection.columns else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Empleados", t_emp)
        m2.metric("Nómina Total", f"${t_pay:,.2f}")
        m3.metric("Edad Promedio", f"{avg_age:.1f} años")
        m4.metric("Sueldo Promedio", f"${(t_pay/t_emp) if t_emp > 0 else 0:,.2f}")

        st.divider()

        # FILA 1: DISTRIBUCIÓN POR DEPARTAMENTO Y DEMOGRAFÍA (POR NÚMERO DE PERSONAS)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Empleados por Departamento")
            # Agrupamos por departamento contando personas (headcount)
            df_dept_count = df_selection.groupby("Departamento").size().reset_index(name='Conteo')
            fig_dept_pie = px.pie(df_dept_count, names="Departamento", values="Conteo", hole=0.5,
                                  template="plotly_white", labels={'Conteo': 'Personas'})
            fig_dept_pie.update_traces(textinfo='value+percent', hovertemplate="<b>%{label}</b><br>Personas: %{value}<extra></extra>")
            st.plotly_chart(fig_dept_pie, use_container_width=True)

        with c2:
            st.subheader("Demografía (Género y Edo. Civil)")
            # Cambiamos values a conteo de filas para que el tamaño sea por personas
            df_sun = df_selection.groupby(["Sexo", "Edo. Civil"]).size().reset_index(name='Personas')
            fig_sun = px.sunburst(df_sun, path=["Sexo", "Edo. Civil"], values="Personas")
            fig_sun.update_traces(hovertemplate="<b>%{label}</b><br>Total: %{value} personas<extra></extra>")
            st.plotly_chart(fig_sun, use_container_width=True)

        st.divider()

        # FILA 2: BAJAS Y NUEVO CHART DE HIJOS
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Motivos de Baja (Total Personas)")
            df_bajas = df_selection[df_selection["MOT. BAJA"] != "Sin Dato"]
            if not df_bajas.empty:
                # Contamos ocurrencias por motivo
                df_bajas_count = df_bajas.groupby("MOT. BAJA").size().reset_index(name='Total')
                fig_pie = px.pie(df_bajas_count, names="MOT. BAJA", values="Total", hole=0.5, 
                                 labels={'MOT. BAJA': 'Motivo'})
                fig_pie.update_traces(textinfo='value+label', hovertemplate="<b>%{label}</b>: %{value} personas<extra></extra>")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No hay datos de bajas registrados.")

        with c4:
            st.subheader("Distribución de Hijos por Departamento")
            if "Hijos" in df_selection.columns:
                # Gráfico de barras seccionado
                fig_hijos = px.histogram(df_selection, x="Hijos", color="Departamento", 
                                        barmode="group", template="plotly_white",
                                        labels={"Hijos": "Número de Hijos", "count": "Cantidad de Empleados"})
                st.plotly_chart(fig_hijos, use_container_width=True)
            else:
                st.warning("Columna 'Hijos' no encontrada.")

        st.divider()

        # FILA 3: ANTIGÜEDAD VS SUELDO
        st.subheader("Relación Antigüedad vs Sueldo")
        if "Antigüedad" in df_selection.columns:
            fig_scat = px.scatter(df_selection, x="Antigüedad", y="Sueldo Mensual (bruto)", 
                                 color="Area", size="Edad", hover_name="Nombre por apellido",
                                 labels={"Sueldo Mensual (bruto)": "Sueldo", "Area": "Área"})
            fig_scat.update_traces(hovertemplate="<b>%{hovertext}</b><br>Sueldo: $%{y:,.2f}<br>Años: %{x}<extra></extra>")
            st.plotly_chart(fig_scat, use_container_width=True)

        with st.expander("🔍 Ver Base de Datos Detallada"):
            st.dataframe(df_selection, use_container_width=True)
            
    else:
        st.info("👋 Por favor, sube el archivo Excel en la barra lateral.")

elif st.session_state["authentication_status"] is False:
    st.error("Credenciales incorrectas")
