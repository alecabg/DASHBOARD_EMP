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
    
    # --- 2. FUNCIÓN DE CARGA ROBUSTA ---
    def load_data(file):
        if file is None: return None
        df = pd.read_excel(file)
        
        # Limpieza de encabezados (Regex para saltos de línea)
        df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        
        # Mapeo de columnas críticas
        for col in df.columns:
            c_low = col.lower()
            if "sueldo" in c_low and "bruto" in c_low: df.rename(columns={col: "Sueldo Mensual (bruto)"}, inplace=True)
            if "sexo" in c_low: df.rename(columns={col: "Sexo"}, inplace=True)
            if "civil" in c_low: df.rename(columns={col: "Edo. Civil"}, inplace=True)
            if "antig" in c_low: df.rename(columns={col: "Antigüedad"}, inplace=True)
            if "mot" in c_low and "baja" in c_low: df.rename(columns={col: "MOT. BAJA"}, inplace=True)
            if "edad" in c_low: df.rename(columns={col: "Edad"}, inplace=True)
            if "hijos" in c_low: df.rename(columns={col: "Hijos"}, inplace=True)

        # Limpieza de Nulos para evitar el ValueError ('FEMENINO', '')
        cols_to_fix = ["Sexo", "Edo. Civil", "Departamento", "Puesto", "Area", "MOT. BAJA", "Hijos"]
        for c in cols_to_fix:
            if c in df.columns:
                df[c] = df[c].fillna("Sin Dato").astype(str).str.strip().replace(['', 'nan', 'None'], 'Sin Dato')
        
        return df

    # --- 3. SIDEBAR ---
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

    # --- 4. DASHBOARD PRINCIPAL ---
    if df_selection is not None:
        st.title("📊 Panel de Control de Recursos Humanos")
        st.markdown("---")
        
        # KPIs
        t_emp, t_pay = len(df_selection), df_selection["Sueldo Mensual (bruto)"].sum()
        avg_age = df_selection["Edad"].astype(float).mean() if "Edad" in df_selection.columns else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Empleados", t_emp)
        m2.metric("Nómina Total", f"${t_pay:,.2f}")
        m3.metric("Edad Promedio", f"{avg_age:.1f} años")
        m4.metric("Sueldo Promedio", f"${(t_pay/t_emp) if t_emp > 0 else 0:,.2f}")

        st.markdown("###")
        st.divider()
        st.markdown("###")

        # FILA 1: DONA DE DEPTO Y SUNBURST DEMOGRÁFICO
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Distribución por Departamento (Personas)")
            # Agregamos conteo y sueldo para el hover
            df_dept_agg = df_selection.groupby("Departamento").agg(
                Personas=("Sueldo Mensual (bruto)", "count"),
                Sueldo_Total=("Sueldo Mensual (bruto)", "sum")
            ).reset_index()
            
            fig_dept = px.pie(df_dept_agg, names="Departamento", values="Personas", hole=0.5,
                             custom_data=["Sueldo_Total"], template="plotly_white")
            # Limpiamos hover: Departamento arriba, sueldo abajo
            fig_dept.update_traces(
                textinfo='value+percent', 
                hovertemplate="<b>%{label}</b><br>Personas: %{value}<br>Nómina: $%{customdata[0]:,.2f}<extra></extra>"
            )
            st.plotly_chart(fig_dept, use_container_width=True)

        with c2:
            st.subheader("Demografía (Tamaño por Headcount)")
            # Tamaño por personas, incluyendo sueldo en hover
            df_sun_agg = df_selection.groupby(["Sexo", "Edo. Civil"]).agg(
                Personas=("Suel
