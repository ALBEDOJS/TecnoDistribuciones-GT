import streamlit as st
import re
import unicodedata

st.set_page_config(page_title="TecnoDistribuciones GT", page_icon="🚚", layout="wide")

BODEGAS = ["Guatemala", "Quetzaltenango", "Escuintla", "Cobán"]
DESTINOS = ["Huehuetenango", "San Marcos", "Totonicapán", "Retalhuleu"]

st.markdown("""
<style>
.stApp {background-color:#0f172a;color:#e2e8f0}
h1,h2,h3 {color:#f8fafc}
div[data-testid="stMetric"] {background:#1e293b;padding:12px;border-radius:12px}
</style>
""", unsafe_allow_html=True)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())

def buscar_numero(texto, patrones):
    for patron in patrones:
        r = re.search(patron, texto, re.IGNORECASE)
        if r:
            return int(r.group(1))
    return None

def interpretar_enunciado(texto_original):
    texto = normalizar_texto(texto_original)
    nb = ["guatemala", "quetzaltenango", "escuintla", "coban"]
    nd = ["huehuetenango", "san marcos", "totonicapan", "retalhuleu"]

    oferta = [None]*4
    demanda = [None]*4
    costos = [[None]*4 for _ in range(4)]

    for i, nombre in enumerate(nb):
        patrones = [
            rf"(\d+)\s+unidades?.{{0,40}}?bodega\s+(?:de\s+)?{nombre}",
            rf"bodega\s+(?:de\s+)?{nombre}.{{0,50}}?(?:oferta|dispone|tiene|cuenta con).{{0,20}}?(\d+)",
            rf"{nombre}.{{0,35}}?(?:oferta|dispone|tiene|cuenta con).{{0,20}}?(\d+)"
        ]
        oferta[i] = buscar_numero(texto, patrones)

    for j, nombre in enumerate(nd):
        patrones = [
            rf"(?:sucursal\s+(?:de\s+)?)?{nombre}.{{0,30}}?(?:necesita|requiere|demanda).{{0,15}}?(\d+)",
            rf"(\d+)\s+unidades?.{{0,35}}?(?:sucursal\s+(?:de\s+)?)?{nombre}",
            rf"demanda.{{0,20}}?{nombre}.{{0,15}}?(\d+)"
        ]
        demanda[j] = buscar_numero(texto, patrones)

    for i, nombre in enumerate(nb):
        patrones_lista = [
            rf"costos?(?:\s+de\s+transporte)?\s+(?:desde|de)\s+{nombre}.{{0,25}}?(?:son|:)?\s*(\d+)\s*[,;]\s*(\d+)\s*[,;]\s*(\d+)\s*(?:,|y)\s*(\d+)",
            rf"desde\s+{nombre}.{{0,25}}?costos?.{{0,15}}?(\d+)\s*[,;]\s*(\d+)\s*[,;]\s*(\d+)\s*(?:,|y)\s*(\d+)"
        ]
        r = None
        for patron in patrones_lista:
            r = re.search(patron, texto, re.IGNORECASE)
            if r:
                break
        if r:
            costos[i] = [int(r.group(k)) for k in range(1,5)]

    for i, bodega in enumerate(nb):
        for j, destino in enumerate(nd):
            if costos[i][j] is not None:
                continue
            patrones = [
                rf"(?:desde|de)\s+{bodega}\s+(?:a|hacia)\s+{destino}.{{0,30}}?(?:cuesta|costo|valor|es)?.{{0,10}}?(?:q\s*)?(\d+)",
                rf"{bodega}.{{0,15}}?(?:a|hacia)\s+{destino}.{{0,30}}?(?:costo|cuesta|valor).{{0,15}}?(?:q\s*)?(\d+)"
            ]
            costos[i][j] = buscar_numero(texto, patrones)

    campos = sum(v is not None for v in oferta)
    campos += sum(v is not None for v in demanda)
    campos += sum(v is not None for fila in costos for v in fila)
    return oferta, demanda, costos, campos

def resolver_costo_minimo(costos, oferta, demanda):
    if any(v <= 0 for v in oferta):
        raise ValueError("La oferta debe ser mayor que cero.")
    if any(v <= 0 for v in demanda):
        raise ValueError("La demanda debe ser mayor que cero.")
    if any(v < 0 for fila in costos for v in fila):
        raise ValueError("Los costos no pueden ser negativos.")
    if sum(oferta) != sum(demanda):
        raise ValueError(f"Problema no balanceado: oferta {sum(oferta)} y demanda {sum(demanda)}.")

    oferta_r = oferta.copy()
    demanda_r = demanda.copy()
    asignaciones = [[0]*4 for _ in range(4)]
    costo_total = 0
    pasos = []
    paso = 1

    while sum(oferta_r) > 0 and sum(demanda_r) > 0:
        minimo = None
        fi = cj = -1
        for i in range(4):
            if oferta_r[i] == 0:
                continue
            for j in range(4):
                if demanda_r[j] == 0:
                    continue
                if minimo is None or costos[i][j] < minimo:
                    minimo = costos[i][j]
                    fi, cj = i, j

        cantidad = min(oferta_r[fi], demanda_r[cj])
        asignaciones[fi][cj] += cantidad
        subtotal = cantidad * minimo
        costo_total += subtotal
        pasos.append({
            "Paso": paso,
            "Ruta": f"{BODEGAS[fi]} → {DESTINOS[cj]}",
            "Costo unitario": f"Q{minimo}",
            "Asignación": cantidad,
            "Subtotal": f"Q{subtotal:,}"
        })
        oferta_r[fi] -= cantidad
        demanda_r[cj] -= cantidad
        paso += 1

    return asignaciones, costo_total, pasos

for i in range(4):
    st.session_state.setdefault(f"oferta_{i}", 0)
    st.session_state.setdefault(f"demanda_{i}", 0)
    for j in range(4):
        st.session_state.setdefault(f"costo_{i}_{j}", 0)
st.session_state.setdefault("enunciado", "")

st.title("TECNODISTRIBUCIONES GT")
st.caption("Sistema de Optimización de Transporte — Método de Costo Mínimo")

st.subheader("Interpretar enunciado")
st.text_area(
    "Pegue el problema. El sistema intentará identificar oferta, demanda y costos.",
    key="enunciado",
    height=140
)

c1, c2 = st.columns(2)
with c1:
    if st.button("INTERPRETAR DATOS", type="primary", use_container_width=True):
        if not st.session_state.enunciado.strip():
            st.warning("Pegue primero el enunciado del problema.")
        else:
            oferta, demanda, costos, campos = interpretar_enunciado(st.session_state.enunciado)

            for i, v in enumerate(oferta):
                if v is not None:
                    st.session_state[f"oferta_{i}"] = v
            for j, v in enumerate(demanda):
                if v is not None:
                    st.session_state[f"demanda_{j}"] = v
            for i in range(4):
                for j in range(4):
                    if costos[i][j] is not None:
                        st.session_state[f"costo_{i}_{j}"] = costos[i][j]

            st.session_state["mensaje"] = (
                "El sistema logró identificar todos los datos."
                if campos == 24
                else f"Se reconocieron {campos} de 24 datos. Revise los campos faltantes."
            )
            st.rerun()

with c2:
    if st.button("LIMPIAR", use_container_width=True):
        st.session_state.enunciado = ""
        for i in range(4):
            st.session_state[f"oferta_{i}"] = 0
            st.session_state[f"demanda_{i}"] = 0
            for j in range(4):
                st.session_state[f"costo_{i}_{j}"] = 0
        st.session_state.pop("resultado", None)
        st.session_state.pop("mensaje", None)
        st.rerun()

if "mensaje" in st.session_state:
    if "todos" in st.session_state["mensaje"]:
        st.success(st.session_state["mensaje"])
    else:
        st.warning(st.session_state["mensaje"])

izq, der = st.columns(2)

with izq:
    st.subheader("1. Oferta de bodegas")
    for i, nombre in enumerate(BODEGAS):
        st.number_input(nombre, min_value=0, step=1, key=f"oferta_{i}")

with der:
    st.subheader("2. Demanda de sucursales")
    for j, nombre in enumerate(DESTINOS):
        st.number_input(nombre, min_value=0, step=1, key=f"demanda_{j}")

st.subheader("3. Costos de transporte por ruta")
h = st.columns([1.4,1,1,1,1])
h[0].markdown("**Bodega / Sucursal**")
for j, nombre in enumerate(DESTINOS):
    h[j+1].markdown(f"**{nombre}**")

for i, bodega in enumerate(BODEGAS):
    cols = st.columns([1.4,1,1,1,1])
    cols[0].markdown(f"**{bodega}**")
    for j in range(4):
        with cols[j+1]:
            st.number_input(
                f"{bodega}-{DESTINOS[j]}",
                min_value=0,
                step=1,
                key=f"costo_{i}_{j}",
                label_visibility="collapsed"
            )

oferta = [int(st.session_state[f"oferta_{i}"]) for i in range(4)]
demanda = [int(st.session_state[f"demanda_{i}"]) for i in range(4)]

m1, m2, m3 = st.columns(3)
m1.metric("Oferta total", sum(oferta))
m2.metric("Demanda total", sum(demanda))

if sum(oferta) == 0 and sum(demanda) == 0:
    estado = "Ingrese los datos"
elif sum(oferta) == sum(demanda):
    estado = "Problema balanceado"
else:
    estado = "Problema no balanceado"
m3.metric("Estado", estado)

if st.button("CALCULAR SOLUCIÓN", type="primary", use_container_width=True):
    try:
        costos = [[int(st.session_state[f"costo_{i}_{j}"]) for j in range(4)] for i in range(4)]
        asignaciones, costo_total, pasos = resolver_costo_minimo(costos, oferta, demanda)
        st.session_state["resultado"] = {
            "asignaciones": asignaciones,
            "costo_total": costo_total,
            "pasos": pasos
        }
    except ValueError as e:
        st.error(str(e))

if "resultado" in st.session_state:
    r = st.session_state["resultado"]
    st.divider()
    st.header("Resultados del Método de Costo Mínimo")

    filas = []
    for i, bodega in enumerate(BODEGAS):
        fila = {"Bodega": bodega}
        for j, destino in enumerate(DESTINOS):
            fila[destino] = r["asignaciones"][i][j]
        filas.append(fila)

    st.subheader("Asignaciones realizadas")
    st.dataframe(filas, use_container_width=True, hide_index=True)

    st.success(f"COSTO TOTAL DE TRANSPORTE: Q {r['costo_total']:,}")

    st.subheader("Procedimiento")
    st.dataframe(r["pasos"], use_container_width=True, hide_index=True)

    st.info(
        "El Método de Costo Mínimo genera una solución básica factible inicial; "
        "por sí solo no garantiza la solución óptima global."
    )
