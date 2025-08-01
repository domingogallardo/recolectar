from pathlib import Path
from config import BASE_DIR, INCOMING, HISTORIAL
from datetime import datetime
import os, shutil, logging, re

def list_files(exts, root=INCOMING):
    return [p for p in Path(root).rglob("*") if p.suffix.lower() in exts]

def is_podcast_file(file_path: Path) -> bool:
    """Detecta si un archivo MD es un podcast exportado de Snipd."""
    try:
        if not file_path.suffix.lower() == '.md':
            return False
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return "Episode metadata" in content and "## Snips" in content
    except Exception:
        return False

def list_podcast_files(root=INCOMING):
    """Lista todos los archivos MD que son podcasts."""
    md_files = list_files({".md"}, root)
    return [f for f in md_files if is_podcast_file(f)]

def extract_episode_title(file_path: Path) -> str | None:
    """Extrae el título del episodio de los metadatos del archivo de podcast."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        show_match = re.search(r"- Show:\s*(.+)", content)
        episode_match = re.search(r"- Episode title:\s*(.+)", content)
        
        if episode_match:
            episode_title = episode_match.group(1).strip()
            show_name = show_match.group(1).strip() if show_match else None
            
            # Construir título final
            full_title = f"{show_name} - {episode_title}" if show_name else episode_title
            
            # Limpiar caracteres problemáticos para nombres de archivo
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', full_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            return clean_title[:200]  # Limitar longitud
        return None
    except Exception:
        return None

def rename_podcast_files(podcasts: list[Path]) -> list[Path]:
    """Renombra archivos de podcast usando el título del episodio."""
    renamed_files = []
    
    for podcast in podcasts:
        title = extract_episode_title(podcast)
        if not title:
            renamed_files.append(podcast)
            print(f"⚠️  No se pudo extraer título de: {podcast.name}")
            continue
            
        # Generar nombres únicos para MD y HTML
        new_md_path = podcast.parent / f"{title}.md"
        new_html_path = podcast.parent / f"{title}.html"
        
        # Evitar conflictos si ya existe
        counter = 1
        while new_md_path.exists():
            new_md_path = podcast.parent / f"{title} ({counter}).md"
            new_html_path = podcast.parent / f"{title} ({counter}).html"
            counter += 1
        
        # Renombrar archivos
        podcast.rename(new_md_path)
        renamed_files.append(new_md_path)
        
        html_path = podcast.with_suffix('.html')
        if html_path.exists():
            html_path.rename(new_html_path)
            renamed_files.append(new_html_path)
        
        print(f"📻 Renombrado: {podcast.name} → {new_md_path.name}")
    
    return renamed_files

def move_files(files, dest):
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in files:
        new_path = dest / f.name
        shutil.move(str(f), new_path)
        moved.append(new_path)
    return moved

def register_paths(paths, base_dir: Path = None, historial_path: Path = None):
    """Registra rutas en el historial. Acepta base_dir y historial_path configurables para tests."""
    if not paths:
        return
    
    # Usar valores por defecto si no se especifican (compatibilidad hacia atrás)
    if base_dir is None:
        base_dir = BASE_DIR
    if historial_path is None:
        historial_path = HISTORIAL
    
    # Agregar fecha y hora al final de cada línea
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines_new = ["./" + p.relative_to(base_dir).as_posix() + " - " + timestamp + "\n" for p in paths]
    if historial_path.exists():
        old_content = historial_path.read_text(encoding="utf-8")
    else:
        old_content = ""
    historial_path.write_text("".join(lines_new) + old_content, encoding="utf-8")

def setup_logging(level="INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

def add_margins_to_html_files(directory: Path, file_filter=None):
    """
    Añade márgenes del 6% a todos los archivos HTML en un directorio.
    
    Args:
        directory: Directorio donde buscar archivos HTML
        file_filter: Función opcional para filtrar qué archivos procesar (ej: is_podcast_file)
    """
    from bs4 import BeautifulSoup
    
    margin_style = "body { margin-left: 6%; margin-right: 6%; }"
    
    html_files = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(('.html', '.htm')):
                file_path = Path(dirpath) / filename
                # Aplicar filtro si se proporciona
                if file_filter is None or file_filter(file_path):
                    html_files.append(file_path)
    
    if not html_files:
        print('📏 No hay archivos HTML para añadir márgenes')
        return
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
            
            # Buscar la etiqueta <head>
            head = soup.head
            if head is None:
                # Si no existe, crear un <head> nuevo y añadir el estilo
                head = soup.new_tag("head")
                style_tag = soup.new_tag("style")
                style_tag.string = margin_style
                head.append(style_tag)
                if soup.html:
                    soup.html.insert(0, head)
            else:
                # Si ya hay <head>, verificar si hay una etiqueta <style>
                style_tag = head.find("style")
                if style_tag:
                    # Si hay una etiqueta <style>, añadir el margen al final del contenido existente
                    style_tag.string += "\n" + margin_style
                else:
                    # Si no hay <style>, crear una nueva etiqueta <style> con el margen
                    style_tag = soup.new_tag("style")
                    style_tag.string = margin_style
                    head.append(style_tag)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print(f"📏 Márgenes añadidos: {html_file.name}")
            
        except Exception as e:
            print(f"❌ Error añadiendo márgenes a {html_file}: {e}")


def clean_duplicate_markdown_links(text: str) -> str:
    """Limpia enlaces Markdown donde el texto y la URL son idénticos."""
    import re
    
    # Patrón para encontrar enlaces Markdown donde el texto es la misma URL
    # [https://example.com](https://example.com)
    duplicate_link_pattern = r'\[(https?://[^\]]+)\]\(\1\)'
    
    def replace_duplicate_link(match):
        url = match.group(1)
        # Extraer dominio y path corto para mostrar
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Si el path es muy largo, truncarlo
            path = parsed.path
            if len(path) > 30:
                path = path[:27] + "..."
            display_text = f"{domain}{path}"
            return f'[{display_text}]({url})'
        except:
            # Si hay algún error, usar un texto genérico
            return f'[Ver enlace]({url})'
    
    return re.sub(duplicate_link_pattern, replace_duplicate_link, text)


def convert_urls_to_links(text: str) -> str:
    """Convierte URLs de texto plano a enlaces Markdown de forma robusta."""
    import re
    
    # Primero limpiar enlaces duplicados
    text = clean_duplicate_markdown_links(text)
    
    # Dividir el texto en líneas para procesar línea por línea
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        # Buscar URLs que no estén ya en enlaces Markdown o HTML
        if 'http' in line:
            # Regex para encontrar URLs con sus posiciones
            url_pattern = r'https?://[^\s\)\]>"\']+'
            matches = list(re.finditer(url_pattern, line))
            
            # Procesar matches en orden inverso para no alterar posiciones
            for match in reversed(matches):
                url = match.group()
                start_pos = match.start()
                
                # Verificar el contexto antes de la URL
                prefix = line[:start_pos].lower()
                
                # Verificar si está en un enlace Markdown o atributo HTML de forma robusta
                prefix_lines = prefix.split('\n')
                is_in_markdown_link = '](' in prefix_lines[-1] if prefix_lines else False
                
                prefix_words = prefix.split()
                last_word = prefix_words[-1] if prefix_words else ""
                is_in_html_attribute = any(attr in last_word for attr in [
                    'href=', 'src=', 'srcset=', 'poster=', 'data-src=', 'action=', 'cite='
                ])
                is_in_css_url = 'url(' in last_word
                
                # Solo convertir si no está en ningún contexto especial
                if not (is_in_markdown_link or is_in_html_attribute or is_in_css_url):
                    # Reemplazar la URL
                    line = line[:start_pos] + f'[{url}]({url})' + line[match.end():]
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def convert_newlines_to_br(html_text: str) -> str:
    """
    Convierte saltos de línea simples a elementos <br>, pero solo dentro del contenido,
    no entre elementos de bloque HTML.
    """
    import re
    
    # Procesar solo el contenido dentro de elementos de bloque
    def replace_in_content(match):
        tag_open = match.group(1)
        content = match.group(2)
        tag_close = match.group(3)
        
        # Solo aplicar nl2br al contenido, no a los saltos estructurales
        content_with_br = content.replace('\n', '<br>\n')
        
        return f"{tag_open}{content_with_br}{tag_close}"
    
    # Aplicar nl2br solo dentro de párrafos y otros elementos de contenido
    html_text = re.sub(r'(<p[^>]*>)(.*?)(</p>)', replace_in_content, html_text, flags=re.DOTALL)
    html_text = re.sub(r'(<li[^>]*>)(.*?)(</li>)', replace_in_content, html_text, flags=re.DOTALL)
    html_text = re.sub(r'(<div[^>]*>)(.*?)(</div>)', replace_in_content, html_text, flags=re.DOTALL)
    
    return html_text


def markdown_to_html(md_text: str, title: str = None) -> str:
    """
    Convierte texto Markdown a HTML completo con limpieza y URLs clickables.
    
    Args:
        md_text: Texto en formato Markdown
        title: Título para el HTML (opcional)
        
    Returns:
        HTML completo con <html>, <head>, <body>
    """
    import markdown
    
    # Limpiar solo caracteres realmente problemáticos
    md_text = md_text.replace('\xa0', ' ')  # Non-breaking space problemático
    
    # Convertir URLs de texto plano a enlaces Markdown
    md_text = convert_urls_to_links(md_text)
    
    # Convertir a HTML
    try:
        html_body = markdown.markdown(
            md_text,
            extensions=[
                "fenced_code",
                "tables", 
                "toc",
            ],
            output_format="html5",
        )
    except Exception as e:
        print(f"⚠️  Error en conversión markdown, intentando sin extensiones: {e}")
        html_body = markdown.markdown(md_text, output_format="html5")
    
    # Aplicar conversión nl2br: todos los saltos de línea → <br>
    html_body = convert_newlines_to_br(html_body)
    
    # Crear HTML completo
    title_tag = f"<title>{title}</title>\n" if title else ""
    full_html = (
        "<!DOCTYPE html>\n"
        "<html>\n<head>\n<meta charset=\"UTF-8\">\n"
        f"{title_tag}"
        "</head>\n<body>\n"
        f"{html_body}\n"
        "</body>\n</html>\n"
    )
    
    return full_html


def get_base_css() -> str:
    """Devuelve el CSS base con la tipografía del sistema y estilos comunes."""
    return (
        "body { margin: 6%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }\n"
        "h1, h2, h3 { font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 10px; }\n"
        "blockquote { margin-left: 0; padding-left: 20px; color: #666; }\n"
        "a { text-decoration: none; }\n"
        "a:hover { text-decoration: underline; }\n"
        "hr { border: none; border-top: 1px solid #eee; margin: 30px 0; }\n"
    )