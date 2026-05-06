import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

ARCHIVO_BIBLIOTECA = "biblioteca.csv"
IMAGEN_LIBRO_ENCONTRADO = "libro_encontrado.jpeg"

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


st.title("📚 Biblioteca Enrique")
st.write("App para registrar libros mediante código de barras o ISBN.")

st.markdown(
    """
    <style>
    div[role="radiogroup"] {
        display: flex;
        gap: 0.35rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.35);
        padding-bottom: 0.15rem;
        margin-bottom: 1rem;
    }

    div[role="radiogroup"] label {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-bottom: none;
        border-radius: 0.65rem 0.65rem 0 0;
        padding: 0.45rem 0.95rem;
        background: rgba(128, 128, 128, 0.08);
        min-height: 2.4rem;
    }

    div[role="radiogroup"] label:has(input:checked) {
        background: rgba(0, 229, 255, 0.16);
        border-color: rgba(0, 229, 255, 0.65);
        box-shadow: 0 -2px 12px rgba(0, 229, 255, 0.18) inset;
        font-weight: 700;
    }

    div[role="radiogroup"] input {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def limpiar_isbn(isbn):
    isbn_limpio = isbn.strip().upper()
    isbn_limpio = re.sub(r"[^0-9X]", "", isbn_limpio)
    return isbn_limpio


def cargar_biblioteca():
    if os.path.exists(ARCHIVO_BIBLIOTECA):
        df = pd.read_csv(ARCHIVO_BIBLIOTECA, dtype=str).fillna("")

        for columna in COLUMNAS_BIBLIOTECA:
            if columna not in df.columns:
                df[columna] = ""

        return df[COLUMNAS_BIBLIOTECA]

    return pd.DataFrame(columns=COLUMNAS_BIBLIOTECA)


def guardar_biblioteca(df):
    df.to_csv(ARCHIVO_BIBLIOTECA, index=False)


def obtener_nombre_autor_open_library(author_key):
    try:
        url = f"https://openlibrary.org{author_key}.json"
        respuesta = requests.get(url, timeout=10)

        if respuesta.status_code != 200:
            return "Autor desconocido"

        datos = respuesta.json()
        return datos.get("name", "Autor desconocido")

    except Exception:
        return "Autor desconocido"


def buscar_en_google_books(isbn):
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        respuesta = requests.get(url, timeout=10)

        if respuesta.status_code != 200:
            return None

        datos = respuesta.json()

        if datos.get("totalItems", 0) == 0:
            return None

        info = datos["items"][0]["volumeInfo"]

        return {
            "fuente": "Google Books",
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


def buscar_en_open_library(isbn):
    try:
        url = f"https://openlibrary.org/isbn/{isbn}.json"
        respuesta = requests.get(url, timeout=10)

        if respuesta.status_code != 200:
            return None

        info = respuesta.json()

        autores = []
        for autor in info.get("authors", []):
            author_key = autor.get("key")
            if author_key:
                autores.append(obtener_nombre_autor_open_library(author_key))

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


def buscar_libro_por_isbn(isbn):
    isbn = limpiar_isbn(isbn)

    libro = buscar_en_google_books(isbn)
    if libro:
        return libro

    libro = buscar_en_open_library(isbn)
    if libro:
        return libro

    return None


def obtener_executor_busqueda():
    if "executor_busqueda" not in st.session_state:
        st.session_state["executor_busqueda"] = ThreadPoolExecutor(max_workers=3)
    return st.session_state["executor_busqueda"]


def lanzar_busqueda_en_segundo_plano(item_id, isbn):
    executor = obtener_executor_busqueda()
    future = executor.submit(buscar_libro_por_isbn, isbn)

    if "tareas_busqueda" not in st.session_state:
        st.session_state["tareas_busqueda"] = {}

    st.session_state["tareas_busqueda"][item_id] = future


def actualizar_resultados_busqueda():
    if "tareas_busqueda" not in st.session_state:
        st.session_state["tareas_busqueda"] = {}

    tareas_finalizadas = []

    for item_id, future in list(st.session_state["tareas_busqueda"].items()):
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
                item["mensaje"] = "No encontrado"

            break

    for item_id in tareas_finalizadas:
        del st.session_state["tareas_busqueda"][item_id]


def texto_estado_cola(estado):
    textos = {
        "pendiente": "⏳ Esperando",
        "buscando": "🔎 Buscando",
        "encontrado": "✅ Encontrado",
        "no_encontrado": "⚠️ No encontrado",
        "en_revision": "📚 En revisión",
    }
    return textos.get(estado, estado)


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

    if isbn_limpio:
        isbn_ya_en_cola = any(item["isbn"] == isbn_limpio for item in st.session_state["cola_isbn"])
        isbn_ya_guardado = isbn_limpio in biblioteca["isbn"].astype(str).values

        if not isbn_ya_en_cola and not isbn_ya_guardado:
            st.session_state["contador_cola"] += 1
            nuevo_id = st.session_state["contador_cola"]

            st.session_state["cola_isbn"].append({
                "id": nuevo_id,
                "isbn": isbn_limpio,
                "estado": "buscando",
                "libro": None,
                "mensaje": "Buscando"
            })

            lanzar_busqueda_en_segundo_plano(nuevo_id, isbn_limpio)
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

                    col_revisar, col_descartar = st.columns(2)

                    with col_revisar:
                        if st.button("Revisar / guardar", key=f"revisar_{item_id}"):
                            item_cola_activo_anterior = st.session_state.get("item_cola_activo")
                            if item_cola_activo_anterior is not None and item_cola_activo_anterior != item_id:
                                for item_anterior in st.session_state["cola_isbn"]:
                                    if item_anterior["id"] == item_cola_activo_anterior and item_anterior["estado"] == "en_revision":
                                        item_anterior["estado"] = "encontrado"

                            item["estado"] = "en_revision"
                            st.session_state["libro_encontrado"] = libro_item
                            st.session_state["item_cola_activo"] = item_id
                            st.session_state["mostrar_aviso_libro_encontrado"] = False
                            st.rerun()

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "no_encontrado":
                    st.warning("⚠️ Libro no encontrado")
                    st.caption(f"ISBN: {item['isbn']}")

                    col_manual, col_descartar = st.columns(2)

                    with col_manual:
                        if st.button("Crear ficha manual", key=f"manual_{item_id}"):
                            item_cola_activo_anterior = st.session_state.get("item_cola_activo")
                            if item_cola_activo_anterior is not None and item_cola_activo_anterior != item_id:
                                for item_anterior in st.session_state["cola_isbn"]:
                                    if item_anterior["id"] == item_cola_activo_anterior and item_anterior["estado"] == "en_revision":
                                        item_anterior["estado"] = "encontrado"

                            item["estado"] = "en_revision"
                            st.session_state["libro_encontrado"] = item["libro"]
                            st.session_state["item_cola_activo"] = item_id
                            st.session_state["mostrar_aviso_libro_encontrado"] = False
                            st.rerun()

                    with col_descartar:
                        if st.button("Descartar", key=f"descartar_no_{item_id}"):
                            st.session_state["cola_isbn"] = [i for i in st.session_state["cola_isbn"] if i["id"] != item_id]
                            st.rerun()

                elif item["estado"] == "buscando":
                    st.info(f"🔎 Buscando · ISBN: {item['isbn']}")

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
    st.header("📚 Biblioteca")

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
        .configure(background="transparent")
    )

    col_espacio_izq, col_grafico, col_espacio_der = st.columns([1, 2, 1])

    with col_grafico:
        st.altair_chart(grafico_estado, use_container_width=False)


def mostrar_tab_copia(biblioteca):
    st.header("💾 Copia de seguridad")

    if biblioteca.empty:
        st.info("Todavía no hay libros guardados para exportar.")
        return

    st.write("Descarga una copia de la biblioteca para guardarla fuera de la app.")

    st.download_button(
        label="⬇️ Descargar biblioteca en CSV",
        data=biblioteca.to_csv(index=False).encode("utf-8"),
        file_name="biblioteca_enrique.csv",
        mime="text/csv"
    )

    st.caption("El archivo CSV puede abrirse con Excel, Numbers o Google Sheets.")


# =========================
# APP
# =========================

inicializar_estado()

biblioteca = cargar_biblioteca()

if "mensaje_guardado" in st.session_state:
    st.success(st.session_state["mensaje_guardado"])
    del st.session_state["mensaje_guardado"]

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