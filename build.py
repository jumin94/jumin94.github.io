#!/usr/bin/env python3
"""
Build the website from the `content/` folder into `docs/`.

    python3 build.py          # build once
    python3 build.py --serve  # build and preview at http://localhost:8000

No installation needed. If Pillow is installed, photos are resized for the web
(much faster page loads); otherwise they are copied as they are.

You normally never need to edit this file: edit the files in `content/`.
"""
import html
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
ASSETS = ROOT / "assets"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PX = 1600
import time
VERSION = str(int(time.time()))  # new on every build, so browsers never use an old style.css

try:
    from PIL import Image, ImageOps
except ImportError:  # optional
    Image = None


# --------------------------------------------------------------------------
# Languages
#   English is the main language. A Spanish version of any content file sits
#   next to it with .es.md (about.es.md, index.es.md, highlight.es.md ...) and only
#   needs the fields that change (title, role, text...). Everything missing falls
#   back to English, and the build lists what is not translated yet.
# --------------------------------------------------------------------------
LANGS = {"en": "", "es": "es/"}      # language -> output sub-folder
LANG, PREFIX, MISSING = "en", "", []

UI = {"es": {
    "About": "Sobre mí", "Highlight": "Destacado", "Publications": "Publicaciones",
    "Research": "Investigación", "Journey": "Recorrido", "Conferences": "Congresos",
    "Projects": "Proyectos", "Music": "Música", "Books": "Libros",
    "The CV": "El CV", "The person": "La persona", "Enter": "Entrá", "Why": "Por qué",
    "Talks": "Charlas", "Education": "Formación", "Further reading": "Para seguir leyendo", "Experience": "Trayectoria", "Awards": "Premios",
    "Experience & education": "Trayectoria y formación", "Awards & funding": "Premios y financiamiento",
    "Books I recommend": "Libros que recomiendo", "See the book": "Mirá el libro",
    "Email": "Email", "Institute page": "Página del instituto", "CV (PDF)": "CV (PDF)",
    "Highlight of the month": "Destacado del mes", "Read more": "Leé más",
    "Past highlights": "Destacados anteriores", "Award": "Premio",
    "published": "publicado", "under review": "en revisión", "submitted": "enviado",
    "in preparation": "en preparación",
    "Under review & in preparation": "En revisión y en preparación",
    "upcoming": "próximamente", "Recorded talks": "Charlas grabadas", "Marie Curie": "Marie Curie", "Project page": "Página del proyecto", "Videos": "Videos", "Watch": "Video",
    "Watch on YouTube": "Mirá en YouTube", "In Spanish": "En castellano", "In English": "En inglés",
    "Talks, conferences & organisation": "Charlas, congresos y organización",
    "Year": "Año", "Event": "Evento", "Contribution": "Participación",
    "★ keynote or invited": "★ conferencia plenaria o invitada",
    "Publications & conferences": "Publicaciones y congresos",
    "peer-reviewed publications": "publicaciones con referato",
    "under review or in preparation": "en revisión o en preparación",
    "related papers": "artículos relacionados",
    "Research in a nutshell": "Mi investigación en pocas palabras",
    "Academic journey": "Recorrido académico",
    "From the road: conferences & what I learned": "Desde el camino: congresos y lo que aprendí",
    "Other projects & activities": "Otros proyectos y actividades",
    "Visit": "Visitá", "Listen": "Escuchá", "Last updated": "Última actualización",
    # roles in talks_and_conferences.md
    "Keynote": "Conferencia plenaria", "Invited talk": "Charla invitada",
    "Invited lecture": "Clase invitada", "Invited speaker": "Oradora invitada",
    "Invited seminar": "Seminario invitado", "Invited highlight talk": "Charla destacada invitada",
    "Talk": "Charla", "Departmental seminar": "Seminario departamental",
    "Convener": "Coordinadora de sesión", "Co-convener": "Co-coordinadora de sesión",
    "Co-organizer": "Co-organizadora", "Scientific committee": "Comité científico",
    "Organizing committee": "Comité organizador",
}}
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
PLACES_ES = [("Mexico City", "Ciudad de México"), ("Mexico", "México"), ("Switzerland", "Suiza"),
             ("Lausanne", "Lausana"), ("Bern", "Berna"), ("Kenya", "Kenia"), ("Vienna", "Viena"),
             ("Brazil", "Brasil"), ("Spain", "España"), ("USA", "EE. UU."), ("Germany", "Alemania"),
             ("United Kingdom", "Reino Unido"), ("UK", "Reino Unido"), ("Italy", "Italia"),
             ("Online", "En línea"), ("hybrid", "híbrido")]


def T(text):
    """Translate an interface word (English -> current language)."""
    return UI.get(LANG, {}).get(text, text)


def T_place(text):
    if LANG == "es":
        for en, es in PLACES_ES:
            text = re.sub(rf"\b{re.escape(en)}\b", es, text)
    return text


def is_translation(path):
    return re.search(r"\.[a-z]{2}\.md$", path.name) is not None


# --------------------------------------------------------------------------
# Reading content files
# --------------------------------------------------------------------------
def parse_fields(text):
    """'key: value' lines -> dict. Lines starting with # are comments."""
    data = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip().lower()] = v.strip()
    return data


def _read_md(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        meta, body = parse_fields(m.group(1)), m.group(2)
    return meta, body.strip()


def read_md(path, translate=True):
    """A Markdown file with an optional '---' header block of key: value lines.
    In another language, fields/text from the .es.md twin replace the English ones."""
    meta, body = _read_md(path)
    if LANG != "en" and translate:
        twin = path.with_name(f"{path.stem}.{LANG}.md")
        if twin.exists():
            tmeta, tbody = _read_md(twin)
            meta.update(tmeta)
            body = tbody or body
        elif body or meta.get("title"):
            MISSING.append(twin.relative_to(CONTENT).as_posix())
    return meta, body


def read_entries(path):
    """A list file: entries of key: value lines separated by '---' lines."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"^\s*---\s*$", text, flags=re.M)
    return [e for e in (parse_fields(b) for b in blocks) if e]


def images_in(folder):
    """Photos in the folder, plus any in a subfolder (e.g. pictures/ or fotos/)."""
    found = []
    for p in sorted(folder.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_dir():
            found += [q for q in sorted(p.iterdir()) if q.suffix.lower() in IMG_EXT and not q.name.startswith(".")]
        elif p.suffix.lower() in IMG_EXT:
            found.append(p)
    return sorted(found, key=lambda q: q.name)


def caption_from(path):
    """'03_poster-session_with_team.jpg' -> 'Poster session with team'."""
    name = re.sub(r"^\d+[_\-\s]*", "", path.stem)
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name[:1].upper() + name[1:] if name else ""


def publish_image(src):
    """Copy (and shrink) an image into docs/media, return its URL."""
    rel = src.relative_to(CONTENT)
    dest = OUT / "media" / rel
    url = PREFIX + "media/" + rel.as_posix()
    if dest.exists():
        return url
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Image and src.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail((MAX_PX, MAX_PX))
                if src.suffix.lower() in {".jpg", ".jpeg"}:
                    im.convert("RGB").save(dest, quality=85, optimize=True)
                else:
                    im.save(dest, optimize=True)
            return url
        except Exception as exc:  # fall back to a plain copy
            print(f"  ! could not resize {rel}: {exc}")
    shutil.copy2(src, dest)
    return url


def build_lake():
    """Background photos from content/lake/, in file-name order: first = surface, last = deepest.
    Saved at 2000px without EXIF data (so phone GPS locations are not published)."""
    folder = CONTENT / "lake"
    photos = sorted(p for p in folder.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}) \
        if folder.exists() else []
    if not photos:
        return ""
    layers = []
    for src in photos:
        rel = src.relative_to(CONTENT).with_suffix(".jpg")
        dest = OUT / "media" / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if Image:
                with Image.open(src) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((2000, 2000))
                    im.save(dest, quality=78, optimize=True, progressive=True)
            else:
                shutil.copy2(src, dest)
        layers.append(f'<div class="layer" style="background-image:url(\'{PREFIX}media/{rel.as_posix()}\')"></div>')
    unit = "m"
    return (f'<div class="lake" aria-hidden="true"><div class="drift">{"".join(layers)}</div></div>\n'
            f'<div class="depth" aria-hidden="true"><span class="mark"><b>0</b> {unit}</span></div>')


def publish_file(src):
    rel = src.relative_to(CONTENT)
    dest = OUT / "media" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return PREFIX + "media/" + rel.as_posix()


# --------------------------------------------------------------------------
# Minimal Markdown
# --------------------------------------------------------------------------
def inline(text, base=None):
    text = html.escape(text, quote=False)

    def img(m):
        src = m.group(2)
        if base and not re.match(r"https?://", src):
            p = base / src
            src = publish_image(p) if p.exists() else src
        return f'<img src="{src}" alt="{m.group(1)}" loading="lazy">'

    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", img, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: f'<a href="{m.group(2)}"{ext(m.group(2))}>{m.group(1)}</a>', text)
    text = re.sub(r"(?<![\"=>])(https?://[^\s<]+[^\s<.,;:)])",
                  lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def ext(url):
    return ' target="_blank" rel="noopener"' if re.match(r"https?://", url) else ""


def markdown(text, base=None):
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        b = block.strip()
        if not b:
            continue
        if b.startswith("<"):  # raw HTML or <!-- comments --> pass through
            out.append(b)
        elif m := re.match(r"^(#{1,4})\s+(.*)", b):
            lvl = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{inline(m.group(2), base)}</h{lvl}>")
        elif all(re.match(r"^\s*[-*]\s+", l) for l in b.splitlines()):
            items = [inline(re.sub(r"^\s*[-*]\s+", "", l), base) for l in b.splitlines()]
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        elif all(re.match(r"^\s*\d+[.)]\s+", l) for l in b.splitlines()):
            items = [inline(re.sub(r"^\s*\d+[.)]\s+", "", l), base) for l in b.splitlines()]
            out.append("<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>")
        elif b.startswith(">"):
            q = " ".join(re.sub(r"^>\s?", "", l) for l in b.splitlines())
            out.append(f"<blockquote>{inline(q, base)}</blockquote>")
        else:
            out.append("<p>" + "<br>".join(inline(l, base) for l in b.splitlines()) + "</p>")
    return "\n".join(out)


def esc(s):
    return html.escape(s or "")


def split_list(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


# Where each section lives inside content/
DIRS = {
    "home": "home",
    "cv": "the_cv",
    "publications": "the_cv/2_publications",
    "talks": "the_cv/3_talks_and_conferences.md", "videos": "the_cv/3_recorded_talks", "msca": "the_cv/7_marie_curie_project",
    "experience": "the_cv/1_experience_and_education.md",
    "research": "the_cv/4_research_summary",
    "awards": "the_cv/5_awards_and_funding.md",
    "projects": "the_cv/6_projects_and_activities",
    "person": "the_person",
    "highlight": "the_person/1_highlight_of_the_month",
    "thinking": "the_person/2_education",
    "books": "the_person/3_books",
    "journey": "the_person/4_academic_journey",
    "conferences": "the_person/5_conference_gallery",
    "music": "the_person/6_music",
}


def section_dir(key):
    p = CONTENT / DIRS[key]
    return p if p.exists() else None


def intro_of(folder, name="_intro.md"):
    return read_md(folder / name) if folder and (folder / name).exists() else ({}, "")


def subfolders(folder):
    return sorted((p for p in folder.iterdir()
                   if p.is_dir() and not p.name.startswith(("_", "."))), key=lambda p: p.name)


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
LINK_LABELS = [("email", "Email"), ("scholar", "Google Scholar"), ("orcid", "ORCID"),
               ("institute", "Institute page"), ("github", "GitHub"), ("bluesky", "Bluesky"),
               ("linkedin", "LinkedIn"), ("mastodon", "Mastodon")]


def portrait(meta):
    folder = section_dir("home")
    photos = [p for p in images_in(folder) if p.stem.lower().startswith("photo")]
    if photos:
        return f'<img class="portrait" src="{publish_image(photos[0])}" alt="{esc(meta.get("name"))}">'
    initials = "".join(w[0] for w in meta.get("name", "?").split()[:2])
    return f'<div class="portrait placeholder" aria-hidden="true">{esc(initials)}</div>'


def link_pills(meta):
    folder = section_dir("home")
    links = []
    for key, label in LINK_LABELS:
        if v := meta.get(key):
            href = f"mailto:{v}" if key == "email" else v
            links.append(f'<a class="pill" href="{esc(href)}"{ext(href)}>{T(label)}</a>')
    cvs = [p for p in folder.iterdir() if p.suffix.lower() == ".pdf"]
    if cvs:
        links.append(f'<a class="pill" href="{publish_file(cvs[0])}" target="_blank">{T("CV (PDF)")}</a>')
    return f'<nav class="pills">{"".join(links)}</nav>'


def read_home():
    return read_md(section_dir("home") / "about.md")


def entry(e, key):
    """Field of a list entry, in Spanish if a key_es version exists."""
    return e.get(f"{key}_{LANG}") or e.get(key, "") if LANG != "en" else e.get(key, "")


def build_cv_header(meta):
    meta_bio, bio = intro_of(section_dir("cv"), "_bio.md")
    return f"""
<header class="page-head" id="about">
  <div class="mini">{portrait(meta)}<div>
    <h1>{esc(meta.get("name"))}</h1>
    <p class="tagline">{esc(meta.get("tagline"))}</p>
    <p class="affiliation">{esc(meta.get("affiliation"))}</p>
  </div></div>
  <div class="bio">{markdown(bio, section_dir("cv"))}</div>
  {link_pills(meta)}
</header>"""


def build_experience():
    f = section_dir("experience")
    if not f:
        return ""
    rows = []
    for e in read_entries(f):
        kind = e.get("kind", "position")
        place = entry(e, "place")
        rows.append(f"""<li class="cv-row {esc(kind)}"><span class="when">{esc(e.get('years'))}</span>
<div><strong>{inline(entry(e, 'role'))}</strong>{f'<div class="where">{esc(place)}</div>' if place else ''}</div></li>""")
    return f"""
<section id="experience">
  <h2>{T('Experience & education')}</h2>
  <ul class="cv-list">{''.join(rows)}</ul>
</section>"""


def build_awards():
    f = section_dir("awards")
    if not f:
        return ""
    rows = "".join(f"""<li class="cv-row"><span class="when">{esc(e.get('years'))}</span>
<div>{inline(entry(e, 'title'))}</div></li>""" for e in read_entries(f))
    return f"""
<section id="awards">
  <h2>{T('Awards & funding')}</h2>
  <ul class="cv-list">{rows}</ul>
</section>"""


def build_abstract():
    meta, body = intro_of(section_dir("person"), "_abstract.md")
    return f"""
<header class="page-head person-head" id="purpose">
  <h1>{esc(meta.get('title', T('The person')))}</h1>
  <div class="abstract">{markdown(body, section_dir("person"))}</div>
</header>"""


def build_highlight():
    folder = section_dir("highlight")
    months = [p for p in subfolders(folder) if (p / "highlight.md").exists()]
    if not months:
        return ""
    months.sort(key=lambda p: p.name, reverse=True)

    def card(p, full=True):
        meta, body = read_md(p / "highlight.md")
        kind = meta.get("type", T("Highlight"))
        imgs = images_in(p)
        img = f'<img class="hl-img" src="{publish_image(imgs[0])}" alt="" loading="lazy">' if imgs else ""
        link = meta.get("link")
        btn = f'<a class="button" href="{esc(link)}"{ext(link)}>{esc(meta.get("link_text", T("Read more")))} →</a>' if link else ""
        return f"""
<article class="highlight{' compact' if not full else ''}">
  {img if full else ''}
  <div>
    <p class="kicker">{esc(kind)} · {esc(meta.get("month", p.name))}</p>
    <h3>{esc(meta.get("title"))}</h3>
    {markdown(body, p) if full else ''}
    {btn}
  </div>
</article>"""

    past = ""
    if len(months) > 1:
        past = f"<details class='past'><summary>{T('Past highlights')}</summary>" + \
               "".join(card(p, full=False) for p in months[1:]) + "</details>"
    return f"""
<section id="highlight">
  <h2>{T('Highlight of the month')}</h2>
  {card(months[0])}
  {past}
</section>"""


def load_publications():
    folder = section_dir("publications")
    pubs = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("_") or is_translation(p):
            continue
        meta, body = read_md(p, translate=False)
        meta["summary"] = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
        meta["id"] = p.stem
        pubs.append(meta)
    return pubs


def pub_line(pub, me):
    authors = esc(pub.get("authors"))
    for name in me:
        authors = authors.replace(esc(name), f"<strong>{esc(name)}</strong>")
    title = esc(pub.get("title"))
    url = pub.get("doi") or pub.get("link")
    if url:
        if not url.startswith("http"):
            url = "https://doi.org/" + url
        title = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>'
    venue = f" <em>{esc(pub.get('journal'))}</em>" if pub.get("journal") else ""
    status = pub.get("status", "published").lower()
    badge = "" if status == "published" else f' <span class="badge">{esc(T(status))}</span>'
    star = f' <span class="star" title="{T('Award')}">★</span>' if pub.get("award") else ""
    return f"<li>{authors} ({esc(pub.get('year'))}). {title}.{venue}{badge}{star}</li>"


def build_publications(pubs, me):
    published = [p for p in pubs if p.get("status", "published").lower() == "published"]
    pending = [p for p in pubs if p not in published]
    by_year = {}
    for p in sorted(published, key=lambda p: p.get("year", ""), reverse=True):
        by_year.setdefault(p.get("year", ""), []).append(p)

    groups = "".join(
        f"<h3 class='year'>{esc(y)}</h3><ul class='pubs'>{''.join(pub_line(p, me) for p in ps)}</ul>"
        for y, ps in by_year.items())
    if pending:
        groups += f"<h3 class='year'>{esc(T('Under review & in preparation'))}</h3><ul class='pubs'>" + \
                  "".join(pub_line(p, me) for p in pending) + "</ul>"

    # Talks & conferences table
    rows = []
    talks_file = section_dir("talks")
    if talks_file:
        entries = read_entries(talks_file)
        entries.sort(key=lambda e: e.get("date", ""), reverse=True)
        for e in entries:
            role = e.get("role", "")
            mark = " ★" if any(w in role.lower() for w in ("keynote", "invited")) else ""
            upcoming = f" <span class='badge'>{T('upcoming')}</span>" if e.get("date", "") > date.today().isoformat() else ""
            title = f"<div class='talk-title'>{inline(entry(e, 'title'))}</div>" if e.get("title") else ""
            if e.get("video"):
                title += f"<a class='watch' href='{esc(e['video'])}'{ext(e['video'])}>▶ {T('Watch')}</a>"
            rows.append(f"""<tr><td class="when">{esc(e.get('date', '')[:4])}</td>
<td><strong>{inline(entry(e, 'event'))}</strong>{upcoming}<div class="where">{esc(T_place(e.get('place', '')))}</div>{title}</td>
<td class="role">{esc(T(role))}{mark}</td></tr>""")
    table = f"""<div class="table-wrap"><table class="talks"><thead><tr><th>{T('Year')}</th><th>{T('Event')}</th><th>{T('Contribution')}</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="note">{T('★ keynote or invited')}</p>""" if rows else ""

    return f"""
<section id="publications">
  <h2>{esc(T('Publications'))}</h2>
  <p class="note">{len(published)} {T('peer-reviewed publications')} · {len(pending)} {T('under review or in preparation')}</p>
  {groups}
</section>""" + build_videos() + (DIVIDER + f"""
<section id="talks">
  <h2>{esc(T('Talks, conferences & organisation'))}</h2>
  {table}
</section>""" if table else "")


def build_research(pubs, me):
    folder = section_dir("research")
    themes = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("_") or is_translation(p):
            continue
        meta, body = read_md(p)
        theme_id = re.sub(r"^\d+[_\-]", "", p.stem)
        related = [x for x in pubs if theme_id in split_list(x.get("themes"))]
        rel_html = ""
        if related:
            items = []
            for x in sorted(related, key=lambda x: x.get("year", ""), reverse=True):
                text = x.get("resumen") if LANG == "es" and x.get("resumen") else x.get("summary")
                summ = f"<p>{inline(text)}</p>" if text else ""
                items.append(f"<li><span class='yr'>{esc(x.get('year'))}</span> {esc(x.get('title'))}{summ}</li>")
            rel_html = f"<details><summary>{len(related)} {T('related papers')}</summary><ul class='related'>{''.join(items)}</ul></details>"
        imgs = images_in(folder / theme_id) if (folder / theme_id).is_dir() else []
        img = f'<img src="{publish_image(imgs[0])}" alt="" loading="lazy">' if imgs else ""
        themes.append(f"""<article class="theme">{img}<h3>{esc(meta.get('title'))}</h3>
{markdown(body, folder)}{rel_html}</article>""")
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    return f"""
<section id="research">
  <h2>{esc(intro_meta.get('title', T('Research in a nutshell')))}</h2>
  {markdown(intro, folder)}
  <div class="themes">{''.join(themes)}</div>
</section>"""


def translated_caption(img):
    """Captions for other languages: a captions.es.txt file next to the photos,
    one line per photo:  07_lake-shore.jpg: La orilla del lago"""
    f = img.parent / f"captions.{LANG}.txt"
    if not f.exists():
        if LANG != "en":   # English captions file is optional (file names are the default)
            MISSING.append(str(f.relative_to(CONTENT)))
        return ""
    for line in f.read_text(encoding="utf-8").splitlines():
        name, sep, cap = line.partition(":")
        if sep and name.strip() in (img.name, img.stem):
            return cap.strip()
    return ""


def gallery(imgs, group):
    if not imgs:
        return ""
    figs = []
    for p in imgs:
        url, cap = publish_image(p), caption_from(p)
        cap = translated_caption(p) or cap
        figs.append(f'<figure><a href="{url}" class="lightbox" data-group="{group}" data-caption="{esc(cap)}">'
                    f'<img src="{url}" alt="{esc(cap)}" loading="lazy"></a>'
                    f'{f"<figcaption>{esc(cap)}</figcaption>" if cap else ""}</figure>')
    return f'<div class="gallery">{"".join(figs)}</div>'


def build_journey():
    folder = section_dir("journey")
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    stops = []
    for p in subfolders(folder):
        if not (p / "index.md").exists():
            continue
        meta, body = read_md(p / "index.md")
        flag = meta.get("flag", "")
        stops.append(f"""<li class="stop">
  <div class="dot"></div>
  <p class="kicker">{esc(meta.get('years'))}</p>
  <h3>{esc(flag)} {esc(meta.get('place'))}</h3>
  <p class="role">{esc(meta.get('role'))}</p>
  {markdown(body, p)}
  {gallery(images_in(p), p.name)}
</li>""")
    return f"""
<section id="journey">
  <h2>{esc(intro_meta.get('title', T('Academic journey')))}</h2>
  {markdown(intro, folder)}
  <ol class="timeline">{''.join(stops)}</ol>
</section>"""


def build_thinking():
    """An essay in threads: _intro.md + one .md file per thread (1_..., 2_...)."""
    folder = section_dir("thinking")
    if not folder:
        return ""
    intro_meta, intro = intro_of(folder)
    threads = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("_") or is_translation(p):
            continue
        meta, body = read_md(p)
        link = meta.get("link")
        more = (f'<p class="further">{T("Further reading")}: <a href="{esc(link)}"{ext(link)}>'
                f'{esc(meta.get("link_text", link))}</a></p>') if link else ""
        threads.append(f"""<article class="thread">
  <h3>{esc(meta.get('title'))}</h3>
  {markdown(body, folder)}
  {more}
</article>""")
    return f"""
<section id="education">
  <h2>{esc(intro_meta.get('title', T('Education')))}</h2>
  <div class="thinking-intro">{markdown(intro, folder)}</div>
  <div class="threads">{''.join(threads)}</div>
</section>"""


def build_conferences():
    folder = section_dir("conferences")
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    cards = []
    for p in sorted(subfolders(folder), key=lambda p: p.name, reverse=True):
        if not (p / "index.md").exists():
            continue
        meta, body = read_md(p / "index.md")
        link = meta.get("link")
        title = esc(meta.get("title"))
        if link:
            title = f'<a href="{esc(link)}"{ext(link)}>{title}</a>'
        cards.append(f"""<article class="conf">
  <p class="kicker">{esc(meta.get('date'))} · {esc(T_place(meta.get('place', '')))}</p>
  <h3>{title}</h3>
  {f"<p class='role'>{esc(meta['role'])}</p>" if meta.get('role') else ''}
  {gallery(images_in(p), p.name)}
  <div class="reflection">{markdown(body, p)}</div>
</article>""")
    return f"""
<section id="conferences">
  <h2>{esc(intro_meta.get('title', T('From the road: conferences & what I learned')))}</h2>
  {markdown(intro, folder)}
  {''.join(cards)}
</section>"""


def build_projects():
    folder = section_dir("projects")
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    cards = []
    for p in subfolders(folder):
        if not (p / "index.md").exists():
            continue
        meta, body = read_md(p / "index.md")
        imgs = images_in(p)
        logo = f'<img class="logo" src="{publish_image(imgs[0])}" alt="" loading="lazy">' if imgs else ""
        link = meta.get("link")
        btn = f'<a class="button" href="{esc(link)}"{ext(link)}>{esc(meta.get("link_text", T("Visit")))} →</a>' if link else ""
        cards.append(f"""<article class="project">{logo}
  <p class="kicker">{esc(meta.get('years'))}</p>
  <h3>{esc(meta.get('title'))}</h3>
  <p class="role">{esc(meta.get('role'))}</p>
  {markdown(body, p)}{btn}</article>""")
    return f"""
<section id="projects">
  <h2>{esc(intro_meta.get('title', T('Other projects & activities')))}</h2>
  {markdown(intro, folder)}
  <div class="projects">{''.join(cards)}</div>
</section>"""


def embed_for(url):
    """YouTube / YouTube Music / Spotify / SoundCloud links -> embedded player."""
    if not url:
        return ""
    if m := re.search(r"[?&]list=([\w-]+)", url):
        src = f"https://www.youtube-nocookie.com/embed/videoseries?list={m.group(1)}"
    elif m := re.search(r"(?:youtu\.be/|v=|/live/|/shorts/)([\w-]{11})", url):
        src = f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
        if t := re.search(r"[?&]t=(\d+)", url):
            src += f"?start={t.group(1)}"
    elif m := re.search(r"open\.spotify\.com/(track|album|playlist|artist|episode)/(\w+)", url):
        return (f'<iframe class="player spotify" src="https://open.spotify.com/embed/{m.group(1)}/{m.group(2)}" '
                f'loading="lazy" allow="encrypted-media"></iframe>')
    elif "soundcloud.com" in url:
        return (f'<iframe class="player spotify" loading="lazy" src="https://w.soundcloud.com/player/?url='
                f'{html.escape(url)}&color=%23d6336c"></iframe>')
    else:
        return ""
    return (f'<div class="player video"><iframe src="{src}" loading="lazy" title="Player" '
            f'allow="encrypted-media; picture-in-picture" allowfullscreen></iframe></div>')


def build_msca():
    """content/the_cv/7_marie_curie_project/index.md: the Marie Curie project, as one section."""
    folder = section_dir("msca")
    if not folder or not (folder / "index.md").exists():
        return ""
    meta, body = read_md(folder / "index.md")
    link = meta.get("link")
    imgs = [i for i in images_in(folder)]
    fig = f'<img class="msca-img" src="{publish_image(imgs[0])}" alt="" loading="lazy">' if imgs else ""
    btn = f'<a class="button" href="{esc(link)}"{ext(link)}>{esc(meta.get("link_text", T("Project page")))} →</a>' if link else ""
    return f"""
<section id="msca">
  <h2>{esc(meta.get('title'))}</h2>
  <p class="kicker">{esc(meta.get('kicker', ''))}</p>
  <p class="msca-sub">{esc(meta.get('subtitle', ''))}</p>
  {fig}
  <div class="msca-body">{markdown(body, folder)}</div>
  {btn}
</section>"""


def build_videos():
    """content/the_cv/3_recorded_talks/: one .md per talk with a YouTube link."""
    folder = section_dir("videos")
    if not folder:
        return ""
    talks = []
    for f in sorted(folder.glob("*.md")):
        if f.name.startswith("_") or is_translation(f):
            continue
        meta, body = read_md(f)
        link = meta.get("link", "")
        lang = {"es": "In Spanish", "en": "In English"}.get(meta.get("language", ""), "")
        kicker = " · ".join(x for x in (meta.get("date"), meta.get("event"), T(lang) if lang else "") if x)
        talks.append(f"""<article class="video-item">
  <p class="kicker">{esc(kicker)}</p>
  <h3>{esc(meta.get('title'))}</h3>
  {embed_for(link)}
  {markdown(body, folder)}
  {f'<a class="button" href="{esc(link)}"{ext(link)}>{T("Watch on YouTube")} →</a>' if link else ''}
</article>""")
    if not talks:
        return ""
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    return DIVIDER + f"""
<section id="videos">
  <h2>{esc(intro_meta.get('title', T('Recorded talks')))}</h2>
  {markdown(intro, folder)}
  <div class="videos">{''.join(talks)}</div>
</section>"""


def build_music():
    folder = section_dir("music")
    if not folder:
        return ""
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    cards = []
    for p in subfolders(folder):
        if not (p / "index.md").exists():
            continue
        meta, body = read_md(p / "index.md")
        link = meta.get("link")
        player = embed_for(link)
        btn = f'<a class="button" href="{esc(link)}"{ext(link)}>{esc(meta.get("link_text", T("Listen")))} →</a>' if link else ""
        cards.append(f"""<article class="music-item">
  <p class="kicker">{esc(meta.get('kind'))}</p>
  <h3>{esc(meta.get('title'))}</h3>
  {markdown(body, p)}
  {player}
  {gallery(images_in(p), p.name)}
  {btn}
</article>""")
    return f"""
<section id="music">
  <h2>{esc(intro_meta.get('title', T('Music')))}</h2>
  <div class="music-intro">{markdown(intro, folder)}</div>
  <div class="music">{''.join(cards)}</div>
</section>"""


def fetch_cover(folder, isbn):
    """Download a book cover from Open Library by ISBN and keep it as cover.jpg."""
    import urllib.request
    isbn = re.sub(r"[^0-9Xx]", "", isbn)
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "personal-website-builder"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) > 2000:
            (folder / "cover.jpg").write_bytes(data)
            print(f"  downloaded cover for ISBN {isbn} -> {folder.relative_to(ROOT)}/cover.jpg")
            return folder / "cover.jpg"
    except Exception as exc:
        print(f"  ! no cover found for ISBN {isbn} ({exc}); add cover.jpg by hand")
    return None


def build_books():
    folder = section_dir("books")
    if not folder:
        return ""
    intro_meta, intro = read_md(folder / "_intro.md") if (folder / "_intro.md").exists() else ({}, "")
    cards = []
    for p in subfolders(folder):
        if not (p / "index.md").exists():
            continue
        meta, body = read_md(p / "index.md")
        imgs = images_in(p)
        cover = imgs[0] if imgs else (fetch_cover(p, meta["isbn"]) if meta.get("isbn") else None)
        cover_html = (f'<img class="cover" src="{publish_image(cover)}" alt="{esc(meta.get("title"))}" loading="lazy">'
                      if cover else '<div class="cover blank"></div>')
        link = meta.get("link")
        btn = f'<a class="button" href="{esc(link)}"{ext(link)}>{esc(meta.get("link_text", T("See the book")))} →</a>' if link else ""
        byline = " · ".join(x for x in (meta.get("author"), meta.get("year")) if x)
        cards.append(f"""<article class="book">
  {cover_html}
  <div>
    <h3>{esc(meta.get('title'))}</h3>
    <p class="role">{esc(byline)}</p>
    {markdown(body, p)}
    {btn}
  </div>
</article>""")
    return f"""
<section id="books">
  <h2>{esc(intro_meta.get('title', T('Books I recommend')))}</h2>
  {markdown(intro, folder)}
  <div class="books">{''.join(cards)}</div>
</section>"""


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
DIVIDER = '<div class="divider" aria-hidden="true">' + "<i></i>" * 7 + "</div>"

# page name -> (file, sections shown in the menu)
PAGES = {
    "home": ("index.html", []),
    "cv": ("cv.html", [("about", "About"), ("research", "Research"), ("msca", "Marie Curie"), ("experience", "Experience"),
                       ("publications", "Publications"), ("videos", "Videos"), ("talks", "Talks"), ("awards", "Awards"),
                       ("projects", "Projects")]),
    "person": ("person.html", [("purpose", "Why"), ("highlight", "Highlight"), ("education", "Education"),
                               ("books", "Books"), ("journey", "Journey"), ("conferences", "Conferences"),
                               ("music", "Music")]),
}


def build():
    global LANG, PREFIX
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ASSETS, OUT / "assets")
    (OUT / ".nojekyll").write_text("")
    for LANG, sub in LANGS.items():
        PREFIX = "../" * sub.count("/")
        MISSING.clear()
        out_dir = OUT / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        for page in PAGES:
            build_page(page, out_dir)
        if MISSING:
            print(f"  {len(MISSING)} files not yet translated to '{LANG}' (English shown instead):")
            for m in sorted(set(MISSING)):
                print(f"     - content/{m}")
        print(f"Built {out_dir.relative_to(ROOT)}/  [{LANG}]  index.html · cv.html · person.html")


def lang_switch(page):
    fname = PAGES[page][0]
    links = []
    for lang, sub in LANGS.items():
        href = PREFIX + sub + (fname if fname != "index.html" else "") or "./"
        cls = ' class="current"' if lang == LANG else ""
        links.append(f'<a href="{href}"{cls} hreflang="{lang}">{lang.upper()}</a>')
    return f'<span class="lang">{"".join(links)}</span>'


def top_nav(page, meta):
    home = f'<a class="home" href="./">{esc(meta.get("name"))}</a>'
    doors = "".join(
        f'<a class="door-link{" current" if p == page else ""}" href="{PAGES[p][0]}">{T(label)}</a>'
        for p, label in (("cv", "The CV"), ("person", "The person")))
    anchors = "".join(f'<a href="#{k}">{T(v)}</a>' for k, v in PAGES[page][1])
    sub = f'<div class="sub-nav">{anchors}</div>' if anchors else ""
    return f'<nav class="top"><div class="main-nav">{home}<span class="doors">{doors}</span>{lang_switch(page)}</div>{sub}</nav>'


def build_landing(meta, body):
    return f"""
<header class="landing">
  <div class="figures" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
  {portrait(meta)}
  <h1>{esc(meta.get("name"))}</h1>
  <p class="tagline">{esc(meta.get("tagline"))}</p>
  <p class="affiliation">{esc(meta.get("affiliation"))}</p>
  <div class="welcome">{markdown(body, section_dir("home"))}</div>
  <div class="doors-grid">
    <a class="door door-cv" href="cv.html">
      <span class="door-orn" aria-hidden="true"></span>
      <span class="door-title">{T('The CV')}</span>
      <span class="door-text">{esc(meta.get('cv_door', ''))}</span>
      <span class="door-go">{T('Enter')} →</span>
    </a>
    <a class="door door-person" href="person.html">
      <span class="door-orn" aria-hidden="true"></span>
      <span class="door-title">{T('The person')}</span>
      <span class="door-text">{esc(meta.get('person_door', ''))}</span>
      <span class="door-go">{T('Enter')} →</span>
    </a>
  </div>
  {link_pills(meta)}
</header>"""


def build_page(page, out_dir):
    meta, body = read_home()
    if page == "home":
        sections = [build_landing(meta, body)]
        title = esc(meta.get("name"))
    elif page == "cv":
        me = [x.strip() for x in meta.get("bold_author_names", "").split(";") if x.strip()]
        pubs = load_publications()
        sections = [build_cv_header(meta), build_research(pubs, me), build_msca(), build_experience(),
                    build_publications(pubs, me), build_awards(), build_projects()]
        title = f"{esc(meta.get('name'))} · {T('The CV')}"
    else:
        sections = [build_abstract(), build_highlight(), build_thinking(), build_books(), build_journey(),
                    build_conferences(), build_music()]
        title = f"{esc(meta.get('name'))} · {T('The person')}"

    today = date.today()
    updated = f"{MONTHS_ES[today.month - 1]} {today.year}" if LANG == "es" else today.strftime("%B %Y")
    nav = "" if page == "home" else top_nav(page, meta)
    lang_corner = f'<div class="lang-corner">{lang_switch(page)}</div>' if page == "home" else ""
    html_page = f"""<!doctype html>
<html lang="{LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{esc(meta.get('tagline'))}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Alegreya:ital,wght@0,400;0,500;0,700;1,400&family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;1,400&family=Alegreya+Sans+SC:wght@500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{PREFIX}assets/style.css?v={VERSION}">
</head>
<body class="page-{page}">
{build_lake()}
{nav}{lang_corner}
<main>
{DIVIDER.join(s for s in sections if s)}
</main>
<footer>© {today.year} {esc(meta.get('name'))} · {T('Last updated')} {updated}</footer>
<script src="{PREFIX}assets/script.js?v={VERSION}"></script>
</body>
</html>"""
    (out_dir / PAGES[page][0]).write_text(html_page, encoding="utf-8")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Preview: http://localhost:8000   (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
