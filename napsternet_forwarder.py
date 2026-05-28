import requests
import re
import json
import os
import time
import hashlib
import random
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HISTORY_FILE = "napsternet_history.json"
FILES_DIR = "napsternet_files"

SOURCES = [
    "https://t.me/s/vasl_bashim",
    "https://t.me/s/Configir98",
    "https://t.me/s/RedLinnez",
    "https://t.me/s/amir_webstudio",
    "https://t.me/s/nftvici",
    "https://t.me/s/JynMarket",
    "https://t.me/s/ConfigX2ray",
    "https://t.me/s/ProxyMTProtoIR",
    "https://t.me/s/xixv2ray",
    "https://t.me/s/JavidanNet",
    "https://t.me/s/ShiftVN",
    "https://t.me/s/ApolooVpn",
    "https://t.me/s/PathToArrive",
    "https://t.me/s/HTTPinjectorcustom",
    "https://t.me/s/hddify"
]


class NapsternetForwarder:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

        self.history = self.load_history()

        os.makedirs(FILES_DIR, exist_ok=True)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("History load error:", e)

        return {"sent_hashes": []}

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def is_sent(self, file_hash):
        return file_hash in self.history["sent_hashes"]

    def mark_sent(self, file_hash):
        if file_hash not in self.history["sent_hashes"]:
            self.history["sent_hashes"].append(file_hash)
            self.save_history()

    def fetch_page(self, url):
        try:
            r = self.session.get(url, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print("Fetch error:", url, e)
            return ""

    def extract_password(self, text):
        patterns = [
            r'(?:رمز|Password|پسورد|Pass|PASSWORD|password)[\s:]*([^\s\n]+)',
            r'(?:🔐|🔑)[\s:]*([^\s\n]+)',
            r'گذرواژه[\s:]*([^\s\n]+)',
            r'code[\s:]*([^\s\n]+)',
            r'key[\s:]*([^\s\n]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                password = match.group(1).strip()

                password = re.sub(r'[<>:"/\\|?*]+', '', password)

                if 3 <= len(password) <= 50:
                    return password

        return None

    def extract_links(self, html):
        soup = BeautifulSoup(html, "html.parser")

        files = []

        for a in soup.find_all("a", href=True):
            href = a["href"]

            if any(ext in href.lower() for ext in [
                ".npv",
                ".zip",
                ".rar",
                ".7z",
                ".cfg",
                ".config"
            ]):

                parent_text = a.parent.get_text() if a.parent else ""

                password = self.extract_password(parent_text)

                files.append({
                    "url": href,
                    "password": password
                })

        return files

    def sanitize_filename(self, filename):
        filename = re.sub(r'[<>:"/\\|?*]+', '_', filename)

        if len(filename) > 120:
            ext = filename.split(".")[-1]
            filename = filename[:100] + "." + ext

        return filename

    def download(self, url):
        try:
            r = self.session.get(url, timeout=40)

            r.raise_for_status()

            filename = url.split("/")[-1].split("?")[0]

            if not filename or "." not in filename:
                filename = hashlib.md5(url.encode()).hexdigest()[:10] + ".npv"

            filename = self.sanitize_filename(filename)

            content = r.content

            if not content:
                return None, None, None

            file_hash = hashlib.md5(content).hexdigest()

            return content, filename, file_hash

        except Exception as e:
            print("Download error:", e)
            return None, None, None

    def save_file(self, filename, content):
        try:
            path = os.path.join(FILES_DIR, filename)

            with open(path, "wb") as f:
                f.write(content)

        except Exception as e:
            print("Save error:", e)

    def send(self, content, filename, password):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

            files = {
                "document": (filename, content)
            }

            password_text = password if password else "بدون رمز"

            caption = f"""🔰 NapsternetV File

🔐 Password: {password_text}

📥 Download App:
https://play.google.com/store/apps/details?id=com.napsternetv.napsternetv

@aristapnel"""

            data = {
                "chat_id": CHANNEL_ID,
                "caption": caption[:1000]
            }

            r = requests.post(
                url,
                files=files,
                data=data,
                timeout=60
            )

            if r.status_code != 200:
                print("Telegram error:", r.text)

            return r.status_code == 200

        except Exception as e:
            print("Send error:", e)
            return False

    def process_channel(self, source):
        print("\nProcessing:", source)

        html = self.fetch_page(source)

        if not html:
            return 0

        links = self.extract_links(html)

        if not links:
            print("No files found")
            return 0

        count = 0

        for file in links:
            content, filename, file_hash = self.download(file["url"])

            if not content:
                continue

            if self.is_sent(file_hash):
                print("Duplicate:", filename)
                continue

            success = self.send(
                content,
                filename,
                file["password"]
            )

            if success:
                self.save_file(filename, content)

                self.mark_sent(file_hash)

                count += 1

                print("Sent:", filename)

                time.sleep(random.uniform(5, 12))

        return count

    def run(self):
        print("=" * 60)
        print("NAPSTERNETV FORWARDER")
        print(datetime.now())
        print("=" * 60)

        total = 0

        for source in SOURCES:
            try:
                total += self.process_channel(source)

                time.sleep(random.uniform(2, 6))

            except Exception as e:
                print("Channel error:", source, e)

        print("\nCompleted")
        print("Total sent:", total)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing")

    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID missing")

    forwarder = NapsternetForwarder()

    forwarder.run()
