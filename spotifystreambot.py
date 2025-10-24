import os
import random
import time
import webbrowser
import threading
from typing import List, Optional

import pytz
import requests
from colorama import Fore, Style
from pystyle import Center, Colors, Colorate

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Modul penting tidak ditemukan (selenium, webdriver-manager, dll.).")
    print("Silakan install dengan: pip install selenium webdriver-manager pytz requests colorama pystyle")
    exit()

# --- Konstanta ---
GITHUB_REPO_URL = "https://github.com/Kichi779/Spotify-Streaming-Bot/"
VERSION_FILE_URL = "https://raw.githubusercontent.com/Kichi779/Spotify-Streaming-Bot/main/version.txt"
ANNOUNCEMENT_URL = "https://raw.githubusercontent.com/Kichi779/Spotify-Streaming-Bot/main/announcement.txt"
LOCAL_VERSION_FILE = "version.txt"
ACCOUNTS_FILE = "accounts.txt"
PROXY_FILE = "proxy.txt"

SPOTIFY_LOGIN_URL = "https://accounts.spotify.com/en/login"
CONSOLE_TITLE = "Kichi779 - Spotify Streaming Bot (Ditingkatkan oleh Gemini)"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
]

SUPPORTED_LANGUAGES = [
    "en-US", "en-GB", "fr-FR", "de-DE", "es-ES", "it-IT", "ja-JP", "ko-KR", 
    "pt-BR", "ru-RU", "tr-TR", "nl-NL", "sv-SE",
]

# --- Fungsi Utilitas ---

def set_console_title(title: str) -> None:
    os.system(f"title {title}")

def check_for_updates() -> bool:
    print(Colors.yellow, "Memeriksa pembaruan...")
    try:
        r = requests.get(VERSION_FILE_URL, timeout=5)
        r.raise_for_status()
        remote_version = r.content.decode('utf-8').strip()
        
        if not os.path.exists(LOCAL_VERSION_FILE):
            print(Colors.red, "File 'version.txt' lokal tidak ditemukan. Pembuatan file baru...")
            with open(LOCAL_VERSION_FILE, 'w') as f:
                f.write(remote_version)
            return True

        with open(LOCAL_VERSION_FILE, 'r') as f:
            local_version = f.read().strip()

        if remote_version != local_version:
            print(Colors.red, Center.XCenter("Versi baru tersedia! Silakan unduh versi terbaru dari GitHub."))
            time.sleep(2)
            webbrowser.open(GITHUB_REPO_URL)
            return False
        
        print(Colors.green, "Anda menggunakan versi terbaru.")
        return True
    except requests.exceptions.RequestException as e:
        print(Colors.red, f"Gagal memeriksa pembaruan: {e}")
        return True

def print_announcement() -> None:
    try:
        r = requests.get(ANNOUNCEMENT_URL, headers={"Cache-Control": "no-cache"}, timeout=5)
        r.raise_for_status()
        announcement = r.content.decode('utf-8').strip()
        print(Colors.red, Center.XCenter("--- PENGUMUMAN ---"))
        print(Colors.yellow, Center.XCenter(f"{announcement}"))
        print(Colors.red, Center.XCenter("--------------------"))
        print("")
    except requests.exceptions.RequestException:
        print(Colors.yellow, "Tidak dapat mengambil pengumuman dari GitHub.\n")

def print_banner() -> None:
    banner = """
                       ▄█   ▄█▄  ▄█    ▄████████    ▄█    █▄     ▄█  
                       ███ ▄███▀ ███   ███    ███   ███    ███   ███  
                       ███▐██▀   ███▌  ███    █▀    ███    ███   ███▌ 
                      ▄█████▀    ███▌  ███         ▄███▄▄▄▄███▄▄ ███▌ 
                     ▀▀█████▄    ███▌  ███        ▀▀███▀▀▀▀███▀  ███▌ 
                       ███▐██▄   ███   ███    █▄    ███    ███   ███  
                       ███ ▀███▄ ███   ███    ███   ███    ███   ███  
                       ███   ▀█▀ █▀    ████████▀    ███    █▀    █▀   
                       ▀                                             
 Peningkatan kode oleh Gemini. Jika Anda mendapatkan error, kunjungi Discord asli.
                             Github  github.com/kichi779
                             Discord discord.gg/3Wp3amnNr3 """
    print(Colorate.Vertical(Colors.white_to_green, Center.XCenter(banner)))
    print("")

def load_file_lines(filename: str) -> List[str]:
    if not os.path.exists(filename):
        print(f"{Fore.RED}Error: File '{filename}' tidak ditemukan.{Style.RESET_ALL}")
        with open(filename, 'w') as f:
            pass 
        return []
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# --- Kelas Worker ---

class SpotifyWorker(threading.Thread):
    def __init__(self, account: str, song_url: str, proxy: Optional[str] = None):
        super().__init__(daemon=True)
        self.account = account
        self.song_url = song_url
        self.proxy = proxy
        self.driver: Optional[webdriver.Chrome] = None
        self.wait_long: Optional[WebDriverWait] = None
        self.wait_short: Optional[WebDriverWait] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None

        try:
            self.username, self.password = self.account.split(':')
        except ValueError:
            print(f"{Fore.RED}Format akun salah untuk: '{self.account[:10]}...'. Lewati.{Style.RESET_ALL}")

    def _set_random_timezone(self) -> None:
        if not self.driver: return
        try:
            random_timezone = random.choice(pytz.all_timezones)
            self.driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": random_timezone})
        except Exception as e:
            print(f"{Fore.YELLOW}Peringatan [{self.username}]: Gagal mengatur zona waktu. {e}{Style.RESET_ALL}")

    def _set_fake_geolocation(self) -> None:
        if not self.driver: return
        try:
            latitude = random.uniform(-90, 90)
            longitude = random.uniform(-180, 180)
            params = {"latitude": latitude, "longitude": longitude, "accuracy": 100}
            self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)
        except Exception as e:
            print(f"{Fore.YELLOW}Peringatan [{self.username}]: Gagal mengatur geolokasi. {e}{Style.RESET_ALL}")

    def _create_driver(self) -> bool:
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option('excludeSwitches', ["enable-automation", 'enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument("--window-size=1366,768")
            chrome_options.add_argument("--mute-audio")
            chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
            chrome_options.add_argument(f"--lang={random.choice(SUPPORTED_LANGUAGES)}")
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            
            chrome_options.add_experimental_option('prefs', {
                'profile.default_content_setting_values.notifications': 2,
                'credentials_enable_service': False,
                'profile.password_manager_enabled': False
            })
            
            if self.proxy:
                chrome_options.add_argument(f'--proxy-server={self.proxy}')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self._set_random_timezone()
            self._set_fake_geolocation()

            self.wait_long = WebDriverWait(self.driver, 30)
            self.wait_short = WebDriverWait(self.driver, 10)
            return True
        except Exception as e:
            print(f"{Fore.RED}Error [{self.username}] saat membuat WebDriver: {e}{Style.RESET_ALL}")
            return False

    def _handle_cookies(self) -> None:
        if not self.driver or not self.wait_short: return
        try:
            cookie_button = self.wait_short.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[text()='Accept Cookies'] | //button[text()='Setuju'] | //button[@id='onetrust-accept-btn-handler']")
            ))
            cookie_button.click()
            print(f"{Fore.CYAN}    > [{self.username}] Menangani dialog cookie.{Style.RESET_ALL}")
        except TimeoutException:
            try:
                close_button = self.driver.find_element(By.XPATH, "//button[contains(@class,'onetrust-close-btn-handler')]")
                close_button.click()
                print(f"{Fore.CYAN}    > [{self.username}] Menutup dialog cookie alternatif.{Style.RESET_ALL}")
            except NoSuchElementException:
                pass
        except Exception:
            pass

    def run(self) -> None:
        if not self.username or not self.password:
            return

        print(f"{Fore.BLUE}Memulai proses untuk: {self.username}{Style.RESET_ALL}")
        
        if not self._create_driver() or not self.driver or not self.wait_long or not self.wait_short:
            print(f"{Fore.RED}Gagal memulai browser untuk {self.username}.{Style.RESET_ALL}")
            return

        try:
            self.driver.get(SPOTIFY_LOGIN_URL)
            
            username_input = self.wait_long.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input#login-username"))
            )
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input#login-password")

            username_input.send_keys(self.username)
            password_input.send_keys(self.password)

            login_button = self.wait_short.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='login-button']"))
            )
            login_button.click()
            print(f"{Fore.CYAN}    > [{self.username}] Mencoba login...{Style.RESET_ALL}")

            self.wait_long.until(EC.not_(EC.url_contains("accounts.spotify.com")))
            print(f"{Fore.GREEN}    > [{self.username}] Login berhasil.{Style.RESET_ALL}")

            self.driver.get(self.song_url)
            print(f"{Fore.CYAN}    > [{self.username}] Menavigasi ke URL lagu...{Style.RESET_ALL}")
            
            try:
                self.wait_short.until(EC.visibility_of_element_located((By.TAG_NAME, "body")))
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except Exception:
                pass 

            self._handle_cookies()

            play_button_selector = (By.CSS_SELECTOR, "button[data-testid='play-button'][aria-label*='Play']")
            
            play_button = self.wait_long.until(
                EC.element_to_be_clickable(play_button_selector)
            )
            play_button.click()

            print(f"{Fore.GREEN}*** Sukses: {self.username} - Proses mendengarkan telah dimulai. ***{Style.RESET_ALL}")

            while True:
                time.sleep(60)

        except TimeoutException:
            print(f"{Fore.RED}Error [{self.username}]: Timeout. Mungkin halaman lambat atau login gagal.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error [{self.username}] yang tidak terduga: {e}{Style.RESET_ALL}")
        finally:
            if self.driver:
                self.driver.quit()
                print(f"{Fore.BLUE}Browser untuk {self.username} telah ditutup.{Style.RESET_ALL}")

# --- Fungsi Utama ---

def main() -> None:
    set_console_title(CONSOLE_TITLE)
    
    if not check_for_updates():
        return
    
    print_banner()
    print_announcement()

    accounts = load_file_lines(ACCOUNTS_FILE)
    if not accounts:
        print(f"{Fore.RED}Tidak ada akun ditemukan di {ACCOUNTS_FILE}. Keluar.{Style.RESET_ALL}")
        return

    proxies = load_file_lines(PROXY_FILE)
    active_proxies = []

    try:
        use_proxy = input(Colorate.Vertical(Colors.green_to_blue, "Apakah Anda ingin menggunakan proksi? (y/n): ")).lower().strip()
    except EOFError:
        return

    if use_proxy == 'y':
        if not proxies:
            print(f"{Fore.YELLOW}Peringatan: Anda memilih 'y' tetapi {PROXY_FILE} kosong atau tidak ditemukan. Melanjutkan tanpa proksi.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Berhasil memuat {len(proxies)} proksi.{Style.RESET_ALL}")
            active_proxies = proxies
    
    try:
        spotify_song = input(Colorate.Vertical(Colors.green_to_blue, "Masukkan URL lagu Spotify: "))
    except EOFError:
        return

    if "spotify.com" not in spotify_song:
        print(f"{Fore.RED}URL tidak valid. Pastikan itu adalah tautan Spotify yang benar.{Style.RESET_ALL}")
        return

    threads = []
    print(f"\n{Fore.MAGENTA}Memulai {len(accounts)} thread browser. Ini mungkin memakan waktu...{Style.RESET_ALL}")

    for account in accounts:
        proxy = random.choice(active_proxies) if active_proxies else None
        
        thread = SpotifyWorker(account, spotify_song, proxy)
        threads.append(thread)
        thread.start()
        time.sleep(random.uniform(2, 5)) 

    print(f"\n{Fore.GREEN}Semua {len(threads)} operasi stream telah dimulai di latar belakang.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Program akan tetap berjalan untuk menjaga browser tetap aktif.")
    print(f"{Fore.CYAN}Tekan Ctrl+C untuk menghentikan semua bot dan menutup program.{Style.RESET_ALL}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Perintah berhenti (Ctrl+C) diterima. Menutup semua browser...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
