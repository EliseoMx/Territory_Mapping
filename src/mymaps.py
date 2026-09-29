# -*- coding: utf-8 -*-
"""
Publica un KML en Google My Maps y devuelve la liga.

My Maps no tiene API publica, asi que esto maneja el navegador como lo haria
una persona: crea un mapa nuevo, importa el KML, le pone nombre y activa
"cualquier persona con el vinculo puede verlo".

Por que asi y no con Selenium/Playwright lanzando su propio navegador:
Google bloquea el inicio de sesion en navegadores controlados por
automatizacion ("este navegador puede no ser seguro"). Aqui se abre un Chrome
normal, con un perfil propio del programa, y solo despues nos conectamos por
el puerto de depuracion. La primera vez inicias sesion a mano en esa ventana;
el perfil la recuerda y las siguientes corridas ya no la piden.
"""

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from urllib.parse import parse_qs, urlparse

PORT = 9333
HOME_URL = "https://www.google.com/maps/d/?hl=en"
CREATE_URL = "https://www.google.com/maps/d/create?hl=en"
# Sin sesion, /maps/d/create responde 404 en vez de pedir login. Por eso se
# entra primero por el login de Google con My Maps como destino: si ya hay
# sesion, Google redirige de inmediato.
LOGIN_URL = ("https://accounts.google.com/ServiceLogin?hl=en&continue="
             "https%3A%2F%2Fwww.google.com%2Fmaps%2Fd%2F%3Fhl%3Den")
VIEWER_URL = "https://www.google.com/maps/d/viewer?mid=%s"
EDIT_URL = "https://www.google.com/maps/d/edit?mid=%s"
LOGIN_TIMEOUT = 300   # segundos para iniciar sesion la primera vez


class MyMapsError(Exception):
    pass


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache")
    return os.path.join(base, "Territory_Mapping")


def profile_dir():
    return os.path.join(data_dir(), "chrome-perfil")


def find_browser():
    """Chrome, o Edge si no hay Chrome. TM_CHROME fuerza una ruta."""
    forced = os.environ.get("TM_CHROME")
    if forced and os.path.isfile(forced):
        return forced
    roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    rel = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"]
    for r in rel:
        for root in roots:
            if root:
                cand = os.path.join(root, r)
                if os.path.isfile(cand):
                    return cand
    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _devtools_up(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1):
            return True
    except Exception:
        return False


def launch_browser(port=PORT):
    """Abre el navegador con el perfil del programa, o reusa el que ya este abierto."""
    if _devtools_up(port):
        return
    exe = find_browser()
    if not exe:
        raise MyMapsError("no encontre Google Chrome ni Microsoft Edge instalados.")
    os.makedirs(profile_dir(), exist_ok=True)
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [exe, "--remote-debugging-port=%d" % port, "--user-data-dir=" + profile_dir(),
         "--no-first-run", "--no-default-browser-check", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags,
    )
    for _ in range(40):
        if _devtools_up(port):
            return
        time.sleep(0.5)
    raise MyMapsError(
        "el navegador no abrio el puerto de depuracion %d. "
        "Cierra las ventanas de Chrome que abrio este programa y vuelve a intentar." % port)


# --------------------------------------------------------------------------
# Pasos dentro de My Maps
# --------------------------------------------------------------------------

def _alive(page):
    try:
        return not page.is_closed()
    except Exception:
        return False


def _ensure_login(page, log):
    """Deja la pestana en My Maps con sesion iniciada."""
    page.goto(LOGIN_URL)
    fin = time.time() + LOGIN_TIMEOUT
    avisado = False
    while True:
        if not _alive(page):
            raise MyMapsError("se cerro la pestana de Chrome antes de terminar. "
                              "Deja abierta la ventana que abre el programa.")
        url = page.url
        if "accounts.google.com" not in url and "/maps/d" in url:
            return
        if not avisado and "accounts.google.com" in url:
            log("  google  : inicia sesion en la ventana de Chrome que se abrio "
                "(solo la primera vez; tienes %d min)" % (LOGIN_TIMEOUT // 60))
            avisado = True
        if time.time() > fin:
            raise MyMapsError("no se completo el inicio de sesion a tiempo.")
        page.wait_for_timeout(1000)


def _editor_page(ctx):
    for pg in ctx.pages:
        if _alive(pg) and "/maps/d/edit" in pg.url:
            return pg
    return None


def _open_editor(ctx, page, log):
    """Crea un mapa nuevo y devuelve (pestana del editor, mid)."""
    # Camino corto: la URL directa de creacion.
    page.goto(CREATE_URL)
    fin = time.time() + 15
    while time.time() < fin and not _editor_page(ctx):
        page.wait_for_timeout(700)
    ed = _editor_page(ctx)

    # Camino largo: el boton "Create a new map" de la portada de My Maps.
    if not ed:
        page.goto(HOME_URL)
        page.wait_for_timeout(2000)
        if not _click_first(page, [re.compile(r"create a new map", re.I),
                                   re.compile(r"^\s*create\s*$", re.I)], timeout=20000):
            raise MyMapsError("no encontre el boton 'Create a new map' en My Maps.")
        fin = time.time() + 30
        while time.time() < fin and not _editor_page(ctx):
            page.wait_for_timeout(700)
        ed = _editor_page(ctx)
    if not ed:
        raise MyMapsError("My Maps no abrio el editor del mapa nuevo.")

    ed.bring_to_front()
    ed.wait_for_load_state("domcontentloaded")
    mid = parse_qs(urlparse(ed.url).query).get("mid", [None])[0]
    if not mid:
        raise MyMapsError("My Maps no devolvio el identificador del mapa.")
    return ed, mid


def _click_first(page, patterns, timeout=15000):
    """Hace clic en el primer elemento visible cuyo texto coincida."""
    fin = time.time() + timeout / 1000.0
    while time.time() < fin:
        for pat in patterns:
            loc = page.get_by_text(pat)
            try:
                n = loc.count()
            except Exception:
                n = 0
            for k in range(n):
                el = loc.nth(k)
                try:
                    if el.is_visible():
                        el.click()
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(500)
    return False


def _picker_frames(page):
    return [f for f in page.frames if "picker" in f.url or "docs.google.com" in f.url]


def _upload(page, kml_path):
    if not _click_first(page, [re.compile(r"^\s*Import\s*$")], timeout=30000):
        raise MyMapsError("no encontre el boton Import de la capa.")
    fin = time.time() + 45
    while time.time() < fin:
        for fr in page.frames:
            try:
                inp = fr.query_selector("input[type=file]")
            except Exception:
                inp = None
            if inp:
                inp.set_input_files(kml_path)
                return
        page.wait_for_timeout(700)
    # Plan B: el boton de "Browse" abre el selector de archivos del sistema.
    rx = re.compile(r"Browse|Select a file|Upload", re.I)
    for fr in page.frames:
        loc = fr.get_by_role("button", name=rx)
        try:
            if loc.count():
                with page.expect_file_chooser(timeout=10000) as fc:
                    loc.first.click()
                fc.value.set_files(kml_path)
                return
        except Exception:
            continue
    raise MyMapsError("no aparecio el cuadro para subir el archivo.")


def _wait_import(page, primer_nombre):
    fin = time.time() + 120
    while time.time() < fin:
        if not _picker_frames(page):
            try:
                if page.get_by_text(primer_nombre, exact=True).count():
                    return True
            except Exception:
                pass
        page.wait_for_timeout(1000)
    return False


def _rename(page, nombre):
    if not _click_first(page, [re.compile(r"^\s*Untitled map\s*$")], timeout=10000):
        return False
    page.wait_for_timeout(800)
    box = page.locator("input[type=text]:visible").first
    try:
        box.fill(nombre)
    except Exception:
        return False
    return _click_first(page, [re.compile(r"^\s*Save\s*$")], timeout=5000)


def _make_public(page):
    if not _click_first(page, [re.compile(r"^\s*Share\s*$")], timeout=10000):
        return False
    page.wait_for_timeout(1500)
    rx = re.compile(r"Anyone with (this|the) link", re.I)
    # El interruptor puede vivir en la pagina o en un iframe de Drive.
    for fr in [page.main_frame] + list(page.frames):
        try:
            sw = fr.get_by_role("switch", name=rx)
            if not sw.count():
                sw = fr.get_by_role("checkbox", name=rx)
            if not sw.count():
                sw = fr.locator("[role=dialog] [role=switch]")
            if sw.count():
                el = sw.first
                if el.get_attribute("aria-checked") != "true":
                    el.click()
                    page.wait_for_timeout(1500)
                ok = el.get_attribute("aria-checked") == "true"
                break
        except Exception:
            continue
    else:
        ok = False
    _click_first(page, [re.compile(r"^\s*(Close|Done)\s*$")], timeout=3000) or page.keyboard.press("Escape")
    return ok


def publish(kml_path, nombre, primer_punto="Punto 1", publico=True, log=print, debug_dir=None):
    """Crea el mapa en My Maps. Devuelve dict con mid, viewer, edit, publico y avisos."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise MyMapsError("falta el paquete playwright (pip install playwright).")

    launch_browser()
    avisos = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:%d" % PORT)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        page.bring_to_front()
        try:
            _ensure_login(page, log)
            log("  google  : creando mapa en My Maps...")
            page, mid = _open_editor(ctx, page, log)
            page.wait_for_timeout(2500)
            page.keyboard.press("Escape")   # cierra avisos de bienvenida si salen

            _upload(page, os.path.abspath(kml_path))
            if not _wait_import(page, primer_punto):
                avisos.append("no pude confirmar que el KML se importo; revisa el mapa.")

            if not _rename(page, nombre):
                avisos.append("no pude ponerle nombre al mapa (quedo como 'Untitled map').")

            es_publico = False
            if publico:
                es_publico = _make_public(page)
                if not es_publico:
                    avisos.append("no pude hacerlo publico: abre la liga de edicion, "
                                  "Share, y activa 'Anyone with this link can view'.")
        except Exception as exc:
            if debug_dir:
                try:
                    shot = os.path.join(debug_dir, "mymaps_error.png")
                    page.screenshot(path=shot)
                    log("  captura : %s" % shot)
                except Exception:
                    pass
            if isinstance(exc, MyMapsError):
                raise
            if "has been closed" in str(exc):
                raise MyMapsError("se cerro la ventana o pestana de Chrome a medio proceso. "
                                  "Deja abierta la ventana que abre el programa.")
            raise MyMapsError(str(exc).splitlines()[0] if str(exc) else repr(exc))

    return {
        "mid": mid,
        "viewer": VIEWER_URL % mid,
        "edit": EDIT_URL % mid,
        "publico": es_publico,
        "avisos": avisos,
    }
