"""
Matriks Web Trader Scraper
- Playwright ile app.matrikswebtrader.com'dan veri çeker
- Login + BIST tablo verisi okuma
- Streamlit uygulamasına JSON olarak veri aktarma
"""

import json
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CANLI_VERI_PATH = DATA_DIR / "canli_veri.json"
CEREZ_PATH = DATA_DIR / "matriks_auth.json"


async def matriks_login(page, kullanici, sifre):
    """Matriks Web Trader'a giriş yapar."""
    await page.goto("https://app.matrikswebtrader.com", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Login formunu bul ve doldur
    # Matriks Web Trader farklı login formları kullanabilir
    login_selectors = [
        # Olası kullanıcı adı alanları
        'input[name="username"]', 'input[name="user"]', 'input[name="email"]',
        'input[type="text"]:first-of-type', 'input[placeholder*="Kullanıcı"]',
        'input[placeholder*="kullanıcı"]', 'input[placeholder*="User"]',
    ]
    sifre_selectors = [
        'input[name="password"]', 'input[type="password"]',
        'input[placeholder*="Şifre"]', 'input[placeholder*="şifre"]',
        'input[placeholder*="Password"]',
    ]
    giris_selectors = [
        'button[type="submit"]', 'button:has-text("Giriş")',
        'button:has-text("Login")', 'button:has-text("Oturum")',
        'input[type="submit"]', '.login-button', '#loginButton',
    ]

    # Kullanıcı adı
    for sel in login_selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.fill(kullanici)
                break
        except Exception:
            continue

    # Şifre
    for sel in sifre_selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.fill(sifre)
                break
        except Exception:
            continue

    # Giriş butonu
    for sel in giris_selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                break
        except Exception:
            continue

    # Giriş sonrası bekleme
    await page.wait_for_timeout(5000)


async def sayfa_kesfet(page):
    """Sayfadaki tablo ve veri elementlerini keşfeder."""
    bilgi = {}

    # Sayfa başlığı
    bilgi["title"] = await page.title()
    bilgi["url"] = page.url

    # Tüm tabloları bul
    tablolar = await page.query_selector_all("table")
    bilgi["tablo_sayisi"] = len(tablolar)

    # Grid/ag-grid elementleri (modern finans uygulamaları genelde ag-grid kullanır)
    ag_grids = await page.query_selector_all(".ag-root, .ag-body, [class*='ag-grid']")
    bilgi["ag_grid_sayisi"] = len(ag_grids)

    # Tüm metin içerikli elementler
    text_content = await page.evaluate("""
        () => {
            const elements = document.querySelectorAll('table, .ag-root, [class*="grid"], [class*="table"], [class*="stock"], [class*="hisse"]');
            return Array.from(elements).map(el => ({
                tag: el.tagName,
                className: el.className.substring(0, 100),
                childCount: el.children.length,
                text: el.innerText.substring(0, 500)
            }));
        }
    """)
    bilgi["veri_elementleri"] = text_content[:10]

    # iframe kontrolü
    iframes = await page.query_selector_all("iframe")
    bilgi["iframe_sayisi"] = len(iframes)

    return bilgi


async def tablo_oku(page):
    """Sayfadaki borsa tablosundan verileri çeker."""
    veriler = []

    # Yöntem 1: Standart HTML tabloları
    tablo_veri = await page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            const results = [];

            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                const tableData = [];

                for (const row of rows) {
                    const cells = row.querySelectorAll('td, th');
                    const rowData = Array.from(cells).map(cell => cell.innerText.trim());
                    if (rowData.length > 0) {
                        tableData.push(rowData);
                    }
                }

                if (tableData.length > 2) {
                    results.push(tableData);
                }
            }
            return results;
        }
    """)

    if tablo_veri:
        for tablo in tablo_veri:
            parsed = _tablo_parse(tablo)
            if parsed:
                veriler.extend(parsed)

    # Yöntem 2: ag-grid (eğer kullanılıyorsa)
    if not veriler:
        ag_veri = await page.evaluate("""
            () => {
                // ag-grid API'sine erişmeyi dene
                const gridElements = document.querySelectorAll('[class*="ag-"]');
                const results = [];

                // ag-grid row'larını oku
                const rows = document.querySelectorAll('.ag-row');
                for (const row of rows) {
                    const cells = row.querySelectorAll('.ag-cell');
                    const rowData = Array.from(cells).map(cell => cell.innerText.trim());
                    if (rowData.length > 0) {
                        results.push(rowData);
                    }
                }

                return results;
            }
        """)

        if ag_veri:
            parsed = _tablo_parse(ag_veri)
            if parsed:
                veriler.extend(parsed)

    # Yöntem 3: Genel div-tabanlı grid
    if not veriler:
        div_veri = await page.evaluate("""
            () => {
                const results = [];
                // Hisse kodu içeren elementleri ara
                const allText = document.body.innerText;
                const lines = allText.split('\\n');

                for (const line of lines) {
                    // BIST hisse kodu pattern: 3-5 büyük harf + sayılar
                    const match = line.match(/([A-Z]{3,5})\\s+([\\d.,]+)/);
                    if (match) {
                        results.push(line.trim());
                    }
                }
                return results;
            }
        """)

        if div_veri:
            for satir in div_veri:
                parsed = _satir_parse(satir)
                if parsed:
                    veriler.append(parsed)

    return veriler


def _tablo_parse(rows):
    """Tablo satırlarını hisse verilerine parse eder."""
    import re
    veriler = []

    # Bilinen BIST kodları
    from veri_isleyici import TICKER_ISIMLERI
    bilinen = set(TICKER_ISIMLERI.keys())

    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue

        # Satırda hisse kodu ara
        for i, cell in enumerate(row):
            cell_str = str(cell).strip().upper()
            kod_match = re.findall(r'\b([A-Z]{3,5})\b', cell_str)

            for kod in kod_match:
                if kod in bilinen:
                    # Kalan hücrelerden sayıları çıkar
                    sayilar = []
                    for j, c in enumerate(row):
                        if j == i:
                            continue
                        try:
                            deger = float(str(c).replace(",", ".").replace(" ", "").replace("%", ""))
                            sayilar.append(deger)
                        except (ValueError, TypeError):
                            continue

                    if sayilar:
                        veri = {"kod": kod, "fiyat": sayilar[0]}
                        if len(sayilar) > 1:
                            veri["degisim"] = sayilar[1]
                        if len(sayilar) > 2:
                            veri["hacim"] = sayilar[2]
                        veriler.append(veri)
                    break

    return veriler


def _satir_parse(satir):
    """Tek metin satırından hisse verisi çıkarır."""
    import re
    from veri_isleyici import TICKER_ISIMLERI

    bilinen = set(TICKER_ISIMLERI.keys())

    kod_match = re.findall(r'\b([A-Z]{3,5})\b', satir)
    sayilar = re.findall(r'[\d]+[.,]?\d*', satir)

    for kod in kod_match:
        if kod in bilinen and sayilar:
            try:
                fiyat = float(sayilar[0].replace(",", "."))
                veri = {"kod": kod, "fiyat": fiyat}
                if len(sayilar) > 1:
                    veri["degisim"] = float(sayilar[1].replace(",", "."))
                if len(sayilar) > 2:
                    veri["hacim"] = float(sayilar[2].replace(",", "."))
                return veri
            except ValueError:
                continue

    return None


async def matriks_veri_cek(kullanici=None, sifre=None, headless=True):
    """Ana fonksiyon: Matriks Web Trader'dan veri çeker.

    Args:
        kullanici: Matriks kullanıcı adı
        sifre: Matriks şifresi
        headless: True=görünmez browser, False=görünür browser (debug için)

    Returns:
        dict: {"veriler": [...], "zaman": "...", "kaynak": "matriks_web_trader"}
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Tarayıcıyı başlat
        browser = await p.chromium.launch(headless=headless)

        # Kayıtlı oturum varsa kullan
        context_args = {"viewport": {"width": 1920, "height": 1080}}
        if CEREZ_PATH.exists():
            context_args["storage_state"] = str(CEREZ_PATH)

        context = await browser.new_context(**context_args)
        page = await context.new_page()

        try:
            # Siteye git
            await page.goto("https://app.matrikswebtrader.com", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Login gerekiyorsa
            if kullanici and sifre:
                await matriks_login(page, kullanici, sifre)
                # Oturumu kaydet
                await context.storage_state(path=str(CEREZ_PATH))

            # Sayfa keşfi
            bilgi = await sayfa_kesfet(page)

            # Veri çek
            veriler = await tablo_oku(page)

            # Screenshot al (debug için)
            screenshot_path = DATA_DIR / "matriks_son_ekran.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            sonuc = {
                "veriler": veriler,
                "zaman": datetime.now().isoformat(),
                "kaynak": "matriks_web_trader",
                "sayfa_bilgi": bilgi,
                "screenshot": str(screenshot_path),
            }

            # JSON olarak kaydet
            with open(CANLI_VERI_PATH, "w", encoding="utf-8") as f:
                json.dump(sonuc, f, ensure_ascii=False, indent=2)

            return sonuc

        except Exception as e:
            # Hata durumunda da screenshot al
            try:
                hata_path = DATA_DIR / "matriks_hata_ekran.png"
                await page.screenshot(path=str(hata_path))
            except Exception:
                pass
            return {"hata": str(e), "zaman": datetime.now().isoformat()}

        finally:
            await browser.close()


def matriks_veri_cek_sync(kullanici=None, sifre=None, headless=True):
    """Senkron wrapper — Streamlit'ten çağırmak için."""
    return asyncio.run(matriks_veri_cek(kullanici, sifre, headless))


def kayitli_veri_oku():
    """Son kaydedilen Matriks verisini okur."""
    if CANLI_VERI_PATH.exists():
        with open(CANLI_VERI_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def veri_to_dataframe(veriler):
    """Scraper çıktısını DataFrame'e çevirir."""
    if not veriler:
        return None
    return pd.DataFrame(veriler)


# CLI test
if __name__ == "__main__":
    import sys

    print("Matriks Web Trader Scraper")
    print("=" * 40)

    if len(sys.argv) >= 3:
        kullanici = sys.argv[1]
        sifre = sys.argv[2]
        headless = "--visible" not in sys.argv
    else:
        kullanici = input("Kullanıcı adı: ")
        sifre = input("Şifre: ")
        headless = True

    print(f"\nVeri çekiliyor (headless={headless})...")
    sonuc = matriks_veri_cek_sync(kullanici, sifre, headless)

    if "hata" in sonuc:
        print(f"HATA: {sonuc['hata']}")
    else:
        print(f"Sayfa: {sonuc['sayfa_bilgi'].get('title', '?')}")
        print(f"Bulunan veri sayısı: {len(sonuc['veriler'])}")
        if sonuc["veriler"]:
            df = veri_to_dataframe(sonuc["veriler"])
            print(df.to_string(index=False))
        print(f"\nScreenshot: {sonuc['screenshot']}")
        print(f"JSON: {CANLI_VERI_PATH}")
