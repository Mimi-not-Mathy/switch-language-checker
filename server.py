#!/usr/bin/env python3
"""
Switch Language Checker - Serveur Railway
Identifie un jeu Switch via Google Lens, scrape Nintendo JP pour les langues.
"""

import base64
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8,ja;q=0.7",
}

# ── Étape 1 : Google Lens ─────────────────────────────────────────────────────

def identify_game_google_lens(image_bytes: bytes) -> dict:
    lens_url = "https://lens.google.com/v3/upload?hl=fr&re=df&stcs=1&ep=subb"
    files = {"encoded_image": ("image.jpg", image_bytes, "image/jpeg")}
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept-Language": HEADERS["Accept-Language"],
        "Referer": "https://lens.google.com/",
    }
    resp = requests.post(lens_url, files=files, headers=headers, timeout=20, allow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    game_title = None

    page_title = soup.find("title")
    if page_title:
        t = page_title.text.strip()
        for prefix in ["Résultats pour : ", "Results for: ", "結果："]:
            if prefix in t:
                game_title = t.split(prefix)[1].split(" - Google")[0].strip()
                break

    if not game_title:
        og = soup.find("meta", property="og:title")
        if og:
            game_title = og.get("content", "").strip()

    if not game_title:
        for span in soup.find_all(["span", "h3", "div"],
                                   class_=re.compile(r"(title|result|caption)", re.I)):
            text = span.get_text(strip=True)
            if 3 < len(text) < 80 and any(
                kw in text.lower() for kw in
                ["switch", "nintendo", "zelda", "mario", "pokemon", "kirby",
                 "fire emblem", "xenoblade", "splatoon", "animal", "metroid"]
            ):
                game_title = text
                break

    if not game_title:
        game_title = google_images_fallback(image_bytes)

    return {"title": game_title, "source": "google_lens"}


def google_images_fallback(image_bytes: bytes):
    url = "https://www.google.com/searchbyimage/upload"
    files = {"encoded_image": ("image.jpg", image_bytes, "image/jpeg")}
    params = {"hl": "fr", "safe": "off"}
    headers = {"User-Agent": HEADERS["User-Agent"], "Referer": "https://www.google.com/"}
    resp = requests.post(url, files=files, params=params, headers=headers,
                         timeout=20, allow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all(["h3", "div", "span"]):
        text = tag.get_text(strip=True)
        if 5 < len(text) < 100 and any(
            kw in text.lower() for kw in
            ["switch", "nintendo", "game", "jeu", "zelda", "mario", "pokemon"]
        ):
            return text

    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.text
        for noise in [" - Recherche Google", " - Google Search", " - Google"]:
            t = t.replace(noise, "")
        return t.strip() or None
    return None


# ── Étape 2 : Nintendo JP ─────────────────────────────────────────────────────

def search_nintendo_jp(game_title: str) -> dict:
    clean_title = re.sub(r"(nintendo switch|switch|™|®)", "", game_title, flags=re.I).strip()
    encoded = urllib.parse.quote(clean_title)
    search_url = f"https://store-jp.nintendo.com/list/software/search.html?q={encoded}&lang=ja_JP"

    session = requests.Session()
    resp = session.get(search_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    game_url = None
    game_name_jp = None

    for a in soup.select("a[href*='/item/']"):
        href = a.get("href", "")
        if "/item/" in href:
            game_url = ("https://store-jp.nintendo.com" + href
                        if href.startswith("/") else href)
            name_el = a.select_one("p, span, div")
            if name_el:
                game_name_jp = name_el.get_text(strip=True)
            break

    if not game_url:
        game_url = f"https://store-jp.nintendo.com/search/#q={encoded}&t=software"

    result = {
        "search_url": search_url,
        "game_url": game_url,
        "game_name_jp": game_name_jp,
        "languages": {},
    }

    if game_url and "/item/" in game_url:
        lang_info = scrape_game_page(session, game_url)
        result["languages"]    = lang_info.get("languages", {})
        result["game_name_jp"] = lang_info.get("name_jp", game_name_jp)
        result["image_url"]    = lang_info.get("image_url")
        result["price"]        = lang_info.get("price")

    return result


def scrape_game_page(session: requests.Session, url: str) -> dict:
    resp = session.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")
    result = {}

    title_el = soup.select_one("h1, .product-title, [class*='title']")
    if title_el:
        result["name_jp"] = title_el.get_text(strip=True)

    price_el = soup.select_one("[class*='price'], .price")
    if price_el:
        result["price"] = price_el.get_text(strip=True)

    img_el = soup.select_one("img[class*='package'], img[class*='product'], img[class*='hero']")
    if img_el:
        result["image_url"] = img_el.get("src", "")

    page_text = soup.get_text()
    raw_langs_text = ""

    for pattern in [
        r"対応言語[^\n]*[\n:：]?\s*([^\n]+)",
        r"languages?[^\n]*[\n:：]?\s*([^\n]+)",
        r"言語[^\n]*[\n:：]?\s*([^\n]+)",
    ]:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            raw_langs_text = match.group(1)
            break

    for el in soup.find_all(string=re.compile(r"対応言語|Languages?|言語", re.I)):
        parent = el.parent
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                raw_langs_text = sibling.get_text(strip=True)
                break

    lang_map = {
        "english":    ["english", "英語"],
        "french":     ["french", "français", "フランス語"],
        "japanese":   ["japanese", "日本語"],
        "german":     ["german", "deutsch", "ドイツ語"],
        "spanish":    ["spanish", "español", "スペイン語"],
        "italian":    ["italian", "italiano", "イタリア語"],
        "korean":     ["korean", "한국어", "韓国語"],
        "chinese_s":  ["chinese (simplified)", "简体中文", "中国語(簡体字)"],
        "chinese_t":  ["chinese (traditional)", "繁體中文", "中国語(繁体字)"],
        "portuguese": ["portuguese", "português", "ポルトガル語"],
        "russian":    ["russian", "русский", "ロシア語"],
        "dutch":      ["dutch", "nederlands", "オランダ語"],
    }

    text_lower = (raw_langs_text + " " + page_text[:5000]).lower()
    languages_found = {
        k: any(kw in text_lower for kw in kws)
        for k, kws in lang_map.items()
    }

    if not any(languages_found.values()):
        languages_found = {k: None for k in languages_found}

    result["languages"] = languages_found
    return result


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "Pas d'image fournie"}), 400

        img_b64 = data["image"]
        if "," in img_b64:
            img_b64 = img_b64.split(",")[1]
        image_bytes = base64.b64decode(img_b64)

        lens_result = identify_game_google_lens(image_bytes)
        game_title  = lens_result.get("title")

        if not game_title:
            return jsonify({
                "error": "Impossible d'identifier le jeu. Essaie avec une photo plus nette."
            }), 422

        nintendo_result = search_nintendo_jp(game_title)

        return jsonify({
            "identified_title": game_title,
            "nintendo": nintendo_result,
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout — connexion trop lente"}), 504
    except Exception as e:
        return jsonify({"error": f"Erreur serveur : {str(e)}"}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=False)
