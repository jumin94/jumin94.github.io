# Julia Mindlin — personal website

Everything on the site comes from the **`content/`** folder. You edit text files and drop in photos. You never need to touch HTML.

The opening page has two doors, **The CV** (`cv.html`) and **The person** (`person.html`).

```
content/
├── lake/                         background photos for the "dive": 1_surface.jpg … 4_deep.jpg
├── home/                         opening page: about.md (name, tagline, links, door texts, welcome) + photo.jpg
├── the_cv/
│   ├── _bio.md                   academic bio at the top of the CV
│   ├── 1_experience_and_education.md   list of positions & degrees
│   ├── 2_publications/           one .md file per paper (copy _TEMPLATE.md)
│   ├── 3_talks_and_conferences.md      list of talks / sessions / committees
│   ├── 4_research_summary/       one .md per research theme (+ _intro.md)
│   ├── 5_awards_and_funding.md   list of awards, fellowships, grants
│   └── 6_projects_and_activities/  one folder per project (teaching, mentoring, service…)
└── the_person/
    ├── _abstract.md              why this part of the site exists
    ├── 1_highlight_of_the_month/ one folder per month: 2026-11/, 2026-12/ … (newest shown)
    ├── 2_education/              reflective chapter in threads: _intro.md + 1_geophysics.md, 2_whitehead.md …
    ├── 3_books/                  one folder per book: index.md + cover.jpg (or just an isbn: line)
    ├── 4_academic_journey/       one folder per place: index.md + photos
    ├── 5_conference_gallery/     one folder per conference: index.md (reflection) + photos
    └── 6_music/                  one folder per album / instrument / group (YouTube, Spotify links → player)
```

The `.md` lists (experience, talks, awards) hold one entry per block, separated by `---`. Add `role_es:`, `place_es:` or `title_es:` lines for the Spanish site.

Each folder has a `README.txt` with the details. Text marked **✏️** is a placeholder for you to write or check. To find all of them, search the folder for `✏️`.

## File format

Each `.md` file has a small header between `---` lines, then normal text:

```markdown
---
title: Climate Informatics 2026
date: April 2026
place: Lausanne, Switzerland
---
This is the reflection. **Bold**, *italic*, [a link](https://example.org),

- bullet points
- work too
```

**Photos:** use `.jpg`/`.png` and put them in the item's folder. They're resized automatically. The caption comes from the file name: `02_poster-session-with-julius.jpg` becomes "Poster session with julius". Convert iPhone `.HEIC` photos to JPG first. For Spanish captions, add a `captions.es.txt` file next to the photos with one line per photo, e.g. `07_lake-shore.jpg: La orilla del lago`.

## Spanish version (castellano)

The site is built twice: English at `/` and Spanish at `/es/`, with an EN/ES switch in the menu.

- Next to each content file there is a Spanish twin: `about.md` → `about.es.md`, `index.md` → `index.es.md`, `_intro.md` → `_intro.es.md`, and so on.
- The twin only needs what changes (title, role, years, text). Links, photos and everything else are taken from the English file.
- Papers: titles stay in the original language. Add a `resumen:` line for the Spanish summary.
- Talks: roles and countries are translated automatically (see `UI` and `PLACES_ES` in `build.py`).
- If a twin is missing, the Spanish site shows the English text, and `python3 build.py` lists the files still to translate. You can ask Claude to "translate the missing files" in this folder.

## Preview on your computer

```bash
cd ~/Dropbox/my_website
python3 build.py --serve
```
Then open http://localhost:8000. Press Ctrl+C to stop.

## Publish on GitHub Pages (one-time setup)

1. On github.com, create a **public** repository named **`jumin94.github.io`**. The site will then be at `https://jumin94.github.io`, and your Climate Toolkit stays at `https://jumin94.github.io/climate_toolkit/`.
2. In this folder:
   ```bash
   git init -b main
   git add .
   git commit -m "First version of website"
   git remote add origin https://github.com/jumin94/jumin94.github.io.git
   git push -u origin main
   ```
3. In the repository, go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.

## Updating the site

```bash
git add . && git commit -m "November highlight" && git push
```
The site rebuilds itself in about a minute (follow it in the **Actions** tab). You can also edit or upload files directly on github.com: use the pencil icon, or **Add file → Upload files**, and the site rebuilds the same way.

## The lake background

The photos in `content/lake/` sit behind every page. As a visitor scrolls down, the photos fade from the first file to the last, so name them from surface to deep (`1_…`, `2_…`). The water also darkens and zooms in slowly, and a small gauge on the right counts metres. You can add, remove or swap photos and keep any number of them.

They're published at 2000 px, and the phone's location (GPS) data is removed. Calm, textured photos work best: the text sits on sand-coloured paper, so busy photos won't hurt readability. The 14 m maximum depth is set in `assets/script.js` (`MAX_DEPTH`).

## Changing the look

Colours and fonts are at the top of `assets/style.css`. The page layout is in `build.py`.
