import streamlit as st
import re
import unicodedata

st.set_page_config(
    page_title="TecnoDistribuciones GT",
    page_icon="🚚",
    layout="wide"
)

BODEGAS = ["Guatemala", "Quetzaltenango", "Escuintla", "Cobán"]
DESTINOS = ["Huehuetenango", "San Marcos", "Totonicapán", "Retalhuleu"]

# =========================================================
# ESTILO
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #0f172a;
    color: #e2e8f0;
}

h1, h2, h3 {
    color: #f8fafc;
}

div[data-testid="stMetric"] {
    background: #1e293b;
    padding: 12px;
    border-radius: 12px;
}

.stButton > button[kind="primary"] {
    background-color: #2563eb;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# FUNCIONES
# =========================================================

def normalizar_texto(texto):
    texto = texto.lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = " ".join(
        texto.split()
    )

    return texto


def buscar_numero(texto, patrones):
    for patron in patrones:
        resultado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if resultado:
            return int(resultado.group(1))

    return None


def interpretar_enunciado(texto_original):
    texto = normalizar_texto(
        texto_original
    )

    nombres_bodegas = [
        "guatemala",
        "quetzaltenango",
        "escuintla",
        "coban"
    ]

    nombres_destinos = [
        "huehuetenango",
        "san marcos",
        "totonicapan",
        "retalhuleu"
    ]

    oferta = [None] * 4
    demanda = [None] * 4
    costos = [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None]
    ]

    # =====================================================
    # OFERTA
    # =====================================================

    for i, nombre in enumerate(nombres_bodegas):
        patrones = [
            rf"(\d+)\s+unidades?"
            rf".{{0,40}}?"
            rf"bodega\s+(?:de\s+)?{nombre}",

            rf"bodega\s+(?:de\s+)?{nombre}"
            rf".{{0,50}}?"
            rf"(?:oferta|dispone|tiene|cuenta con)"
            rf".{{0,20}}?"
            rf"(\d+)",

            rf"{nombre}"
            rf".{{0,35}}?"
            rf"(?:oferta|dispone|tiene|cuenta con)"
            rf".{{0,20}}?"
            rf"(\d+)"
        ]

        oferta[i] = buscar_numero(
            texto,
            patrones
        )

    # =====================================================
    # DEMANDA
    # =====================================================

    for j, nombre in enumerate(nombres_destinos):
        patrones = [
            rf"(?:sucursal\s+(?:de\s+)?)?"
            rf"{nombre}"
            rf".{{0,30}}?"
            rf"(?:necesita|requiere|demanda)"
            rf".{{0,15}}?"
            rf"(\d+)",

            rf"(\d+)\s+unidades?"
            rf".{{0,35}}?"
            rf"(?:sucursal\s+(?:de\s+)?)?"
            rf"{nombre}",

            rf"demanda"
            rf".{{0,20}}?"
            rf"{nombre}"
            rf".{{0,15}}?"
            rf"(\d+)"
        ]

        demanda[j] = buscar_numero(
            texto,
            patrones
        )

    # =====================================================
    # COSTOS EN LISTA
    # =====================================================

    for i, nombre in enumerate(nombres_bodegas):
        patrones_lista = [
            rf"costos?"
            rf"(?:\s+de\s+transporte)?"
            rf"\s+(?:desde|de)\s+{nombre}"
            rf".{{0,25}}?"
            rf"(?:son|:)?"
            rf"\s*(\d+)"
            rf"\s*[,;]\s*"
            rf"(\d+)"
            rf"\s*[,;]\s*"
            rf"(\d+)"
            rf"\s*(?:,|y)\s*"
            rf"(\d+)",

            rf"desde\s+{nombre}"
            rf".{{0,25}}?"
            rf"costos?"
            rf".{{0,15}}?"
            rf"(\d+)"
            rf"\s*[,;]\s*"
            rf"(\d+)"
            rf"\s*[,;]\s*"
            rf"(\d+)"
            rf"\s*(?:,|y)\s*"
            rf"(\d+)"
        ]

        resultado = None

        for patron in patrones_lista:
            resultado = re.search(
                patron,
                texto,
                re.IGNORECASE
            )

            if resultado:
                break

        if resultado:
            costos[i] = [
                int(resultado.group(1)),
                int(resultado.group(2)),
                int(resultado.group(3)),
                int(resultado.group(4))
            ]

    # =====================================================
    # COSTOS RUTA POR RUTA
    # =====================================================

    for i, bodega in enumerate(nombres_bodegas):
        for j, destino in enumerate(nombres_destinos):
            if costos[i][j] is not None:
                continue

            patrones = [
                rf"(?:desde|de)\s+{bodega}"
                rf"\s+(?:a|hacia)\s+{destino}"
                rf".{{0,30}}?"
                rf"(?:cuesta|costo|valor|es)?"
                rf".{{0,10}}?"
                rf"(?:q\s*)?"
                rf"(\d+)",

                rf"{bodega}"
                rf".{{0,15}}?"
                rf"(?:a|hacia)\s+{destino}"
                rf".{{0,30}}?"
                rf"(?:costo|cuesta|valor)"
                rf".{{0,15}}?"
                rf"(?:q\s*)?"
                rf"(\d+)"
            ]

            costos[i][j] = buscar_numero(
                texto,
                patrones
            )

    campos_llenos = 0

    for valor in oferta:
        if valor is not None:
            campos_llenos += 1

    for valor in demanda:
        if valor is not None:
            campos_llenos += 1

    for fila in costos:
        for valor in fila:
            if valor is not None:
                campos_llenos += 1

    return oferta, demanda, costos, campos_llenos


def resolver_costo_minimo(
    costos,
    oferta,
    demanda
):
    if any(valor <= 0 for valor in oferta):
        raise ValueError(
            "Los valores de oferta deben ser mayores que cero."
        )

    if any(valor <= 0 for valor in demanda):
        raise ValueError(
            "Los valores de demanda deben ser mayores que cero."
        )

    if any(
        valor < 0
        for fila in costos
        for valor in fila
    ):
        raise ValueError(
            "Los costos no pueden ser negativos."
        )

    total_oferta = sum(oferta)
    total_demanda = sum(demanda)

    if total_oferta != total_demanda:
        raise ValueError(
            f"Problema no balanceado: "
            f"oferta total = {total_oferta} y "
            f"demanda total = {total_demanda}."
        )

    oferta_restante = oferta.copy()
    demanda_restante = demanda.copy()

    asignaciones = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ]

    costo_total = 0
    pasos = []
    numero_paso = 1

    while (
        sum(oferta_restante) > 0
        and
        sum(demanda_restante) > 0
    ):
        costo_minimo = None
        fila_minima = -1
        columna_minima = -1

        for i in range(4):
            if oferta_restante[i] == 0:
                continue

            for j in range(4):
                if demanda_restante[j] == 0:
                    continue

                if (
                    costo_minimo is None
                    or
                    costos[i][j] < costo_minimo
                ):
                    costo_minimo = costos[i][j]
                    fila_minima = i
                    columna_minima = j

        cantidad = min(
            oferta_restante[fila_minima],
            demanda_restante[columna_minima]
        )

        asignaciones[
            fila_minima
        ][
            columna_minima
        ] += cantidad

        costo_parcial = (
            cantidad
            *
            costo_minimo
        )

        costo_total += costo_parcial

        pasos.append({
            "Paso": numero_paso,
            "Ruta": (
                f"{BODEGAS[fila_minima]} → "
                f"{DESTINOS[columna_minima]}"
            ),
            "Costo unitario": f"Q{costo_minimo}",
            "Asignación": cantidad,
            "Subtotal": f"Q{costo_parcial:,}"
        })

        oferta_restante[
            fila_minima
        ] -= cantidad

        demanda_restante[
            columna_minima
        ] -= cantidad

        numero_paso += 1

    return (
        asignaciones,
        costo_total,
        pasos
    )


def inicializar_estado():
    if "enunciado" not in st.session_state:
        st.session_state.enunciado = ""

    for i in range(4):
        st.session_state.setdefault(
            f"oferta_{i}",
            0
        )

        st.session_state.setdefault(
            f"demanda_{i}",
            0
        )

        for j in range(4):
            st.session_state.setdefault(
                f"costo_{i}_{j}",
                0
            )


def limpiar_datos():
    st.session_state.enunciado = ""

    for i in range(4):
        st.session_state[f"oferta_{i}"] = 0
        st.session_state[f"demanda_{i}"] = 0

        for j in range(4):
            st.session_state[f"costo_{i}_{j}"] = 0

    st.session_state.pop(
        "resultado",
        None
    )

    st.session_state.pop(
        "mensaje",
        None
    )


inicializar_estado()

# =========================================================
# ENCABEZADO
# =========================================================

st.title(
    "TECNODISTRIBUCIONES GT"
)

st.caption(
    "Sistema de Optimización de Transporte — "
    "Método de Costo Mínimo"
)

# =========================================================
# INTERPRETAR ENUNCIADO
# =========================================================

st.subheader(
    "Interpretar enunciado"
)

st.text_area(
    "Pegue el problema. El sistema intentará "
    "identificar oferta, demanda y costos.",
    key="enunciado",
    height=140
)

col_interpretar, col_limpiar = st.columns(2)

with col_interpretar:
    interpretar = st.button(
        "INTERPRETAR DATOS",
        type="primary",
        use_container_width=True
    )

with col_limpiar:
    st.button(
        "LIMPIAR",
        use_container_width=True,
        on_click=limpiar_datos
    )

if interpretar:
    if not st.session_state.enunciado.strip():
        st.warning(
            "Pegue primero el enunciado del problema."
        )

    else:
        (
            oferta_interpretada,
            demanda_interpretada,
            costos_interpretados,
            campos_llenos
        ) = interpretar_enunciado(
            st.session_state.enunciado
        )

        for i, valor in enumerate(
            oferta_interpretada
        ):
            if valor is not None:
                st.session_state[
                    f"oferta_{i}"
                ] = valor

        for j, valor in enumerate(
            demanda_interpretada
        ):
            if valor is not None:
                st.session_state[
                    f"demanda_{j}"
                ] = valor

        for i in range(4):
            for j in range(4):
                valor = costos_interpretados[i][j]

                if valor is not None:
                    st.session_state[
                        f"costo_{i}_{j}"
                    ] = valor

        if campos_llenos == 24:
            st.session_state["mensaje"] = (
                "El sistema logró identificar "
                "todos los datos."
            )
        else:
            st.session_state["mensaje"] = (
                f"Se reconocieron {campos_llenos} "
                f"de 24 datos. "
                f"Revise los campos faltantes."
            )

        st.rerun()

if "mensaje" in st.session_state:
    if "todos los datos" in st.session_state["mensaje"]:
        st.success(
            st.session_state["mensaje"]
        )
    else:
        st.warning(
            st.session_state["mensaje"]
        )

# =========================================================
# OFERTA Y DEMANDA
# =========================================================

col_oferta, col_demanda = st.columns(2)

with col_oferta:
    st.subheader(
        "1. Oferta de bodegas"
    )

    for i, bodega in enumerate(BODEGAS):
        st.number_input(
            bodega,
            min_value=0,
            step=1,
            key=f"oferta_{i}"
        )

with col_demanda:
    st.subheader(
        "2. Demanda de sucursales"
    )

    for j, destino in enumerate(DESTINOS):
        st.number_input(
            destino,
            min_value=0,
            step=1,
            key=f"demanda_{j}"
        )

# =========================================================
# COSTOS
# =========================================================

st.subheader(
    "3. Costos de transporte por ruta"
)

cabeceras = st.columns(
    [1.4, 1, 1, 1, 1]
)

cabeceras[0].markdown(
    "**Bodega / Sucursal**"
)

for j, destino in enumerate(DESTINOS):
    cabeceras[j + 1].markdown(
        f"**{destino}**"
    )

for i, bodega in enumerate(BODEGAS):
    fila = st.columns(
        [1.4, 1, 1, 1, 1]
    )

    fila[0].markdown(
        f"**{bodega}**"
    )

    for j in range(4):
        with fila[j + 1]:
            st.number_input(
                f"{bodega}-{DESTINOS[j]}",
                min_value=0,
                step=1,
                key=f"costo_{i}_{j}",
                label_visibility="collapsed"
            )

# =========================================================
# RESUMEN
# =========================================================

oferta_actual = [
    int(
        st.session_state[
            f"oferta_{i}"
        ]
    )
    for i in range(4)
]

demanda_actual = [
    int(
        st.session_state[
            f"demanda_{i}"
        ]
    )
    for i in range(4)
]

total_oferta = sum(
    oferta_actual
)

total_demanda = sum(
    demanda_actual
)

m1, m2, m3 = st.columns(3)

m1.metric(
    "Oferta total",
    total_oferta
)

m2.metric(
    "Demanda total",
    total_demanda
)

if (
    total_oferta == 0
    and
    total_demanda == 0
):
    estado = "Ingrese los datos"

elif total_oferta == total_demanda:
    estado = "Problema balanceado"

else:
    estado = "Problema no balanceado"

m3.metric(
    "Estado",
    estado
)

# =========================================================
# CALCULAR SOLUCIÓN
# =========================================================

if st.button(
    "CALCULAR SOLUCIÓN",
    type="primary",
    use_container_width=True
):
    try:
        costos_actuales = []

        for i in range(4):
            fila = []

            for j in range(4):
                fila.append(
                    int(
                        st.session_state[
                            f"costo_{i}_{j}"
                        ]
                    )
                )

            costos_actuales.append(
                fila
            )

        (
            asignaciones,
            costo_total,
            pasos
        ) = resolver_costo_minimo(
            costos_actuales,
            oferta_actual,
            demanda_actual
        )

        st.session_state[
            "resultado"
        ] = {
            "asignaciones": asignaciones,
            "costo_total": costo_total,
            "pasos": pasos,
            "oferta": oferta_actual,
            "demanda": demanda_actual
        }

    except ValueError as error:
        st.error(
            str(error)
        )

# =========================================================
# RESULTADOS
# =========================================================

if "resultado" in st.session_state:
    resultado = st.session_state[
        "resultado"
    ]

    st.divider()

    st.header(
        "Resultados del Método de Costo Mínimo"
    )

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Oferta total",
        sum(resultado["oferta"])
    )

    r2.metric(
        "Demanda total",
        sum(resultado["demanda"])
    )

    r3.metric(
        "Estado",
        "Problema balanceado"
    )

    st.subheader(
        "Asignaciones realizadas"
    )

    tabla_asignaciones = []

    for i, bodega in enumerate(BODEGAS):
        fila = {
            "Bodega": bodega
        }

        for j, destino in enumerate(DESTINOS):
            fila[destino] = (
                resultado[
                    "asignaciones"
                ][i][j]
            )

        tabla_asignaciones.append(
            fila
        )

    st.dataframe(
        tabla_asignaciones,
        use_container_width=True,
        hide_index=True
    )

    st.success(
        "COSTO TOTAL DE TRANSPORTE: "
        f"Q {resultado['costo_total']:,}"
    )

    st.subheader(
        "Procedimiento"
    )

    st.dataframe(
        resultado["pasos"],
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "El Método de Costo Mínimo genera una "
        "solución básica factible inicial; "
        "por sí solo no garantiza la solución "
        "óptima global."
    )
