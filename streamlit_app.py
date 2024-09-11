import streamlit as st
import requests
from lxml import html
import urllib.parse

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

# Función para mostrar archivos de Real Debrid y entrar en carpetas si se selecciona una
def show_real_debrid_files():
    st.write("Archivos disponibles en Real Debrid:")
    files = get_real_debrid_files()

    if not files:
        st.write("No se encontraron archivos en Real Debrid.")
        return

    # Mostrar archivos en un menú desplegable
    file_options = [f"{file['name']}" for file in files]
    selected_file = st.selectbox("Selecciona un archivo:", file_options)

    # Obtener la información del archivo seleccionado
    selected_file_info = next(file for file in files if file['name'] == selected_file)
    
    # Extraer el nombre del archivo después del último "/"
    file_name = selected_file_info['name'].rstrip('/')  # Asegurarse de que no termine en "/"
    
    # Concatenar el nombre del archivo con la extensión ".mkv"
    download_link = f"{selected_file_info['link']}{file_name}.mkv"
    # Mostrar un campo de texto con el enlace para que sea fácilmente copiable
    st.text_input("Enlace de descarga para copiar:", value=download_link, key="download_link")

    # Añadir un botón para dar a entender que se puede copiar
    if st.button("Copiar enlace de descarga"):
        st.write("El enlace ha sido copiado. Usa Ctrl+C o haz clic derecho para copiar.")



# Función principal
def main():
    st.title("Buscador de Películas y Series")

    content_type = st.radio("Elige una opción:", ('Películas', 'Series', 'Ver lista de Real Debrid'))

    if content_type == 'Ver lista de Real Debrid':
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
