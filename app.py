import json
import os
import random
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from difflib import SequenceMatcher

import altair as alt
import pandas as pd
import requests
import streamlit as st

ARCHIVO_BIBLIOTECA = "biblioteca.csv"
GOOGLE_SHEET_NAME_DEFAULT = "libros"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
IMAGEN_LIBRO_ENCONTRADO = "libro_encontrado.jpeg"

IMAGENES_CABECERA = [
    "banner_1.jpeg",
    "banner_1.jpg",
    "banner_1.png",
    "banner_2.jpeg",
    "banner_2.jpg",
    "banner_2.png",
    "banner_3.jpeg",
    "banner_3.jpg",
    "banner_3.png",
    "banner_4.jpeg",
    "banner_4.jpg",
    "banner_4.png",
    "banner_5.jpeg",
    "banner_5.jpg",
    "banner_5.png",
]

COLUMNAS_BIBLIOTECA = [
    "isbn",
    "titulo",
    "autores",
    "editorial",
    "fecha_publicacion",
    "categorias",
    "descripcion",
    "portada",
    "fuente",
    "ubicacion",
    "estanteria",
    "balda",
    "estado",
    "notas",
    "fecha_alta",
]


st.set_page_config(
    page_title="Biblioteca Enrique",
    page_icon="📚",
    layout="wide"
)


def obtener_password_app():
    try:
        return st.secrets.get("APP_PASSWORD", "")
    except Exception:
        return os.environ.get("APP_PASSWORD", "")


def comprobar_acceso():
    if st.session_state.get("acceso_autorizado", False):
        return True

    password_correcta = obtener_password_app()

    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(200, 162, 74, 0.18), transparent 30%),
                linear-gradient(135deg, #f8f1e6 0%, #efe1cd 100%);
        }

        .block-container {
            max-width: 620px;
            padding-top: 6rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("📚 La biblioteca de Enrique")
    st.subheader("Acceso privado")
    st.write("Introduce la contraseña para acceder a la biblioteca.")

    with st.form("formulario_acceso"):
        password_introducida = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Escribe la contraseña...",
            key="password_acceso"
        )

        enviar_password = st.form_submit_button("Entrar")

    if enviar_password:
        if not password_correcta:
            st.error("La contraseña de la app todavía no está configurada.")
        elif password_introducida == password_correcta:
            st.session_state["acceso_autorizado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    return False


if not comprobar_acceso():
    st.stop()


imagenes_cabecera_disponibles = [
    imagen for imagen in IMAGENES_CABECERA
    if os.path.exists(imagen)
]

col_titulo, col_espacio_cabecera, col_foto_cabecera = st.columns([1.75, 1.05, 0.9])

with col_titulo:
    st.title("📚 La biblioteca de Enrique")
    st.write("App para registrar libros mediante código de barras o ISBN.")

with col_foto_cabecera:
    if imagenes_cabecera_disponibles:
        imagen_cabecera = random.choice(imagenes_cabecera_disponibles)
        st.image(imagen_cabecera, width="stretch")

st.markdown(
    """
    <style>
    :root {
        --fondo-papel: #f4efe6;
        --tarjeta: #fffaf0;
        --tarjeta-oscura: #efe2cc;
        --texto-principal: #2f2a24;
        --texto-secundario: #6f6256;
        --madera: #8b5e34;
        --madera-oscura: #5f3b1f;
        --verde-biblioteca: #2f5d50;
        --verde-biblioteca-claro: #3f7667;
        --dorado: #c8a24a;
        --borde-suave: rgba(95, 59, 31, 0.18);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(200, 162, 74, 0.18), transparent 30%),
            linear-gradient(135deg, #f8f1e6 0%, #efe1cd 100%);
        color: var(--texto-principal);
    }

    .block-container {
        padding-top: 4.75rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }

    h1, h2, h3 {
        color: var(--madera-oscura) !important;
        letter-spacing: -0.02em;
    }

    p, label, span, div {
        color: var(--texto-principal);
    }

    [data-testid="stHeader"] {
        background: rgba(244, 239, 230, 0.85);
        backdrop-filter: blur(8px);
    }

    [data-testid="stMetric"] {
        background: rgba(255, 250, 240, 0.88);
        border: 1px solid var(--borde-suave);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 10px 24px rgba(95, 59, 31, 0.08);
    }

    [data-testid="stMetric"] label,
    [data-testid="stMetric"] div {
        color: var(--texto-principal) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 250, 240, 0.78);
        border: 1px solid var(--borde-suave) !important;
        border-radius: 18px !important;
        box-shadow: 0 12px 28px rgba(95, 59, 31, 0.08);
    }

    div[role="radiogroup"] {
        display: flex;
        flex-wrap: nowrap;
        gap: 0.45rem;
        border-bottom: 2px solid rgba(139, 94, 52, 0.28);
        padding-bottom: 0;
        margin-top: -3.25rem;
        margin-bottom: 2.8rem;
        max-width: 940px;
        white-space: nowrap;
    }

    div[role="radiogroup"] label {
        border: 1px solid rgba(139, 94, 52, 0.24);
        border-bottom: none;
        border-radius: 0.85rem 0.85rem 0 0;
        padding: 0.55rem 0.95rem;
        background: rgba(255, 250, 240, 0.62);
        min-height: 2.5rem;
        box-shadow: 0 -2px 0 rgba(139, 94, 52, 0.05) inset;
        flex-shrink: 0;
    }

    div[role="radiogroup"] label:hover {
        background: rgba(255, 250, 240, 0.92);
        border-color: rgba(139, 94, 52, 0.42);
    }

    div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(180deg, #fffaf0 0%, #f0dfc3 100%);
        border-color: rgba(95, 59, 31, 0.55);
        box-shadow: 0 -3px 0 var(--dorado) inset, 0 0 18px rgba(200, 162, 74, 0.18);
        font-weight: 800;
    }

    div[role="radiogroup"] input {
        display: none;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(180deg, var(--verde-biblioteca-claro), var(--verde-biblioteca));
        color: #fffaf0 !important;
        border: 1px solid rgba(47, 93, 80, 0.75);
        border-radius: 12px;
        font-weight: 700;
        box-shadow: 0 8px 18px rgba(47, 93, 80, 0.16);
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(180deg, #477f70, #244a40);
        border-color: var(--dorado);
        color: white !important;
    }

    input, textarea, select {
        background-color: #fffdf7 !important;
        border-color: rgba(139, 94, 52, 0.25) !important;
        color: var(--texto-principal) !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #1f2129 !important;
        border-color: rgba(139, 94, 52, 0.35) !important;
        color: #fffaf0 !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #fffaf0 !important;
    }

    div[data-baseweb="select"] input {
        color: #fffaf0 !important;
        -webkit-text-fill-color: #fffaf0 !important;
    }

    div[data-baseweb="select"] svg {
        fill: #fffaf0 !important;
        color: #fffaf0 !important;
    }

    div[data-baseweb="select"] [class*="singleValue"],
    div[data-baseweb="select"] [class*="placeholder"],
    div[data-baseweb="select"] [class*="valueContainer"] {
        color: #fffaf0 !important;
    }

    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] ul,
    div[data-baseweb="menu"] li {
        background-color: #1f2129 !important;
        color: #fffaf0 !important;
    }

    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] li:hover {
        background-color: #2f5d50 !important;
        color: #fffaf0 !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--borde-suave);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 12px 26px rgba(95, 59, 31, 0.08);
    }

    div[data-testid="stAlert"] {
        border-radius: 14px;
        border: 1px solid rgba(139, 94, 52, 0.14);
    }

    [data-testid="stElementToolbar"],
    [data-testid="StyledFullScreenButton"],
    [data-testid="stElementToolbarButton"],
    button[title="View fullscreen"],
    button[title="Fullscreen"],
    details[title="Click to view actions"],
    .vega-embed summary,
    .vega-embed .vega-actions,
    .vega-actions,
    .vega-actions a {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    [data-testid="stImage"] img {
        border-radius: 14px;
        border: 10px solid #fff8e8;
        outline: 3px solid rgba(95, 59, 31, 0.45);
        box-shadow:
            0 3px 0 rgba(200, 162, 74, 0.55),
            0 16px 34px rgba(95, 59, 31, 0.22);
        max-height: 240px;
        object-fit: contain;
        background: rgba(255, 250, 240, 0.75);
        margin-left: auto;
    }

    hr {
        border-color: rgba(139, 94, 52, 0.25) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)




def limpiar_isbn(isbn):
    isbn_limpio = isbn.strip().upper()
    isbn_limpio = re.sub(r"[^0-9X]", "", isbn_limpio)
    return isbn_limpio


def normalizar_texto_busqueda(texto):
    texto = (texto or "").strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def obtener_tokens_significativos(texto):
    texto = normalizar_texto_busqueda(texto).lower()
    palabras_vacias = {
        "a", "al", "de", "del", "el", "en", "la", "las", "lo", "los", "un", "una", "unos", "unas",
        "y", "o", "por", "para", "con", "sin", "sobre", "the", "of", "and"
    }
    tokens = re.findall(r"[a-z0-9]+", texto)
    return [token for token in tokens if token not in palabras_vacias and len(token) > 2]


def calcular_puntuacion_resultado_texto(titulo_buscado, autor_buscado, titulo_resultado, autores_resultado):
    titulo_buscado_norm = normalizar_texto_busqueda(titulo_buscado).lower()
    autor_buscado_norm = normalizar_texto_busqueda(autor_buscado).lower()
    titulo_resultado_norm = normalizar_texto_busqueda(titulo_resultado).lower()
    autores_resultado_norm = normalizar_texto_busqueda(autores_resultado).lower()

    if not titulo_buscado_norm or not titulo_resultado_norm:
        return 0

    puntuacion = 0
    similitud_titulo = SequenceMatcher(None, titulo_buscado_norm, titulo_resultado_norm).ratio()
    puntuacion += similitud_titulo * 65

    tokens_buscados = obtener_tokens_significativos(titulo_buscado_norm)
    tokens_resultado = set(obtener_tokens_significativos(titulo_resultado_norm))

    if tokens_buscados:
        coincidencias = sum(1 for token in tokens_buscados if token in tokens_resultado)
        cobertura = coincidencias / len(tokens_buscados)
        puntuacion += cobertura * 25

        if cobertura < 0.6:
            puntuacion -= 30

    if autor_buscado_norm:
        tokens_autor = obtener_tokens_significativos(autor_buscado_norm)
        coincidencias_autor = sum(1 for token in tokens_autor if token in autores_resultado_norm)
        if tokens_autor:
            cobertura_autor = coincidencias_autor / len(tokens_autor)
            puntuacion += cobertura_autor * 30
            if cobertura_autor == 0:
                puntuacion -= 25

    if len(titulo_resultado_norm) > len(titulo_buscado_norm) * 2.2:
        puntuacion -= 15

    return max(round(puntuacion, 1), 0)


def extraer_isbnes_google_books(info):
    identificadores = info.get("industryIdentifiers", []) or []
    isbnes = []
    for identificador in identificadores:
        valor = limpiar_isbn(identificador.get("identifier", ""))
        if valor and valor not in isbnes:
            isbnes.append(valor)
    return ", ".join(isbnes)


def crear_libro_desde_google_books_info(info, isbn_original, fuente="Google Books por título/autor"):
    return {
        "fuente": fuente,
        "isbn": isbn_original,
        "titulo": info.get("title", "Título desconocido"),
        "autores": ", ".join(info.get("authors", ["Autor desconocido"])),
        "editorial": info.get("publisher", "Editorial desconocida"),
        "fecha_publicacion": info.get("publishedDate", "Fecha desconocida"),
        "categorias": ", ".join(info.get("categories", ["Sin categoría"])),
        "descripcion": info.get("description", "Sin descripción"),
        "portada": info.get("imageLinks", {}).get("thumbnail", ""),
    }


def crear_libro_desde_open_library_doc(info, isbn_original, fuente="Open Library por título/autor"):
    autores = info.get("author_name", [])
    autores_texto = ", ".join(autores) if autores else "Autor desconocido"

    editoriales = info.get("publisher", [])
    editorial_texto = ", ".join(editoriales[:3]) if editoriales else "Editorial desconocida"

    portada = ""
    if info.get("cover_i"):
        portada = f"https://covers.openlibrary.org/b/id/{info['cover_i']}-L.jpg"

    return {
        "fuente": fuente,
        "isbn": isbn_original,
        "titulo": info.get("title", "Título desconocido"),
        "autores": autores_texto,
        "editorial": editorial_texto,
        "fecha_publicacion": str(info.get("first_publish_year", "Fecha desconocida")),
        "categorias": ", ".join(info.get("subject", ["Sin categoría"])[:6]) if info.get("subject") else "Sin categoría",
        "descripcion": "Sin descripción",
        "portada": portada,
    }


def es_isbn10_valido(isbn):
    isbn = limpiar_isbn(isbn)

    if len(isbn) != 10:
        return False

    total = 0

    for posicion, caracter in enumerate(isbn):
        if caracter == "X" and posicion == 9:
            valor = 10
        elif caracter.isdigit():
            valor = int(caracter)
        else:
            return False

        total += (10 - posicion) * valor

    return total % 11 == 0


def es_isbn13_valido(isbn):
    isbn = limpiar_isbn(isbn)

    if len(isbn) != 13 or not isbn.isdigit():
        return False

    total = 0

    for posicion, caracter in enumerate(isbn):
        multiplicador = 1 if posicion % 2 == 0 else 3
        total += int(caracter) * multiplicador

    return total % 10 == 0


def es_codigo_basura(isbn):
    isbn = limpiar_isbn(isbn)

    if not isbn:
        return True

    solo_digitos = isbn.replace("X", "")

    if solo_digitos and len(set(solo_digitos)) == 1:
        return True

    return False


def es_isbn_valido(isbn):
    isbn = limpiar_isbn(isbn)

    if es_codigo_basura(isbn):
        return False

    return es_isbn10_valido(isbn) or es_isbn13_valido(isbn)

def obtener_secret(nombre, valor_por_defecto=""):
    try:
        return st.secrets.get(nombre, valor_por_defecto)
    except Exception:
        return os.environ.get(nombre, valor_por_defecto)


def obtener_config_google_sheets():
    sheet_id = obtener_secret("GOOGLE_SHEET_ID", "")
    sheet_name = obtener_secret("GOOGLE_SHEET_NAME", GOOGLE_SHEET_NAME_DEFAULT)

    credenciales = None

    try:
        if "gcp_service_account" in st.secrets:
            credenciales = dict(st.secrets["gcp_service_account"])
    except Exception:
        credenciales = None

    if not credenciales:
        credenciales_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")
        if credenciales_json:
            try:
                credenciales = json.loads(credenciales_json)
            except Exception:
                credenciales = None

    return sheet_id, sheet_name, credenciales


def google_sheets_configurado():
    sheet_id, sheet_name, credenciales = obtener_config_google_sheets()
    return bool(sheet_id and sheet_name and credenciales)


def obtener_worksheet_google_sheets():
    sheet_id, sheet_name, credenciales = obtener_config_google_sheets()

    if not sheet_id or not credenciales:
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as error:
        st.error(f"Faltan librerías para conectar con Google Sheets: {error}")
        return None

    try:
        credentials = Credentials.from_service_account_info(
            credenciales,
            scopes=GOOGLE_SCOPES
        )
        cliente = gspread.authorize(credentials)
        spreadsheet = cliente.open_by_key(sheet_id)
        return spreadsheet.worksheet(sheet_name)
    except Exception as error:
        st.error(f"No se ha podido conectar con Google Sheets: {error}")
        return None


def preparar_dataframe_biblioteca(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_BIBLIOTECA)

    df = df.astype(str).fillna("")

    for columna in COLUMNAS_BIBLIOTECA:
        if columna not in df.columns:
            df[columna] = ""

    return df[COLUMNAS_BIBLIOTECA]


def cargar_biblioteca_desde_csv():
    if os.path.exists(ARCHIVO_BIBLIOTECA):
        df = pd.read_csv(ARCHIVO_BIBLIOTECA, dtype=str).fillna("")
        return preparar_dataframe_biblioteca(df)

    return pd.DataFrame(columns=COLUMNAS_BIBLIOTECA)


def cargar_biblioteca_desde_google_sheets():
    worksheet = obtener_worksheet_google_sheets()

    if worksheet is None:
        return cargar_biblioteca_desde_csv()

    try:
        valores = worksheet.get_all_values()

        if not valores:
            worksheet.update([COLUMNAS_BIBLIOTECA])
            return pd.DataFrame(columns=COLUMNAS_BIBLIOTECA)

        cabeceras = valores[0]
        filas = valores[1:]
        df = pd.DataFrame(filas, columns=cabeceras)
        return preparar_dataframe_biblioteca(df)

    except Exception as error:
        st.error(f"No se ha podido leer la biblioteca desde Google Sheets: {error}")
        return cargar_biblioteca_desde_csv()


def cargar_biblioteca():
    if google_sheets_configurado():
        return cargar_biblioteca_desde_google_sheets()

    return cargar_biblioteca_desde_csv()


def guardar_biblioteca_en_csv(df):
    df = preparar_dataframe_biblioteca(df)
    df.to_csv(ARCHIVO_BIBLIOTECA, index=False)


def guardar_biblioteca_en_google_sheets(df):
    worksheet = obtener_worksheet_google_sheets()

    if worksheet is None:
        guardar_biblioteca_en_csv(df)
        return

    try:
        df = preparar_dataframe_biblioteca(df)
        filas = df.astype(str).values.tolist()
        valores = [COLUMNAS_BIBLIOTECA] + filas
        worksheet.clear()
        worksheet.update(valores, value_input_option="USER_ENTERED")
    except Exception as error:
        st.error(f"No se ha podido guardar la biblioteca en Google Sheets: {error}")


def guardar_biblioteca(df):
    if google_sheets_configurado():
        guardar_biblioteca_en_google_sheets(df)
    else:
        guardar_biblioteca_en_csv(df)


def obtener_nombre_autor_open_library(author_key, timeout=3):
    try:
        url = f"https://openlibrary.org{author_key}.json"
        respuesta = requests.get(url, timeout=timeout)

        if respuesta.status_code != 200:
            return "Autor desconocido"

        datos = respuesta.json()
        return datos.get("name", "Autor desconocido")

    except Exception:
        return "Autor desconocido"


def buscar_en_google_books(isbn, timeout=10, busqueda_flexible=False):
    try:
        url = "https://www.googleapis.com/books/v1/volumes"

        if busqueda_flexible:
            consulta = isbn
            fuente = "Google Books flexible"
        else:
            consulta = f"isbn:{isbn}"
            fuente = "Google Books ISBN exacto"

        respuesta = requests.get(
            url,
            params={
                "q": consulta,
                "maxResults": 5,
                "printType": "books",
                "country": "ES",
            },
            timeout=timeout
        )

        if respuesta.status_code != 200:
            return None

        datos = respuesta.json()

        if datos.get("totalItems", 0) == 0 or not datos.get("items"):
            return None

        info = datos["items"][0]["volumeInfo"]

        return {
            "fuente": fuente,
            "isbn": isbn,
            "titulo": info.get("title", "Sin título"),
            "autores": ", ".join(info.get("authors", ["Autor desconocido"])),
            "editorial": info.get("publisher", "Editorial desconocida"),
            "fecha_publicacion": info.get("publishedDate", "Fecha desconocida"),
            "categorias": ", ".join(info.get("categories", ["Sin categoría"])),
            "descripcion": info.get("description", "Sin descripción"),
            "portada": info.get("imageLinks", {}).get("thumbnail", None),
        }

    except Exception:
        return None


# --- Búsqueda por título/autor en Google Books ---
def buscar_candidatos_google_books_por_texto(titulo, autor="", isbn_original="", timeout=15):
    candidatos = []
    candidatos_vistos = set()

    try:
        titulo = normalizar_texto_busqueda(titulo)
        autor = normalizar_texto_busqueda(autor)

        if not titulo:
            return []

        consultas = []

        if autor:
            consultas.append(f'"{titulo}" "{autor}"')
            consultas.append(f'{titulo} {autor}')
            consultas.append(f'intitle:{titulo} inauthor:{autor}')

        consultas.append(f'"{titulo}"')
        consultas.append(titulo)

        url = "https://www.googleapis.com/books/v1/volumes"

        for consulta in consultas:
            respuesta = requests.get(
                url,
                params={
                    "q": consulta,
                    "maxResults": 20,
                    "langRestrict": "es",
                    "printType": "books",
                    "orderBy": "relevance",
                    "country": "ES",
                },
                timeout=timeout
            )

            if respuesta.status_code != 200:
                continue

            datos = respuesta.json()

            if datos.get("totalItems", 0) == 0 or not datos.get("items"):
                continue

            for item in datos.get("items", []):
                info = item.get("volumeInfo", {})
                titulo_encontrado = info.get("title", "")
                autores_encontrados = ", ".join(info.get("authors", []))

                if not titulo_encontrado:
                    continue

                puntuacion = calcular_puntuacion_resultado_texto(
                    titulo,
                    autor,
                    titulo_encontrado,
                    autores_encontrados
                )

                if puntuacion < 65:
                    continue

                clave = f"google|{normalizar_texto_busqueda(titulo_encontrado).lower()}|{normalizar_texto_busqueda(autores_encontrados).lower()}"
                if clave in candidatos_vistos:
                    continue
                candidatos_vistos.add(clave)

                libro = crear_libro_desde_google_books_info(info, isbn_original)
                candidatos.append({
                    "libro": libro,
                    "titulo": libro["titulo"],
                    "autores": libro["autores"],
                    "editorial": libro["editorial"],
                    "fecha_publicacion": libro["fecha_publicacion"],
                    "fuente": libro["fuente"],
                    "isbn_original": isbn_original,
                    "isbn_encontrado": extraer_isbnes_google_books(info),
                    "puntuacion": puntuacion,
                })

        return sorted(candidatos, key=lambda candidato: candidato["puntuacion"], reverse=True)

    except Exception:
        return []


def buscar_en_google_books_por_texto(titulo, autor="", isbn_original="", timeout=15):
    candidatos = buscar_candidatos_google_books_por_texto(titulo, autor, isbn_original, timeout)
    if candidatos:
        return candidatos[0]["libro"]
    return None


def buscar_en_open_library(isbn, timeout=10):
    try:
        url = f"https://openlibrary.org/isbn/{isbn}.json"
        respuesta = requests.get(url, timeout=timeout)

        if respuesta.status_code != 200:
            return None

        info = respuesta.json()

        autores = []
        for autor in info.get("authors", []):
            author_key = autor.get("key")
            if author_key:
                autores.append(obtener_nombre_autor_open_library(author_key, timeout=3))

        autores_texto = ", ".join(autores) if autores else "Autor desconocido"

        portada = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

        descripcion = info.get("description", "Sin descripción")
        if isinstance(descripcion, dict):
            descripcion = descripcion.get("value", "Sin descripción")

        return {
            "fuente": "Open Library",
            "isbn": isbn,
            "titulo": info.get("title", "Sin título"),
            "autores": autores_texto,
            "editorial": ", ".join(info.get("publishers", ["Editorial desconocida"])),
            "fecha_publicacion": info.get("publish_date", "Fecha desconocida"),
            "categorias": ", ".join(info.get("subjects", ["Sin categoría"])) if "subjects" in info else "Sin categoría",
            "descripcion": descripcion,
            "portada": portada,
        }

    except Exception:
        return None


def convertir_isbn13_a_isbn10(isbn):
    isbn = limpiar_isbn(isbn)

    if len(isbn) != 13 or not isbn.startswith("978"):
        return None

    base = isbn[3:12]
    total = 0

    for posicion, caracter in enumerate(base):
        total += (10 - posicion) * int(caracter)

    resto = total % 11
    digito = 11 - resto

    if digito == 10:
        digito_control = "X"
    elif digito == 11:
        digito_control = "0"
    else:
        digito_control = str(digito)

    return base + digito_control


def convertir_isbn10_a_isbn13(isbn):
    isbn = limpiar_isbn(isbn)

    if len(isbn) != 10:
        return None

    base = "978" + isbn[:9]
    total = 0

    for posicion, caracter in enumerate(base):
        multiplicador = 1 if posicion % 2 == 0 else 3
        total += int(caracter) * multiplicador

    digito_control = (10 - (total % 10)) % 10
    return base + str(digito_control)


def obtener_variantes_isbn(isbn):
    isbn_limpio = limpiar_isbn(isbn)
    variantes = [isbn_limpio]

    isbn10 = convertir_isbn13_a_isbn10(isbn_limpio)
    if isbn10 and isbn10 not in variantes:
        variantes.append(isbn10)

    isbn13 = convertir_isbn10_a_isbn13(isbn_limpio)
    if isbn13 and isbn13 not in variantes:
        variantes.append(isbn13)

    return variantes


def buscar_en_open_library_books_api(isbn, timeout=25):
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        respuesta = requests.get(url, timeout=timeout)

        if respuesta.status_code != 200:
            return None

        datos = respuesta.json()
        clave = f"ISBN:{isbn}"

        if clave not in datos:
            return None

        info = datos[clave]

        autores = []
        for autor in info.get("authors", []):
            nombre = autor.get("name")
            if nombre:
                autores.append(nombre)

        autores_texto = ", ".join(autores) if autores else "Autor desconocido"

        editoriales = []
        for editorial in info.get("publishers", []):
            nombre = editorial.get("name")
            if nombre:
                editoriales.append(nombre)

        editorial_texto = ", ".join(editoriales) if editoriales else "Editorial desconocida"

        categorias = []
        for categoria in info.get("subjects", [])[:8]:
            nombre = categoria.get("name")
            if nombre:
                categorias.append(nombre)

        categorias_texto = ", ".join(categorias) if categorias else "Sin categoría"

        portada = ""
        if isinstance(info.get("cover"), dict):
            portada = info["cover"].get("large") or info["cover"].get("medium") or info["cover"].get("small") or ""

        if not portada:
            portada = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

        return {
            "fuente": "Open Library Books API",
            "isbn": isbn,
            "titulo": info.get("title", "Sin título"),
            "autores": autores_texto,
            "editorial": editorial_texto,
            "fecha_publicacion": info.get("publish_date", "Fecha desconocida"),
            "categorias": categorias_texto,
            "descripcion": info.get("notes", "Sin descripción"),
            "portada": portada,
        }

    except Exception:
        return None


def buscar_en_open_library_search_api(isbn, timeout=25):
    try:
        url = f"https://openlibrary.org/search.json?isbn={isbn}"
        respuesta = requests.get(url, timeout=timeout)

        if respuesta.status_code != 200:
            return None

        datos = respuesta.json()
        docs = datos.get("docs", [])

        if not docs:
            return None

        info = docs[0]

        autores = info.get("author_name", [])
        autores_texto = ", ".join(autores) if autores else "Autor desconocido"

        editoriales = info.get("publisher", [])
        editorial_texto = ", ".join(editoriales[:3]) if editoriales else "Editorial desconocida"

        portada = ""
        if info.get("cover_i"):
            portada = f"https://covers.openlibrary.org/b/id/{info['cover_i']}-L.jpg"
        else:
            portada = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

        return {
            "fuente": "Open Library Search API",
            "isbn": isbn,
            "titulo": info.get("title", "Sin título"),
            "autores": autores_texto,
            "editorial": editorial_texto,
            "fecha_publicacion": str(info.get("first_publish_year", "Fecha desconocida")),
            "categorias": ", ".join(info.get("subject", ["Sin categoría"])[:6]) if info.get("subject") else "Sin categoría",
            "descripcion": "Sin descripción",
            "portada": portada,
        }

    except Exception:
        return None


# --- Diagnóstico de búsqueda por ISBN ---
def extraer_resumen_google_books(datos):
    resumen = {
        "totalItems": datos.get("totalItems", 0),
        "primer_titulo": "",
        "primer_autor": "",
        "primer_editorial": "",
        "primer_isbn": "",
    }

    items = datos.get("items", []) or []
    if not items:
        return resumen

    info = items[0].get("volumeInfo", {})
    resumen["primer_titulo"] = info.get("title", "")
    resumen["primer_autor"] = ", ".join(info.get("authors", []))
    resumen["primer_editorial"] = info.get("publisher", "")
    resumen["primer_isbn"] = extraer_isbnes_google_books(info)
    return resumen


def diagnosticar_busqueda_isbn(isbn):
    isbn_limpio = limpiar_isbn(isbn)
    variantes = obtener_variantes_isbn(isbn_limpio)
    resultados = []

    for isbn_variante in variantes:
        # Google Books API: búsqueda exacta por operador ISBN
        try:
            respuesta = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={
                    "q": f"isbn:{isbn_variante}",
                    "maxResults": 5,
                    "printType": "books",
                    "country": "ES",
                },
                timeout=12
            )
            info = {"status_code": respuesta.status_code}
            if respuesta.status_code == 200:
                info.update(extraer_resumen_google_books(respuesta.json()))
            resultados.append({
                "fuente": "Google Books API - ISBN exacto",
                "isbn_probado": isbn_variante,
                **info,
            })
        except Exception as error:
            resultados.append({
                "fuente": "Google Books API - ISBN exacto",
                "isbn_probado": isbn_variante,
                "error": str(error),
            })

        # Google Books API: búsqueda flexible por número
        try:
            respuesta = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={
                    "q": isbn_variante,
                    "maxResults": 5,
                    "printType": "books",
                    "country": "ES",
                },
                timeout=12
            )
            info = {"status_code": respuesta.status_code}
            if respuesta.status_code == 200:
                info.update(extraer_resumen_google_books(respuesta.json()))
            resultados.append({
                "fuente": "Google Books API - flexible",
                "isbn_probado": isbn_variante,
                **info,
            })
        except Exception as error:
            resultados.append({
                "fuente": "Google Books API - flexible",
                "isbn_probado": isbn_variante,
                "error": str(error),
            })

        # Open Library /isbn/
        try:
            respuesta = requests.get(f"https://openlibrary.org/isbn/{isbn_variante}.json", timeout=12)
            titulo = ""
            if respuesta.status_code == 200:
                titulo = respuesta.json().get("title", "")
            resultados.append({
                "fuente": "Open Library - ISBN exacto",
                "isbn_probado": isbn_variante,
                "status_code": respuesta.status_code,
                "primer_titulo": titulo,
            })
        except Exception as error:
            resultados.append({
                "fuente": "Open Library - ISBN exacto",
                "isbn_probado": isbn_variante,
                "error": str(error),
            })

        # Open Library Books API
        try:
            respuesta = requests.get(
                "https://openlibrary.org/api/books",
                params={
                    "bibkeys": f"ISBN:{isbn_variante}",
                    "format": "json",
                    "jscmd": "data",
                },
                timeout=12
            )
            titulo = ""
            encontrado = False
            if respuesta.status_code == 200:
                datos = respuesta.json()
                clave = f"ISBN:{isbn_variante}"
                encontrado = clave in datos
                if encontrado:
                    titulo = datos[clave].get("title", "")
            resultados.append({
                "fuente": "Open Library - Books API",
                "isbn_probado": isbn_variante,
                "status_code": respuesta.status_code,
                "totalItems": 1 if encontrado else 0,
                "primer_titulo": titulo,
            })
        except Exception as error:
            resultados.append({
                "fuente": "Open Library - Books API",
                "isbn_probado": isbn_variante,
                "error": str(error),
            })

        # Open Library Search API por ISBN
        try:
            respuesta = requests.get(
                "https://openlibrary.org/search.json",
                params={"isbn": isbn_variante, "limit": 5},
                timeout=12
            )
            total = 0
            titulo = ""
            autores = ""
            if respuesta.status_code == 200:
                datos = respuesta.json()
                docs = datos.get("docs", []) or []
                total = len(docs)
                if docs:
                    titulo = docs[0].get("title", "")
                    autores = ", ".join(docs[0].get("author_name", []))
            resultados.append({
                "fuente": "Open Library - Search API ISBN",
                "isbn_probado": isbn_variante,
                "status_code": respuesta.status_code,
                "totalItems": total,
                "primer_titulo": titulo,
                "primer_autor": autores,
            })
        except Exception as error:
            resultados.append({
                "fuente": "Open Library - Search API ISBN",
                "isbn_probado": isbn_variante,
                "error": str(error),
            })

    return {
        "isbn_introducido": isbn,
        "isbn_limpio": isbn_limpio,
        "variantes": variantes,
        "resultados": resultados,
    }

# --- Búsqueda por título/autor en Open Library ---
def buscar_candidatos_open_library_por_texto(titulo, autor="", isbn_original="", timeout=15):
    candidatos = []
    candidatos_vistos = set()

    try:
        titulo = normalizar_texto_busqueda(titulo)
        autor = normalizar_texto_busqueda(autor)

        if not titulo:
            return []

        url = "https://openlibrary.org/search.json"
        consultas = []

        parametros_titulo = {
            "title": titulo,
            "limit": 20,
            "language": "spa",
        }
        if autor:
            parametros_titulo["author"] = autor
        consultas.append(parametros_titulo)

        if autor:
            consultas.append({"q": f'"{titulo}" "{autor}"', "limit": 20, "language": "spa"})
            consultas.append({"q": f"{titulo} {autor}", "limit": 20, "language": "spa"})

        consultas.append({"q": f'"{titulo}"', "limit": 20, "language": "spa"})
        consultas.append({"q": titulo, "limit": 20, "language": "spa"})

        for parametros in consultas:
            respuesta = requests.get(url, params=parametros, timeout=timeout)

            if respuesta.status_code != 200:
                continue

            datos = respuesta.json()
            docs = datos.get("docs", [])

            if not docs:
                continue

            for info in docs:
                titulo_encontrado = info.get("title", "")
                autores = info.get("author_name", [])
                autores_texto = ", ".join(autores) if autores else ""

                if not titulo_encontrado:
                    continue

                puntuacion = calcular_puntuacion_resultado_texto(
                    titulo,
                    autor,
                    titulo_encontrado,
                    autores_texto
                )

                if puntuacion < 65:
                    continue

                clave = f"openlibrary|{normalizar_texto_busqueda(titulo_encontrado).lower()}|{normalizar_texto_busqueda(autores_texto).lower()}"
                if clave in candidatos_vistos:
                    continue
                candidatos_vistos.add(clave)

                libro = crear_libro_desde_open_library_doc(info, isbn_original)
                isbnes = info.get("isbn", []) or []
                candidatos.append({
                    "libro": libro,
                    "titulo": libro["titulo"],
                    "autores": libro["autores"],
                    "editorial": libro["editorial"],
                    "fecha_publicacion": libro["fecha_publicacion"],
                    "fuente": libro["fuente"],
                    "isbn_original": isbn_original,
                    "isbn_encontrado": ", ".join(isbnes[:3]) if isbnes else "",
                    "puntuacion": puntuacion,
                })

        return sorted(candidatos, key=lambda candidato: candidato["puntuacion"], reverse=True)

    except Exception:
        return []


def buscar_en_open_library_por_texto(titulo, autor="", isbn_original="", timeout=15):
    candidatos = buscar_candidatos_open_library_por_texto(titulo, autor, isbn_original, timeout)
    if candidatos:
        return candidatos[0]["libro"]
    return None


def buscar_libro_por_titulo_autor(titulo, autor, isbn_original):
    libro = buscar_en_google_books_por_texto(titulo, autor, isbn_original, timeout=20)
    if libro:
        return libro

    libro = buscar_en_open_library_por_texto(titulo, autor, isbn_original, timeout=20)
    if libro:
        return libro

    return None


def buscar_candidatos_por_titulo_autor(titulo, autor, isbn_original):
    candidatos = []
    candidatos.extend(buscar_candidatos_google_books_por_texto(titulo, autor, isbn_original, timeout=20))
    candidatos.extend(buscar_candidatos_open_library_por_texto(titulo, autor, isbn_original, timeout=20))

    candidatos_unicos = []
    claves_vistas = set()

    for candidato in sorted(candidatos, key=lambda item: item["puntuacion"], reverse=True):
        clave = f"{normalizar_texto_busqueda(candidato['titulo']).lower()}|{normalizar_texto_busqueda(candidato['autores']).lower()}"
        if clave in claves_vistas:
            continue
        claves_vistas.add(clave)
        candidatos_unicos.append(candidato)

    return candidatos_unicos[:5]


def buscar_libro_por_isbn_rapido(isbn):
    isbn = limpiar_isbn(isbn)

    libro = buscar_en_google_books(isbn, timeout=6, busqueda_flexible=False)
    if libro:
        return libro

    libro = buscar_en_open_library(isbn, timeout=6)
    if libro:
        return libro

    return None


def buscar_libro_por_isbn_completo(isbn):
    isbn_limpio = limpiar_isbn(isbn)


    variantes = obtener_variantes_isbn(isbn_limpio)
    tiempo_inicio = time.time()
    limite_total = 180

    for isbn_variante in variantes:
        if time.time() - tiempo_inicio >= limite_total:
            return None

        libro = buscar_en_google_books(isbn_variante, timeout=12, busqueda_flexible=False)
        if libro:
            return libro

        if time.time() - tiempo_inicio >= limite_total:
            return None

        libro = buscar_en_open_library(isbn_variante, timeout=12)
        if libro:
            return libro

        if time.time() - tiempo_inicio >= limite_total:
            return None

        libro = buscar_en_google_books(isbn_variante, timeout=12, busqueda_flexible=True)
        if libro:
            return libro

        if time.time() - tiempo_inicio >= limite_total:
            return None

        libro = buscar_en_open_library_books_api(isbn_variante, timeout=12)
        if libro:
            return libro

        if time.time() - tiempo_inicio >= limite_total:
            return None

        libro = buscar_en_open_library_search_api(isbn_variante, timeout=12)
        if libro:
            return libro

    return None


def buscar_libro_por_isbn_a_fondo(isbn):
    return buscar_libro_por_isbn_completo(isbn)


def buscar_libro_por_isbn(isbn):
    return buscar_libro_por_isbn_rapido(isbn)


def obtener_executor_busqueda():
    if "executor_busqueda" not in st.session_state:
        st.session_state["executor_busqueda"] = ThreadPoolExecutor(max_workers=3)
    return st.session_state["executor_busqueda"]



def calcular_tiempo_maximo_busqueda(isbn, tipo_busqueda):
    return 180


def lanzar_busqueda_en_segundo_plano(item_id, isbn, tipo_busqueda="completa"):
    executor = obtener_executor_busqueda()
    future = executor.submit(buscar_libro_por_isbn_completo, isbn)

    if "tareas_busqueda" not in st.session_state:
        st.session_state["tareas_busqueda"] = {}

    st.session_state["tareas_busqueda"][item_id] = {
        "future": future,
        "tipo_busqueda": "completa",
        "inicio": time.time(),
        "max_segundos": calcular_tiempo_maximo_busqueda(isbn, "completa"),
    }


def actualizar_resultados_busqueda():
    if "tareas_busqueda" not in st.session_state:
        st.session_state["tareas_busqueda"] = {}

    tareas_finalizadas = []

    for item_id, tarea in list(st.session_state["tareas_busqueda"].items()):
        future = tarea["future"]
        tipo_busqueda = tarea.get("tipo_busqueda", "rapida")
        max_segundos = max(int(tarea.get("max_segundos", 1)), 1)
        transcurrido = int(time.time() - tarea.get("inicio", time.time()))

        if not future.done() and transcurrido >= max_segundos:
            for item in st.session_state.get("cola_isbn", []):
                if item["id"] != item_id:
                    continue

                item["estado"] = "no_encontrado"
                item["mensaje"] = "No encontrado tras búsqueda completa"
                item["libro"] = crear_libro_manual_base(item["isbn"])
                break

            tareas_finalizadas.append(item_id)
            future.cancel()
            continue

        if not future.done():
            continue

        tareas_finalizadas.append(item_id)

        try:
            libro_resultado = future.result()
        except Exception:
            libro_resultado = None

        for item in st.session_state.get("cola_isbn", []):
            if item["id"] != item_id:
                continue

            if libro_resultado:
                item["estado"] = "encontrado"
                item["libro"] = libro_resultado
                item["mensaje"] = "Libro encontrado"
                st.session_state["ultimo_libro_encontrado"] = libro_resultado
                st.session_state["mostrar_aviso_libro_encontrado"] = True
            else:
                item["estado"] = "no_encontrado"
                item["mensaje"] = "No encontrado tras búsqueda completa"

                item["libro"] = {
                    "fuente": "Manual",
                    "isbn": item["isbn"],
                    "titulo": "",
                    "autores": "",
                    "editorial": "",
                    "fecha_publicacion": "",
                    "categorias": "",
                    "descripcion": "",
                    "portada": "",
                }

            break

    for item_id in tareas_finalizadas:
        del st.session_state["tareas_busqueda"][item_id]


def texto_estado_cola(estado):
    textos = {
        "pendiente": "⏳ Esperando",
        "buscando": "🔎 Buscando libro",
        "buscando_rapido": "🔎 Buscando libro",
        "buscando_fondo": "🔎 Buscando libro",
        "encontrado": "✅ Encontrado",
        "no_encontrado": "⚠️ No encontrado",
        "no_encontrado_rapido": "⚠️ No encontrado en búsqueda rápida",
        "no_encontrado_fondo": "❌ No encontrado tras búsqueda a fondo",
        "error_rapido": "⏱️ Búsqueda rápida agotada",
        "error_fondo": "⏱️ Búsqueda a fondo agotada",
        "isbn_no_valido": "⚠️ Revisar código",
        "codigo_basura": "⚠️ Código no válido",
        "en_revision": "📚 En revisión",
    }
    return textos.get(estado, estado)


def crear_libro_manual_base(isbn):
    return {
        "fuente": "Manual",
        "isbn": isbn,
        "titulo": "",
        "autores": "",
        "editorial": "",
        "fecha_publicacion": "",
        "categorias": "",
        "descripcion": "",
        "portada": "",
    }


def devolver_revision_anterior_a_bandeja(item_id_actual):
    item_cola_activo_anterior = st.session_state.get("item_cola_activo")

    if item_cola_activo_anterior is None or item_cola_activo_anterior == item_id_actual:
        return

    for item_anterior in st.session_state["cola_isbn"]:
        if item_anterior["id"] == item_cola_activo_anterior and item_anterior["estado"] == "en_revision":
            if item_anterior.get("libro") and item_anterior["libro"].get("fuente") == "Manual":
                item_anterior["estado"] = "no_encontrado_fondo"
            else:
                item_anterior["estado"] = "encontrado"


def abrir_revision_libro(item, item_id, libro):
    devolver_revision_anterior_a_bandeja(item_id)
    item["estado"] = "en_revision"
    item["libro"] = libro
    st.session_state["libro_encontrado"] = libro
    st.session_state["item_cola_activo"] = item_id
    st.session_state["mostrar_aviso_libro_encontrado"] = False
    st.rerun()



def abrir_ficha_manual(item, item_id):
    libro_manual = crear_libro_manual_base(item["isbn"])
    abrir_revision_libro(item, item_id, libro_manual)


def abrir_ficha_manual_directa():
    if "item_cola_activo" in st.session_state:
        del st.session_state["item_cola_activo"]

    st.session_state["libro_encontrado"] = crear_libro_manual_base("")
    st.session_state["mostrar_aviso_libro_encontrado"] = False
    st.rerun()


def mostrar_progreso_busqueda(item_id):
    tarea = st.session_state.get("tareas_busqueda", {}).get(item_id)

    if not tarea:
        return

    max_segundos = max(int(tarea.get("max_segundos", 1)), 1)
    transcurrido = int(time.time() - tarea.get("inicio", time.time()))
    restante = max(max_segundos - transcurrido, 0)

    if transcurrido >= max_segundos:
        progreso = 0.95
        texto_restante = "agotando último intento"
    else:
        progreso = min(transcurrido / max_segundos, 0.95)
        texto_restante = f"restante estimado: {restante}s"

    st.progress(progreso)
    st.caption(
        f"Tiempo buscando: {transcurrido}s · estimación: {max_segundos}s · {texto_restante}"
    )


def inicializar_estado():
    if "cola_isbn" not in st.session_state:
        st.session_state["cola_isbn"] = []

    if "contador_cola" not in st.session_state:
        st.session_state["contador_cola"] = 0

    if "filtro_ubicacion" not in st.session_state:
        st.session_state["filtro_ubicacion"] = "Todas"

    if "filtro_estado" not in st.session_state:
        st.session_state["filtro_estado"] = "Todos"

    if "busqueda_texto" not in st.session_state:
        st.session_state["busqueda_texto"] = ""


def añadir_isbn_a_cola(biblioteca):
    isbn_escaneado = st.session_state.get("isbn_rapido", "")
    isbn_limpio = limpiar_isbn(isbn_escaneado)

    if isbn_escaneado and not isbn_limpio:
        st.session_state["mensaje_guardado"] = "El código introducido no contiene números de ISBN."

    elif isbn_limpio:
        isbn_ya_en_cola = any(item["isbn"] == isbn_limpio for item in st.session_state["cola_isbn"])
        isbn_ya_guardado = isbn_limpio in biblioteca["isbn"].astype(str).values

        if not isbn_ya_en_cola and not isbn_ya_guardado:
            st.session_state["contador_cola"] += 1
            nuevo_id = st.session_state["contador_cola"]

            if es_codigo_basura(isbn_limpio):
                st.session_state["cola_isbn"].append({
                    "id": nuevo_id,
                    "isbn": isbn_limpio,
                    "estado": "codigo_basura",
                    "libro": crear_libro_manual_base(isbn_limpio),
                    "mensaje": "Código no válido o no reconocible"
                })
            else:
                st.session_state["cola_isbn"].append({
                    "id": nuevo_id,
                    "isbn": isbn_limpio,
                    "estado": "buscando",
                    "libro": None,
                    "mensaje": "Buscando libro"
                })

                lanzar_busqueda_en_segundo_plano(nuevo_id, isbn_limpio, tipo_busqueda="completa")
        elif isbn_ya_guardado:
            st.session_state["mensaje_guardado"] = f"El ISBN {isbn_limpio} ya está guardado en la biblioteca."
        elif isbn_ya_en_cola:
            st.session_state["mensaje_guardado"] = f"El ISBN {isbn_limpio} ya está en la bandeja."

    st.session_state["isbn_rapido"] = ""


def mostrar_aviso_libro_encontrado():
    if st.session_state.get("mostrar_aviso_libro_encontrado", False) and "ultimo_libro_encontrado" in st.session_state:
        with st.container(border=True):
            col_img, col_txt, col_cerrar = st.columns([1, 5, 1])

            with col_img:
                if os.path.exists(IMAGEN_LIBRO_ENCONTRADO):
                    st.image(IMAGEN_LIBRO_ENCONTRADO, width=115)

            with col_txt:
                st.success("📚 ¡Libro encontrado!")
                st.write(f"**{st.session_state['ultimo_libro_encontrado']['titulo']}**")

            with col_cerrar:
                if st.button("Cerrar aviso", key="cerrar_aviso_bandeja"):
                    st.session_state["mostrar_aviso_libro_encontrado"] = False
                    st.rerun()


def mostrar_ficha_revision(biblioteca):
    if "libro_encontrado" not in st.session_state:
        return

    libro = st.session_state["libro_encontrado"]

    st.divider()

    if libro["fuente"] == "Manual":
        st.subheader("Ficha manual del libro")
        st.info("Rellena los datos disponibles y guarda el libro manualmente.")
    else:
        st.subheader("Ficha del libro")

    col1, col2 = st.columns([1, 3])

    with col1:
        portada_manual = libro.get("portada", "") or ""

        if libro["fuente"] == "Manual":
            portada_manual = st.text_input(
                "URL de portada",
                value=portada_manual,
                placeholder="https://...",
                key="nuevo_portada"
            )

        if portada_manual:
            st.image(portada_manual, width=180)
        else:
            st.info("Sin portada disponible")

    with col2:
        titulo_editado = st.text_input("Título", value=libro["titulo"], key="nuevo_titulo")
        autores_editado = st.text_input("Autor/es", value=libro["autores"], key="nuevo_autores")
        editorial_editada = st.text_input("Editorial", value=libro["editorial"], key="nuevo_editorial")
        fecha_editada = st.text_input("Fecha de publicación", value=libro["fecha_publicacion"], key="nuevo_fecha")
        categorias_editadas = st.text_input("Categoría", value=libro["categorias"], key="nuevo_categorias")
        descripcion_editada = st.text_area("Descripción", value=libro["descripcion"], height=120, key="nuevo_descripcion")

        st.markdown("### Ubicación e inventario")
        ubicacion_editada = st.text_input("Ubicación", placeholder="Ejemplo: Salón, despacho, habitación...", key="nuevo_ubicacion")
        estanteria_editada = st.text_input("Estantería", placeholder="Ejemplo: Estantería 1", key="nuevo_estanteria")
        balda_editada = st.text_input("Balda", placeholder="Ejemplo: Balda 2", key="nuevo_balda")
        estado_editado = st.selectbox("Estado", ["Sin especificar", "Pendiente", "Leyendo", "Leído", "Prestado"], key="nuevo_estado")
        notas_editadas = st.text_area("Notas", placeholder="Notas internas sobre este libro", height=80, key="nuevo_notas")

        libro_editado = {
            "isbn": libro["isbn"],
            "titulo": titulo_editado,
            "autores": autores_editado,
            "editorial": editorial_editada,
            "fecha_publicacion": fecha_editada,
            "categorias": categorias_editadas,
            "descripcion": descripcion_editada,
            "portada": portada_manual,
            "fuente": libro["fuente"],
            "ubicacion": ubicacion_editada,
            "estanteria": estanteria_editada,
            "balda": balda_editada,
            "estado": estado_editado,
            "notas": notas_editadas,
        }

        col_guardar_nuevo, col_cancelar_nuevo = st.columns(2)

        with col_guardar_nuevo:
            if st.button("💾 Guardar libro"):
                isbn_actual = libro_editado["isbn"]

                if isbn_actual in biblioteca["isbn"].astype(str).values:
                    st.warning("Este libro ya está guardado en la biblioteca.")
                else:
                    libro_guardar = libro_editado.copy()
                    libro_guardar["fecha_alta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    biblioteca = pd.concat([biblioteca, pd.DataFrame([libro_guardar])], ignore_index=True)
                    guardar_biblioteca(biblioteca)

                    item_cola_activo = st.session_state.get("item_cola_activo")
                    if item_cola_activo is not None:
                        st.session_state["cola_isbn"] = [
                            i for i in st.session_state["cola_isbn"]
                            if i["id"] != item_cola_activo
                        ]
                        del st.session_state["item_cola_activo"]

                    st.session_state["mensaje_guardado"] = f"Libro guardado correctamente: {libro_guardar['titulo'] or 'Sin título'}"
                    st.session_state["mostrar_aviso_libro_encontrado"] = False
                    del st.session_state["libro_encontrado"]
                    st.rerun()

        with col_cancelar_nuevo:
            if st.button("❌ Cancelar ficha"):
                st.session_state["mostrar_aviso_libro_encontrado"] = False

                item_cola_activo = st.session_state.get("item_cola_activo")
                if item_cola_activo is not None:
                    for item_cancelado in st.session_state["cola_isbn"]:
                        if item_cancelado["id"] == item_cola_activo and item_cancelado["estado"] == "en_revision":
                            if item_cancelado.get("libro") and item_cancelado["libro"].get("fuente") == "Manual":
                                item_cancelado["estado"] = "no_encontrado"
                            else:
                                item_cancelado["estado"] = "encontrado"

                    del st.session_state["item_cola_activo"]

                del st.session_state["libro_encontrado"]
                st.rerun()


def mostrar_tab_añadir(biblioteca):
    st.header("📥 Añadir libros")

    col_escaneo, col_pendientes = st.columns([1, 2])

    with col_escaneo:
        st.subheader("Escaneo rápido")
        st.write("Escanea un ISBN y pulsa Enter. La app lo añade a la bandeja.")

        st.text_input(
            "ISBN",
            key="isbn_rapido",
            placeholder="Escanea aquí...",
            on_change=añadir_isbn_a_cola,
            args=(biblioteca,)
        )

        if st.button("✍️ Crear ficha manual sin buscar"):
            abrir_ficha_manual_directa()

        if st.session_state["cola_isbn"]:
            st.caption(f"ISBN en bandeja: {len(st.session_state['cola_isbn'])}")
            st.markdown("**Estado de la cola**")

            for item in st.session_state["cola_isbn"]:
                st.write(f"`{item['isbn']}` — {texto_estado_cola(item['estado'])}")
        else:
            st.caption("No hay ISBN pendientes.")

    with col_pendientes:
        st.subheader("Bandeja de libros")

        actualizar_resultados_busqueda()

        if st.button("🔄 Actualizar estado"):
            actualizar_resultados_busqueda()
            st.rerun()

        mostrar_aviso_libro_encontrado()

        if not st.session_state["cola_isbn"]:
            st.info("Escanea libros para que aparezcan aquí.")

        for item in st.session_state["cola_isbn"]:
            item_id = item["id"]

            with st.container(border=True):
                if item["estado"] == "encontrado":
                    libro_item = item["libro"]
                    st.success("📚 Libro encontrado")
                    st.write(f"**{libro_item['titulo']}**")
                    st.caption(f"ISBN: {item['isbn']} · Fuente: {libro_item['fuente']}")

                    col_revisar, col_manual, col_descartar = st.columns(3)

                    with col_revisar:
                        if st.button("Revisar / guardar", key=f"revisar_{item_id}"):
                            abrir_revision_libro(item, item_id, libro_item)

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_encontrado_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "no_encontrado_rapido":
                    st.warning("⚠️ No encontrado en búsqueda rápida")
                    st.caption(f"ISBN: {item['isbn']}")

                    col_fondo, col_manual, col_descartar = st.columns(3)

                    with col_fondo:
                        if st.button("🔎 Buscar a fondo", key=f"fondo_{item_id}"):
                            item["estado"] = "buscando_fondo"
                            item["mensaje"] = "Búsqueda a fondo"
                            lanzar_busqueda_en_segundo_plano(item_id, item["isbn"], tipo_busqueda="fondo")
                            st.rerun()

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_rapido_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_rapido_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "error_rapido":
                    st.warning("⏱️ La búsqueda rápida agotó el tiempo máximo")
                    st.caption(f"ISBN: {item['isbn']} · No podemos confirmar si el libro existe en las bases consultadas.")

                    col_reintentar, col_fondo, col_manual, col_descartar = st.columns(4)

                    with col_reintentar:
                        if st.button("🔁 Reintentar rápida", key=f"reintentar_rapida_{item_id}"):
                            item["estado"] = "buscando_rapido"
                            item["mensaje"] = "Búsqueda rápida"
                            lanzar_busqueda_en_segundo_plano(item_id, item["isbn"], tipo_busqueda="rapida")
                            st.rerun()

                    with col_fondo:
                        if st.button("🔎 Buscar a fondo", key=f"fondo_error_{item_id}"):
                            item["estado"] = "buscando_fondo"
                            item["mensaje"] = "Búsqueda a fondo"
                            lanzar_busqueda_en_segundo_plano(item_id, item["isbn"], tipo_busqueda="fondo")
                            st.rerun()

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_error_rapido_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_error_rapido_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "no_encontrado_fondo":
                    st.error("❌ No encontrado tras búsqueda a fondo")
                    st.caption(f"ISBN: {item['isbn']}")

                    col_manual, col_descartar = st.columns(2)

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_fondo_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_fondo_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "error_fondo":
                    st.warning("⏱️ La búsqueda a fondo agotó el tiempo máximo")
                    st.caption(f"ISBN: {item['isbn']} · Puedes reintentar o crear la ficha manual.")

                    col_reintentar, col_manual, col_descartar = st.columns(3)

                    with col_reintentar:
                        if st.button("🔁 Reintentar fondo", key=f"reintentar_fondo_{item_id}"):
                            item["estado"] = "buscando_fondo"
                            item["mensaje"] = "Búsqueda a fondo"
                            lanzar_busqueda_en_segundo_plano(item_id, item["isbn"], tipo_busqueda="fondo")
                            st.rerun()

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_error_fondo_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_error_fondo_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] in ["buscando", "buscando_rapido", "buscando_fondo"]:
                    st.info(f"🔎 Buscando libro... · ISBN: {item['isbn']}")
                    mostrar_progreso_busqueda(item_id)

                    col_manual, col_descartar = st.columns(2)

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_buscando_rapido_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_buscando_rapido_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                # bloque eliminado: elif item["estado"] == "buscando_fondo":


                elif item["estado"] == "codigo_basura":
                    st.warning("⚠️ Código no válido o no reconocible")
                    st.caption(f"Código escaneado: {item['isbn']} · Parece un código basura, incompleto o no útil como ISBN.")

                    col_manual, col_descartar = st.columns(2)

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_codigo_basura_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_codigo_basura_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "no_encontrado":
                    st.error("❌ Libro no encontrado por ISBN")
                    st.caption(f"ISBN físico: {item['isbn']} · No se ha encontrado ese ISBN en las bases gratuitas consultadas.")

                    st.markdown("**Buscar por título/autor**")
                    titulo_busqueda = st.text_input(
                        "Título",
                        placeholder="Ejemplo: El sueño de la espada",
                        key=f"titulo_busqueda_{item_id}"
                    )
                    autor_busqueda = st.text_input(
                        "Autor/a",
                        placeholder="Ejemplo: Manuel Sánchez",
                        key=f"autor_busqueda_{item_id}"
                    )

                    col_buscar_texto, col_diagnostico, col_manual, col_descartar = st.columns(4)

                    with col_buscar_texto:
                        if st.button("🔍 Buscar por título/autor", key=f"buscar_texto_{item_id}"):
                            candidatos = buscar_candidatos_por_titulo_autor(
                                titulo_busqueda,
                                autor_busqueda,
                                item["isbn"]
                            )

                            st.session_state[f"candidatos_texto_{item_id}"] = candidatos

                            if not candidatos:
                                st.warning("No se ha encontrado ningún resultado suficientemente parecido por título/autor.")

                    with col_diagnostico:
                        if st.button("🧪 Diagnosticar ISBN", key=f"boton_diagnostico_isbn_{item_id}"):
                            st.session_state[f"resultado_diagnostico_isbn_{item_id}"] = diagnosticar_busqueda_isbn(item["isbn"])

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_{item_id}"):
                            abrir_ficha_manual(item, item_id)

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_no_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                    diagnostico_guardado = st.session_state.get(f"resultado_diagnostico_isbn_{item_id}")
                    if diagnostico_guardado:
                        st.markdown("**Diagnóstico de búsqueda por ISBN**")
                        st.caption(
                            f"ISBN introducido: {diagnostico_guardado['isbn_introducido']} · "
                            f"ISBN limpio: {diagnostico_guardado['isbn_limpio']} · "
                            f"Variantes probadas: {', '.join(diagnostico_guardado['variantes'])}"
                        )

                        tabla_diagnostico = pd.DataFrame(diagnostico_guardado["resultados"])
                        columnas_diagnostico = [
                            columna for columna in [
                                "fuente",
                                "isbn_probado",
                                "status_code",
                                "totalItems",
                                "primer_titulo",
                                "primer_autor",
                                "primer_editorial",
                                "primer_isbn",
                                "error",
                            ]
                            if columna in tabla_diagnostico.columns
                        ]
                        st.dataframe(tabla_diagnostico[columnas_diagnostico], width="stretch", hide_index=True)

                    candidatos_guardados = st.session_state.get(f"candidatos_texto_{item_id}", [])
                    if candidatos_guardados:
                        st.markdown("**Resultados parecidos encontrados**")
                        st.caption("Elige el resultado que corresponda al libro físico. Se conservará el ISBN escaneado.")

                        for indice, candidato in enumerate(candidatos_guardados, start=1):
                            with st.container(border=True):
                                st.write(f"**{indice}. {candidato['titulo']}**")
                                st.caption(
                                    f"{candidato['autores']} · {candidato['editorial']} · {candidato['fecha_publicacion']} · "
                                    f"Fuente: {candidato['fuente']} · Coincidencia: {candidato['puntuacion']}%"
                                )
                                if candidato.get("isbn_encontrado"):
                                    st.caption(f"ISBN de la ficha encontrada: {candidato['isbn_encontrado']}")
                                st.caption(f"ISBN físico que se guardará: {item['isbn']}")

                                if st.button("Usar este resultado", key=f"usar_candidato_{item_id}_{indice}"):
                                    abrir_revision_libro(item, item_id, candidato["libro"])

                elif item["estado"] == "en_revision":
                    st.info(f"📚 En revisión · ISBN: {item['isbn']}")

                    if st.button("Volver a abrir revisión", key=f"continuar_revision_{item_id}"):
                        st.session_state["libro_encontrado"] = item["libro"]
                        st.session_state["item_cola_activo"] = item_id
                        st.session_state["mostrar_aviso_libro_encontrado"] = False
                        st.rerun()

                else:
                    st.info(f"⏳ Esperando · ISBN: {item['isbn']}")

    mostrar_ficha_revision(biblioteca)


def mostrar_tab_biblioteca(biblioteca):
    st.header("📚 La biblioteca de Enrique")

    if biblioteca.empty:
        st.info("Todavía no hay libros guardados.")
        return

    st.write(f"Total de libros guardados: **{len(biblioteca)}**")

    st.markdown("### Filtros")

    col_filtro_ubicacion, col_filtro_estado, col_filtro_texto = st.columns(3)

    ubicaciones_disponibles = sorted([u for u in biblioteca["ubicacion"].unique() if u])
    estados_disponibles = sorted([e for e in biblioteca["estado"].unique() if e])

    def limpiar_filtros():
        st.session_state["filtro_ubicacion"] = "Todas"
        st.session_state["filtro_estado"] = "Todos"
        st.session_state["busqueda_texto"] = ""

    with col_filtro_ubicacion:
        filtro_ubicacion = st.selectbox("Filtrar por ubicación", ["Todas"] + ubicaciones_disponibles, key="filtro_ubicacion")

    with col_filtro_estado:
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos"] + estados_disponibles, key="filtro_estado")

    with col_filtro_texto:
        busqueda = st.text_input("Buscar por texto", key="busqueda_texto")

    st.button("🧹 Limpiar filtros", on_click=limpiar_filtros)

    biblioteca_filtrada = biblioteca.copy()

    if filtro_ubicacion != "Todas":
        biblioteca_filtrada = biblioteca_filtrada[biblioteca_filtrada["ubicacion"] == filtro_ubicacion]

    if filtro_estado != "Todos":
        biblioteca_filtrada = biblioteca_filtrada[biblioteca_filtrada["estado"] == filtro_estado]

    if busqueda:
        filtro = biblioteca_filtrada.apply(lambda fila: busqueda.lower() in " ".join(fila.astype(str)).lower(), axis=1)
        biblioteca_filtrada = biblioteca_filtrada[filtro].copy()

    st.write(f"Libros mostrados: **{len(biblioteca_filtrada)}**")

    columnas_visibles = [
        "titulo", "autores", "estado", "ubicacion", "estanteria", "balda",
        "isbn", "editorial", "fecha_publicacion", "categorias", "fecha_alta"
    ]

    tabla_mostrar = biblioteca_filtrada[columnas_visibles].rename(columns={
        "titulo": "Título",
        "autores": "Autor/es",
        "estado": "Estado",
        "ubicacion": "Ubicación",
        "estanteria": "Estantería",
        "balda": "Balda",
        "isbn": "ISBN",
        "editorial": "Editorial",
        "fecha_publicacion": "Publicación",
        "categorias": "Categoría",
        "fecha_alta": "Fecha de alta"
    })

    evento_tabla = st.dataframe(tabla_mostrar, width="stretch", hide_index=True, selection_mode="single-row", on_select="rerun")
    filas_seleccionadas = evento_tabla.selection.rows

    if filas_seleccionadas:
        posicion_filtrada = filas_seleccionadas[0]
        indice_real = biblioteca_filtrada.index[posicion_filtrada]
        libro_seleccionado = biblioteca.loc[indice_real]

        st.subheader("✏️ Editar libro seleccionado")

        col1, col2 = st.columns([1, 3])

        with col1:
            portada_editada = st.text_input("URL de portada", value=libro_seleccionado["portada"], placeholder="https://...", key="edit_portada")

            if portada_editada:
                st.image(portada_editada, width=180)
            else:
                st.info("Sin portada disponible")

        with col2:
            isbn_editado = st.text_input("ISBN", value=libro_seleccionado["isbn"], key="edit_isbn")
            titulo_editado = st.text_input("Título", value=libro_seleccionado["titulo"], key="edit_titulo")
            autores_editado = st.text_input("Autor/es", value=libro_seleccionado["autores"], key="edit_autores")
            editorial_editada = st.text_input("Editorial", value=libro_seleccionado["editorial"], key="edit_editorial")
            fecha_editada = st.text_input("Fecha de publicación", value=libro_seleccionado["fecha_publicacion"], key="edit_fecha")
            categorias_editadas = st.text_input("Categoría", value=libro_seleccionado["categorias"], key="edit_categorias")
            descripcion_editada = st.text_area("Descripción", value=libro_seleccionado["descripcion"], height=120, key="edit_descripcion")

            st.markdown("### Ubicación e inventario")
            ubicacion_editada = st.text_input("Ubicación", value=libro_seleccionado["ubicacion"], key="edit_ubicacion")
            estanteria_editada = st.text_input("Estantería", value=libro_seleccionado["estanteria"], key="edit_estanteria")
            balda_editada = st.text_input("Balda", value=libro_seleccionado["balda"], key="edit_balda")

            estados = ["Sin especificar", "Pendiente", "Leyendo", "Leído", "Prestado"]
            estado_actual = libro_seleccionado["estado"] if libro_seleccionado["estado"] in estados else "Sin especificar"

            estado_editado = st.selectbox("Estado", estados, index=estados.index(estado_actual), key="edit_estado")
            notas_editadas = st.text_area("Notas", value=libro_seleccionado["notas"], height=80, key="edit_notas")

            col_guardar, col_borrar = st.columns(2)

            with col_guardar:
                if st.button("💾 Guardar cambios"):
                    biblioteca.loc[indice_real, "isbn"] = isbn_editado
                    biblioteca.loc[indice_real, "titulo"] = titulo_editado
                    biblioteca.loc[indice_real, "autores"] = autores_editado
                    biblioteca.loc[indice_real, "editorial"] = editorial_editada
                    biblioteca.loc[indice_real, "fecha_publicacion"] = fecha_editada
                    biblioteca.loc[indice_real, "categorias"] = categorias_editadas
                    biblioteca.loc[indice_real, "descripcion"] = descripcion_editada
                    biblioteca.loc[indice_real, "portada"] = portada_editada
                    biblioteca.loc[indice_real, "ubicacion"] = ubicacion_editada
                    biblioteca.loc[indice_real, "estanteria"] = estanteria_editada
                    biblioteca.loc[indice_real, "balda"] = balda_editada
                    biblioteca.loc[indice_real, "estado"] = estado_editado
                    biblioteca.loc[indice_real, "notas"] = notas_editadas

                    guardar_biblioteca(biblioteca)
                    st.success("Cambios guardados correctamente.")
                    st.rerun()

            with col_borrar:
                if st.button("🗑️ Borrar libro"):
                    st.session_state["confirmar_borrado"] = True

                if st.session_state.get("confirmar_borrado", False):
                    st.warning("¿Seguro que quieres borrar este libro? Esta acción no se puede deshacer.")

                    col_si, col_no = st.columns(2)

                    with col_si:
                        if st.button("Sí, borrar definitivamente"):
                            biblioteca = biblioteca.drop(index=indice_real).reset_index(drop=True)
                            guardar_biblioteca(biblioteca)
                            st.session_state["confirmar_borrado"] = False
                            st.success("Libro borrado correctamente.")
                            st.rerun()

                    with col_no:
                        if st.button("Cancelar"):
                            st.session_state["confirmar_borrado"] = False
                            st.rerun()


def mostrar_tab_estadisticas(biblioteca):
    st.header("📊 Estadísticas")

    if biblioteca.empty:
        st.info("Todavía no hay libros guardados.")
        return

    total_leidos = (biblioteca["estado"] == "Leído").sum()
    total_leyendo = (biblioteca["estado"] == "Leyendo").sum()
    total_pendientes = (biblioteca["estado"] == "Pendiente").sum()
    total_prestados = (biblioteca["estado"] == "Prestado").sum()

    col_total, col_leidos, col_leyendo, col_pendientes, col_prestados = st.columns(5)

    with col_total:
        st.metric("Total", len(biblioteca))

    with col_leidos:
        st.metric("Leídos", total_leidos)

    with col_leyendo:
        st.metric("Leyendo", total_leyendo)

    with col_pendientes:
        st.metric("Pendientes", total_pendientes)

    with col_prestados:
        st.metric("Prestados", total_prestados)

    st.markdown("### Estado de la biblioteca")

    datos_estado = biblioteca["estado"].replace("", "Sin especificar").value_counts().reset_index()
    datos_estado.columns = ["estado", "cantidad"]

    orden_estados = ["Leído", "Leyendo", "Pendiente", "Prestado", "Sin especificar"]
    colores_estado = ["#39FF14", "#00E5FF", "#FFEA00", "#FF2D95", "#8A8DFF"]

    datos_estado["estado"] = pd.Categorical(datos_estado["estado"], categories=orden_estados, ordered=True)
    datos_estado = datos_estado.sort_values("estado")

    st.caption("Distribución visual de los libros según su situación actual")
    st.write("")

    grafico_estado = (
        alt.Chart(datos_estado)
        .mark_arc(innerRadius=52, outerRadius=82, cornerRadius=7, padAngle=0.025)
        .encode(
            theta=alt.Theta(field="cantidad", type="quantitative"),
            color=alt.Color(
                field="estado",
                type="nominal",
                title=None,
                scale=alt.Scale(domain=orden_estados, range=colores_estado),
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    columns=3,
                    labelFontSize=13,
                    labelColor="#2f2a24",
                    symbolSize=140,
                    symbolStrokeWidth=0
                )
            ),
            tooltip=[
                alt.Tooltip("estado:N", title="Estado"),
                alt.Tooltip("cantidad:Q", title="Libros")
            ]
        )
        .properties(width=380, height=460)
        .configure_view(strokeWidth=0)
        .configure_legend(labelColor="#2f2a24", titleColor="#2f2a24")
        .configure(background="transparent")
    )

    col_espacio_izq, col_grafico, col_espacio_der = st.columns([1, 2, 1])

    with col_grafico:
        st.altair_chart(grafico_estado, width="content", theme=None)


def mostrar_tab_copia(biblioteca):
    st.header("💾 Copia de seguridad")

    if biblioteca.empty:
        st.info("Todavía no hay libros guardados para exportar.")
        return

    if google_sheets_configurado():
        st.write("La biblioteca principal se guarda en Google Sheets. Puedes descargar una copia CSV adicional como respaldo.")
    else:
        st.write("Descarga una copia de la biblioteca para guardarla fuera de la app.")

    st.download_button(
        label="⬇️ Descargar biblioteca en CSV",
        data=biblioteca.to_csv(index=False).encode("utf-8"),
        file_name="biblioteca_enrique.csv",
        mime="text/csv"
    )

    st.caption("El archivo CSV puede abrirse con Excel, Numbers o Google Sheets. La base principal de la app será Google Sheets cuando los Secrets estén configurados.")


# =========================
# APP
# =========================

inicializar_estado()

biblioteca = cargar_biblioteca()


pagina_actual = st.radio(
    "Navegación",
    [
        "📥 Añadir libros",
        "📚 Biblioteca",
        "📊 Estadísticas",
        "💾 Copia de seguridad",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="pagina_actual"
)

if "mensaje_guardado" in st.session_state:
    st.success(st.session_state["mensaje_guardado"])
    del st.session_state["mensaje_guardado"]



if pagina_actual == "📥 Añadir libros":
    mostrar_tab_añadir(biblioteca)

elif pagina_actual == "📚 Biblioteca":
    biblioteca = cargar_biblioteca()
    mostrar_tab_biblioteca(biblioteca)

elif pagina_actual == "📊 Estadísticas":
    biblioteca = cargar_biblioteca()
    mostrar_tab_estadisticas(biblioteca)

elif pagina_actual == "💾 Copia de seguridad":
    biblioteca = cargar_biblioteca()
    mostrar_tab_copia(biblioteca)