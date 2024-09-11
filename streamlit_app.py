import streamlit as st
import requests
from lxml import html
import urllib.parse
import re


# Eliminar los colores de consola porque no se utilizan en Streamlit
REAL_DEBRID_FOLDER_URL = 'https://my.real-debrid.com/PS6APRK7YUCDS/torrents/'

# Función para decodificar caracteres especiales en nombres
def decode_special_chars(text):
    try:
        decoded_text = urllib.parse.unquote(text)
        return decoded_text.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return decoded_text

# Función para codificar correctamente las URLs
def encode_url(url):
    return urllib.parse.quote(url, safe=':/')

# Función para buscar películas o series en Cinecalidad
def search_content(query, content_type='movies'):
    if content_type == 'movies':
        search_url = f"https://www.cinecalidad.ec/?s={query.replace(' ', '+')}"
    else:  # Series
        search_url = f"https://www.cinecalidad.ec/?s={query.replace(' ', '+')}&post_type=series"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(search_url, headers=headers)
    webpage = html.fromstring(response.content)

    # Extraer títulos y enlaces
    content_links = webpage.xpath('//article//a[@href]/@href')
    content_titles = webpage.xpath('//article//h3[@class="hover_caption_caption"]//div[@class="in_title"]/text()')

    content = [{"title": decode_special_chars(title.strip()), "link": link.strip()} for title, link in zip(content_titles, content_links)]

    return content

# Función para obtener las calidades y servidores
def get_qualities_and_servers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    webpage = html.fromstring(response.content)

    qualities = []
    servers = []

    # Extraer los elementos del panel de descarga
    links = webpage.xpath('//ul[@id="sbss"]//a')

    for link in links:
        server = link.xpath('.//li/text()')[0].strip()  # Nombre del servidor
        quality_span = link.xpath('.//li/span/text()')   # Calidad (puede estar vacía)
        quality = quality_span[0].strip() if quality_span else "N/A"

        download_link = link.xpath('./@href')[0]  # El enlace de descarga

        qualities.append(quality)
        servers.append({
            "server": server,
            "quality": quality,
            "link": download_link
        })

    return qualities, servers

# Función para obtener temporadas y episodios de una serie
def get_seasons_and_episodes(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    webpage = html.fromstring(response.content)

    # Extraer temporadas y episodios
    seasons = webpage.xpath('//div[@id="seasons"]//span[@class="title dfr"]/text()')
    episodes = []

    for season in seasons:
        season_tab = webpage.xpath(f'//span[text()="{season}"]/parent::div/@data-tab')[0]
        episode_titles = webpage.xpath(f'//div[@id="jstab" and @data-tab="{season_tab}"]//ul[@class="episodios"]//a/text()')
        episode_links = webpage.xpath(f'//div[@id="jstab" and @data-tab="{season_tab}"]//ul[@class="episodios"]//a/@href')

        episodes.append({
            "season": season,
            "episodes": [{"title": title.strip(), "link": link.strip()} for title, link in zip(episode_titles, episode_links)]
        })

    return episodes

# Función para mostrar el menú y permitir la selección de calidad y servidor
def show_menu(servers):
    st.write("Opciones de calidad y servidores disponibles:")
    for idx, server in enumerate(servers, 1):
        st.write(f"{idx}. {server['server']} - {server['quality']}")

    choice = st.number_input("Elige el número de la calidad y servidor deseado:", min_value=1, max_value=len(servers), step=1) - 1

    if 0 <= choice < len(servers):
        selected = servers[choice]
        st.write(f"Has seleccionado {selected['server']} - {selected['quality']}.")
        st.write(f"Accediendo al enlace: {selected['link']}")
        return selected['link']
    else:
        st.write("Opción inválida.")
        return None

# Función para obtener el magnet link
def get_magnet_link(download_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(download_url, headers=headers)
    webpage = html.fromstring(response.content)

    magnet_link = webpage.xpath('//input[@class="input"]/@value')

    if magnet_link:
        return magnet_link[0]
    else:
        return None

# Función para obtener archivos de Real Debrid
def get_real_debrid_files(url=REAL_DEBRID_FOLDER_URL):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    webpage = html.fromstring(response.content)

    # Extraer archivos y enlaces
    file_names = webpage.xpath('//td/a/text()')
    file_links = webpage.xpath('//td/a/@href')

    # Decodificar nombres y enlaces correctamente
    files = [{"name": decode_special_chars(name.strip()), 
              "link": decode_special_chars(urllib.parse.urljoin(url, link.strip()))} 
             for name, link in zip(file_names, file_links)]

    return files

# Función para clasificar archivos en películas y series
def classify_movies_and_series(files):
    movies = []
    series = {}

    # Patrón para detectar series en formato NAME.SXXEXX.YEAR
    series_pattern = re.compile(r'(?P<name>.+)\.S(?P<season>\d{2})E(?P<episode>\d{2})\.\d{4}')

    for file in files:
        file_name = file['name'].rstrip('/')

        # Buscar si es una serie
        match = series_pattern.match(file_name)
        if match:
            series_name = match.group('name')
            season = int(match.group('season'))
            episode = int(match.group('episode'))

            # Detectar calidad en el nombre del archivo
            if "4k" in file_name.lower() or "2160p" in file_name.lower():
                quality = "4k"
            elif "1080p" in file_name.lower():
                quality = "1080p"
            else:
                quality = "Otra calidad"

            # Agregar series al diccionario agrupado por nombre de la serie
            if series_name not in series:
                series[series_name] = []
            series[series_name].append({
                "name": file_name,
                "season": season,
                "episode": episode,
                "link": file['link'],
                "quality": quality  # Agregar calidad al diccionario
            })
        else:
            # Si no es una serie, es una película
            movies.append(file)

    # Ordenar episodios dentro de cada serie por temporada y episodio
    for series_name in series:
        series[series_name].sort(key=lambda x: (x['season'], x['episode']))

    return movies, series
# Función para clasificar archivos por calidad
def classify_files_by_quality(files):
    quality_groups = {"4k": [], "1080p": [], "Otra calidad": []}

    for file in files:
        file_name = file['name'].rstrip('/')
        
        if "4k" in file_name.lower() or "2160p" in file_name.lower():
            quality_groups["4k"].append(file)
        elif "1080p" in file_name.lower():
            quality_groups["1080p"].append(file)
        else:
            quality_groups["Otra calidad"].append(file)

    return quality_groups


# Función para extraer el título y año de las películas, ignorando términos innecesarios
def extract_movie_title_and_year(filename):
    # Remover la extensión y términos como WEB-DL, 1080p, Dual-Lat, etc.
    clean_filename = re.sub(r'\.(WEB-DL|1080p|2160p|720p|Dual|Lat|Cast|ESP).*', '', filename)
    
    # Dividir en partes por año (asume que el año está en formato de cuatro dígitos)
    match = re.match(r'(.+)\.(\d{4})', clean_filename)
    if match:
        title = match.group(1)  # Obtener la parte del título antes del año
        title = title.replace('.', ' ')  # Reemplazar puntos por espacios
        year = match.group(2)  # Obtener el año
        return title.strip(), year
    return filename.strip(), None

# Función para extraer el título y año de las series
def extract_series_title_and_year(filename):
    # El patrón busca un título que esté seguido por SXXEXX y un año
    clean_filename = re.sub(r'\.(WEB-DL|1080p|2160p|720p|Dual|Lat|Cast|ESP).*', '', filename)
    
    match = re.match(r'(.+)\.S\d{2}E\d{2}\.(\d{4})', clean_filename)
    if match:
        title = match.group(1)  # Obtener el título antes del número de temporada y episodio
        title = title.replace('.', ' ')  # Reemplazar puntos por espacios
        year = match.group(2)  # Obtener el año
        return title.strip(), year
    return filename.strip(), None

# Función para obtener información de TMDB
def get_tmdb_info(title, content_type='movie'):
    api_key = '242e044e9ed025098133698da4df3b87'
    search_url = f"https://api.themoviedb.org/3/search/{content_type}?api_key={api_key}&query={urllib.parse.quote(title)}&language=es-ES"
    
   # st.write(f"Buscando información de TMDB para: {title}")  # Mostrar el título buscado
   # st.write(f"URL consultada: {search_url}")  # Mostrar la URL consultada

    response = requests.get(search_url)
    if response.status_code == 200:
        data = response.json()
       # st.write(f"Respuesta de TMDB: {data}")  # Mostrar la respuesta completa para depuración
        if data['results']:
            result = data['results'][0]  # Tomar el primer resultado
            info = {
                'title': result.get('title', result.get('name', '')),
                'overview': result.get('overview', 'No hay descripción disponible.'),
                'poster_path': result.get('poster_path', '')
            }
            return info
        else:
            st.write("No se encontraron resultados en TMDB.")
    else:
        st.write(f"Error al consultar TMDB: {response.status_code}")
    return None

# Función para mostrar archivos de Real Debrid y separar por calidad
import os

# Función para verificar si el archivo ya tiene extensión y agregar ".mkv" si no tiene
def ensure_mkv_extension(file_name):
    # Verificar si el archivo ya tiene una extensión
    if not os.path.splitext(file_name)[1]:  # Si no tiene extensión
        return f"{file_name}.mkv"
    return file_name

# Función para mostrar archivos de Real Debrid y separar por calidad
def show_real_debrid_files():
    st.write("Archivos disponibles:")
    files = get_real_debrid_files()

    if not files:
        st.write("No se encontraron archivos en Real Debrid.")
        return

    # Clasificar archivos en películas y series
    movies, series = classify_movies_and_series(files)

    # Selección de películas o series
    tipo_archivo = st.radio("¿Qué deseas ver?", ("Películas", "Series"))

    if tipo_archivo == "Películas":
        # Clasificar las películas por calidad
        quality_groups = classify_files_by_quality(movies)
        
        # Selección de calidad
        calidad_seleccionada = st.selectbox("Selecciona una calidad:", ["4k", "1080p", "Otra calidad"])

        # Mostrar solo los archivos de la calidad seleccionada
        filtered_files = quality_groups[calidad_seleccionada]
        
        if filtered_files:
            # Mostrar archivos en un menú desplegable
            file_options = [f"{file['name']}" for file in filtered_files]
            selected_file = st.selectbox("Selecciona una película:", file_options)

            # Obtener la información del archivo seleccionado
            selected_file_info = next(file for file in filtered_files if file['name'] == selected_file)
            
            # Extraer el nombre del archivo y obtener el título y año
            file_name = selected_file_info['name'].rstrip('/')  # Asegurarse de que no termine en "/"
            movie_title, movie_year = extract_movie_title_and_year(file_name)  # Extraer título y año correctamente
            
            # Mostrar la información de la película desde TMDB
            movie_info = get_tmdb_info(movie_title, 'movie')  # Usar el título de la película para buscar en TMDB
            if movie_info:
                st.write(f"**Título:** {movie_info['title']} ({movie_year})")
                st.write(f"**Sinopsis:** {movie_info['overview']}")
                if movie_info['poster_path']:
                    poster_url = f"https://image.tmdb.org/t/p/w500{movie_info['poster_path']}"
                    st.image(poster_url, width=200)

            # Verificar si el archivo tiene una extensión y añadir ".mkv" si es necesario
            file_name_with_extension = ensure_mkv_extension(file_name)
            
            # Concatenar el nombre del archivo con el enlace
            download_link = f"{selected_file_info['link']}{file_name_with_extension}"
            
            # Mostrar el enlace de descarga modificado
            st.text_input("Enlace de descarga para copiar:", value=download_link, key="download_link")
        else:
            st.write(f"No se encontraron archivos en la calidad {calidad_seleccionada}.")
    
    else:
        # Agrupar las series por nombre
        series_names = list(series.keys())
        series_seleccionada = st.selectbox("Selecciona una serie:", series_names)

        if series_seleccionada:
            # Obtener los episodios de la serie seleccionada
            episodes = series[series_seleccionada]
            episode_options = [f"Temporada {ep['season']} Episodio {ep['episode']}" for ep in episodes]
            selected_episode = st.selectbox("Selecciona un episodio:", episode_options)

            # Obtener la información del episodio seleccionado
            selected_episode_info = next(
                ep for ep in episodes if f"Temporada {ep['season']} Episodio {ep['episode']}" == selected_episode
            )
            
            # Extraer el nombre del archivo y obtener el título y año
            file_name = selected_episode_info['name']
            series_title, series_year = extract_series_title_and_year(series_seleccionada)
            
            # Mostrar la información de la serie desde TMDB
            series_info = get_tmdb_info(series_title, 'tv')  # Usar el título de la serie para buscar en TMDB
            if series_info:
                st.write(f"**Título:** {series_info['title']} ({series_year})")
                st.write(f"**Sinopsis:** {series_info['overview']}")
                if series_info['poster_path']:
                    poster_url = f"https://image.tmdb.org/t/p/w500{series_info['poster_path']}"
                    st.image(poster_url, width=200)
            
            # Verificar si el archivo tiene una extensión y añadir ".mkv" si es necesario
            file_name_with_extension = ensure_mkv_extension(file_name)
            
            # Mostrar la calidad del episodio seleccionado
            st.write(f"Calidad del episodio: {selected_episode_info['quality']}")
            download_link = f"{selected_episode_info['link']}{file_name_with_extension}"
            st.text_input("Enlace de descarga para copiar:", value=download_link, key="download_link")





# Función principal
def main():
    st.title("Xstreaming")

    content_type = st.radio("Elige una opción:", ('Películas', 'Series', 'Lista de peliculas o series'))

    if content_type == 'Lista de peliculas o series':
        show_real_debrid_files()
        return

    query = st.text_input(f"Ingrese el nombre para buscar {content_type.lower()}:")

    if query:
        content = search_content(query, 'movies' if content_type == 'Películas' else 'series')

        if not content:
            st.write(f"No se encontraron resultados para '{query}'.")
            return

        st.write("Resultados encontrados:")
        for idx, item in enumerate(content, 1):
            st.write(f"{idx}. {item['title']} - {item['link']}")

        choice = st.number_input("Elige el número del contenido que deseas:", min_value=1, max_value=len(content), step=1) - 1

        if 0 <= choice < len(content):
            selected_content = content[choice]
            st.write(f"Has seleccionado: {selected_content['title']}.")

            # Obtener calidades y servidores
            qualities, servers = get_qualities_and_servers(selected_content['link'])
            download_link = show_menu(servers)

            if download_link:
                magnet_link = get_magnet_link(download_link)
                if magnet_link:
                    st.write(f"Magnet link encontrado: {magnet_link}")
                else:
                    st.write("No se encontró el magnet link.")
        else:
            st.write("Opción inválida.")

if __name__ == "__main__":
    main()
