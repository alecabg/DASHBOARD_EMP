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
        uploaded_file = st.file_uploader("Sube el Excel de RRHH", type=["xlsx"])
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            st.header("Filtros")
            depto = st.multiselect("Departamento", options=df_raw.get("Departamento", pd.Series([])).unique())
            df_selection = df_raw.copy()
            if depto: df_selection = df_selection[df_selection["Departamento"].isin(depto)]
        else:
            df_selection = None

    if df_selection is not None:
        st.title("📊 Panel de Control Recursos Humanos")
        
        # --- KPIs ---
        t_emp, t_pay = len(df_selection), df_selection["Sueldo Mensual (bruto)"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Empleados", t_emp)
        m2.metric("Nómina Total", f"${t_pay:,.2f}")
        m3.metric("Sueldo Promedio", f"${(t_pay/t_emp) if t_emp > 0 else 0:,.2f}")

        st.divider()

        # --- FILA 1: MODIFICACIÓN 1 Y 2 (HEADCOUNT + SALARIO) ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Distribución por Departamento")
            # Agrupamos por personas (Headcount) y sumamos sueldo
            df_dept = df_selection.groupby("Departamento").agg(
                Personas=("Sueldo Mensual (bruto)", "count"),
                Sueldo_Total=("Sueldo Mensual (bruto)", "sum")
            ).reset_index()
            
            fig_dept = px.pie(df_dept, names="Departamento", values="Personas", hole=0.5,
                             custom_data=["Sueldo_Total"], template="plotly_white")
            fig_dept.update_traces(
                textinfo='value+percent', 
                hovertemplate="<b>Departamento: %{label}</b><br>Personas: %{value}<br>Nómina: $%{customdata[0]:,.2f}<extra></extra>"
            )
            st.plotly_chart(fig_dept, use_container_width=True)

        with c2:
            st.subheader("Demografía (Tamaño por Personas)")
            # MODIFICACIÓN 2: Tamaño por personas, incluyendo salario en hover
            df_sun_agg = df_selection.groupby(["Sexo", "Edo. Civil"]).agg(
                Personas=("Sueldo Mensual (bruto)", "count"),
                Sueldo_Total=("Sueldo Mensual (bruto)", "sum")
            ).reset_index()
            
            fig_sun = px.sunburst(df_sun_agg, path=["Sexo", "Edo. Civil"], values="Personas",
                                 custom_data=["Sueldo_Total"],
                                 color="Sexo", color_discrete_map={"MASCULINO": "#636EFA", "FEMENINO": "#EF553B"})
            fig_sun.update_traces(hovertemplate="<b>%{label}</b><br>Total: %{value} personas<br>Nómina: $%{customdata[0]:,.2f}<extra></extra>")
            st.plotly_chart(fig_sun, use_container_width=True)

        st.divider()

        # --- FILA 2: MODIFICACIÓN 1 (BAJAS) Y MODIFICACIÓN 3 (HIJOS CLEAN) ---
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Motivos de Baja (Total Personas)")
            df_bajas = df_selection[df_selection["MOT. BAJA"] != "Sin Dato"].copy()
            if not df_bajas.empty:
                df_bajas_agg = df_bajas.groupby("MOT. BAJA").agg(
                    Total=("Sueldo Mensual (bruto)", "count"),
                    Impacto_Nomina=("Sueldo Mensual (bruto)", "sum")
                ).reset_index()
                
                fig_baja = px.pie(df_bajas_agg, names="MOT. BAJA", values="Total", hole=0.5)
                fig_baja.update_traces(
                    textinfo='value+label', 
                    hovertemplate="<b>Motivo: %{label}</b><br>Personas: %{value}<br>Nómina Perdida: $%{custom_data[0]:,.2f}<extra></extra>"
                )
                st.plotly_chart(fig_baja, use_container_width=True)
            else:
                st.info("No hay datos de bajas registrados.")

        with c4:
            st.subheader("Hijos por Departamento (Vista Apilada)")
            if "Hijos" in df_selection.columns:
                # MODIFICACIÓN 3: Agrupación horizontal apilada (mucho más limpia)
                fig_hijos = px.histogram(
                    df_selection, y="Departamento", x="Sueldo Mensual (bruto)", 
                    color="Hijos", barmode="stack", orientation="h",
                    histfunc="count", template="plotly_white",
                    labels={"Sueldo Mensual (bruto)": "Cantidad de Empleados"}
                )
                # Limpieza de hover para eliminar "Departamento="
                fig_hijos.update_traces(hovertemplate="<b>Depto: %{y}</b><br>Hijos: %{fullData.name}<br>Empleados: %{x}<extra></extra>")
                st.plotly_chart(fig_hijos, use_container_width=True)
            else:
                st.warning("Columna 'Hijos' no detectada.")

        # --- FILA 3: SCATTER ---
        st.divider()
        st.subheader("Relación Antigüedad vs Sueldo")
        if "Antigüedad" in df_selection.columns:
            fig_scat = px.scatter(df_selection, x="Antigüedad", y="Sueldo Mensual (bruto)", 
                                 color="Area", size="Edad", hover_name="Nombre por apellido",
                                 labels={"Sueldo Mensual (bruto)": "Sueldo", "Area": "Área"})
            fig_scat.update_traces(hovertemplate="<b>%{hovertext}</b><br>Sueldo: $%{y:,.2f}<br>Antigüedad: %{x} años<extra></extra>")
            st.plotly_chart(fig_scat, use_container_width=True)

        with st.expander("🔍 Ver Base de Datos Detallada"):
            st.dataframe(df_selection, use_container_width=True)
            
    else:
        st.info("👋 Sube el archivo Excel en la barra lateral para comenzar.")

elif st.session_state["authentication_status"] is False:
    st.error("Credenciales incorrectas")
