import requests
import re
import json
import os
import time
import hashlib
import random
import sys
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HISTORY_FILE = "napsternet_history.json"
FILES_DIR = "napsternet_files"

# منابع معتبرتر
SOURCES = [
    "https://t.me/s/FreeConfige",
    "https://t.me/s/ServerNett",
    "https://t.me/s/ProxyV2ray",
    "https://t.me/s/NapsternetVConfig",
    "https://t.me/s/ConfigV2rayN"
]


class NapsternetForwarder:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.session.timeout = 30
        self.history = self.load_history()
        os.makedirs(FILES_DIR, exist_ok=True)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "sent_hashes" not in data:
                        data["sent_hashes"] = []
                    return data
            except Exception as e:
                print(f"History load error: {e}")
        return {"sent_hashes": []}

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Save history error: {e}")

    def is_sent(self, file_hash):
        return file_hash in self.history.get("sent_hashes", [])

    def mark_sent(self, file_hash):
        if "sent_hashes" not in self.history:
            self.history["sent_hashes"] = []
        if file_hash not in self.history["sent_hashes"]:
            self.history["sent_hashes"].append(file_hash)
            self.save_history()

    def fetch_page(self, url):
        try:
            print(f"Fetching: {url}")
            r = self.session.get(url, timeout=25)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"Fetch error {url}: {e}")
            return ""

    def extract_password(self, text):
        patterns = [
            r'(?:رمز|Password|پسورد|Pass|PASSWORD|password)[\s:]*([^\s\n]{4,})',
            r'(?:🔐|🔑|key|code)[\s:]*([^\s\n]{4,})',
            r'گذرواژه[\s:]*([^\s\n]{4,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                password = match.group(1).strip()
                password = re.sub(r'[<>:"/\\|?*]', '', password)
                if 3 <= len(password) <= 50:
                    return password
        return None

    def extract_links(self, html):
        soup = BeautifulSoup(html, "html.parser")
        files = []
        
        # جستجوی لینک‌های فایل
        for a in soup.find_all("a", href=True):
            href = a["href"]
            href_lower = href.lower()
            
            if any(ext in href_lower for ext in [".npv", ".zip", ".rar", ".7z", ".cfg", ".config"]):
                parent_text = a.parent.get_text() if a.parent else ""
                text = parent_text + " " + a.get_text()
                password = self.extract_password(text)
                
                files.append({
                    "url": href,
                    "password": password
                })
        
        # جستجوی متن‌های معمولی
        for text_node in soup.find_all(text=True):
            text = text_node.strip()
            if text and any(ext in text.lower() for ext in [".npv", ".zip"]):
                password = self.extract_password(text)
                if password:
                    print(f"Found potential file reference: {text[:100]}")
        
        return files

    def download(self, url):
        try:
            print(f"Downloading: {url[:100]}")
            r = self.session.get(url, timeout=40)
            r.raise_for_status()
            
            content = r.content
            if not content:
                return None, None, None
            
            filename = url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = hashlib.md5(url.encode()).hexdigest()[:10] + ".npv"
            
            # پاکسازی نام فایل
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            if len(filename) > 100:
                name, ext = os.path.splitext(filename)
                filename = name[:90] + ext
            
            file_hash = hashlib.md5(content).hexdigest()
            return content, filename, file_hash
            
        except Exception as e:
            print(f"Download error: {e}")
            return None, None, None

    def send(self, content, filename, password):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            
            password_text = password if password else "بدون رمز"
            caption = f"""🔰 NapsternetV Config File

📁 {filename}
🔐 Password: {password_text}

📥 Download App:
https://play.google.com/store/apps/details?id=com.napsternetv.napsternetv

@aristapnel"""
            
            files = {"document": (filename, content)}
            data = {"chat_id": CHANNEL_ID, "caption": caption[:1000]}
            
            r = requests.post(url, files=files, data=data, timeout=60)
            
            if r.status_code == 200:
                print(f"✅ Sent: {filename}")
                return True
            else:
                print(f"❌ Telegram error: {r.text[:200]}")
                return False
                
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def process_channel(self, source):
        print(f"\n📡 Processing: {source}")
        html = self.fetch_page(source)
        if not html:
            return 0
        
        links = self.extract_links(html)
        if not links:
            print("No direct links found")
            return 0
        
        count = 0
        for file in links:
            content, filename, file_hash = self.download(file["url"])
            if not content:
                continue
            
            if self.is_sent(file_hash):
                print(f"⏭️ Duplicate: {filename}")
                continue
            
            if self.send(content, filename, file["password"]):
                self.save_file(filename, content)
                self.mark_sent(file_hash)
                count += 1
                time.sleep(random.uniform(3, 8))
        
        return count

    def save_file(self, filename, content):
        try:
            path = os.path.join(FILES_DIR, filename)
            with open(path, "wb") as f:
                f.write(content)
            print(f"💾 Saved: {filename}")
        except Exception as e:
            print(f"Save error: {e}")

    def run(self):
        print("=" * 60)
        print("NAPSTERNETV FORWARDER")
        print(f"Started at: {datetime.now()}")
        print(f"Python version: {sys.version}")
        print("=" * 60)
        
        total = 0
        for source in SOURCES:
            try:
                total += self.process_channel(source)
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                print(f"Channel error {source}: {e}")
        
        print(f"\n✅ Completed! Total sent: {total}")
        print(f"Finished at: {datetime.now()}")


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not set!")
        sys.exit(1)
    
    if not CHANNEL_ID:
        print("❌ ERROR: CHANNEL_ID not set!")
        sys.exit(1)
    
    forwarder = NapsternetForwarder()
    forwarder.run()
