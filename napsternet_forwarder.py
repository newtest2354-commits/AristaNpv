import requests
import re
import json
import os
import time
import hashlib
import random

from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

HISTORY_FILE = "napsternet_history.json"
FILES_DIR = "napsternet_files"
LOG_FILE = "run_log.txt"


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
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        })

        self.history = self.load_history()

        os.makedirs(FILES_DIR, exist_ok=True)

    def log(self, text):

        print(text)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def load_history(self):

        if os.path.exists(HISTORY_FILE):

            try:

                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)

            except Exception as e:

                self.log(f"History load error: {e}")

        return {
            "sent_hashes": [],
            "sent_urls": []
        }

    def save_history(self):

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                self.history,
                f,
                indent=2,
                ensure_ascii=False
            )

    def is_sent(self, file_hash, url):

        return (
            file_hash in self.history["sent_hashes"]
            or
            url in self.history["sent_urls"]
        )

    def mark_sent(self, file_hash, url):

        if file_hash not in self.history["sent_hashes"]:

            self.history["sent_hashes"].append(file_hash)

        if url not in self.history["sent_urls"]:

            self.history["sent_urls"].append(url)

        self.save_history()

    def fetch_page(self, url):

        try:

            r = self.session.get(url, timeout=30)

            r.raise_for_status()

            return r.text

        except Exception as e:

            self.log(f"Fetch error: {url} | {e}")

            return ""

    def extract_password(self, text):

        patterns = [

            r'(?:رمز|پسورد|گذرواژه)[\s:：\-]*([^\s\n]+)',

            r'(?:password|pass|pwd|key|code)[\s:：\-]*([^\s\n]+)',

            r'(?:🔐|🔑)[\s:：\-]*([^\s\n]+)',

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                password = match.group(1).strip()

                password = re.sub(
                    r'[<>:"/\\|?*]+',
                    '',
                    password
                )

                if 2 <= len(password) <= 50:
                    return password

        return None

    def extract_links(self, html):

        soup = BeautifulSoup(html, "html.parser")

        posts = []

        messages = soup.find_all(
            "div",
            class_="tgme_widget_message_wrap"
        )

        for msg in messages:

            try:

                text = msg.get_text(
                    " ",
                    strip=True
                )

                password = self.extract_password(text)

                post_link = None

                date_link = msg.find(
                    "a",
                    class_="tgme_widget_message_date"
                )

                if date_link:
                    post_link = date_link.get("href")

                if not post_link:
                    continue

                posts.append({
                    "post_url": post_link,
                    "password": password
                })

            except Exception as e:

                self.log(f"Extract error: {e}")

        self.log(f"Extracted posts: {len(posts)}")

        return posts

    def sanitize_filename(self, filename):

        filename = re.sub(
            r'[<>:"/\\|?*]+',
            '_',
            filename
        )

        filename = filename.strip()

        if len(filename) > 120:

            ext = filename.split(".")[-1]

            filename = filename[:100] + "." + ext

        return filename

    def resolve_download_link(self, post_url):

        try:

            r = self.session.get(
                post_url,
                timeout=30
            )

            r.raise_for_status()

            soup = BeautifulSoup(
                r.text,
                "html.parser"
            )

            download_btn = soup.find(
                "a",
                class_="tgme_widget_message_download_button"
            )

            if download_btn:

                href = download_btn.get("href")

                if href:

                    self.log(f"Resolved: {href}")

                    return href

            document_wrap = soup.find(
                "a",
                class_="tgme_widget_message_document_wrap"
            )

            if document_wrap:

                href = document_wrap.get("href")

                if href:

                    self.log(f"Resolved: {href}")

                    return href

            self.log(f"No download button: {post_url}")

            return None

        except Exception as e:

            self.log(f"Resolve error: {post_url} | {e}")

            return None

    def download(self, url):

        try:

            r = self.session.get(
                url,
                timeout=120,
                stream=True,
                allow_redirects=True
            )

            r.raise_for_status()

            filename = None

            cd = r.headers.get(
                "content-disposition",
                ""
            )

            if "filename=" in cd:

                filename = cd.split(
                    "filename="
                )[-1]

                filename = filename.strip('"').strip("'")

            if not filename:

                filename = url.split("/")[-1]

            if not filename or "." not in filename:

                filename = (
                    hashlib.md5(url.encode()).hexdigest()[:10]
                    + ".npv"
                )

            filename = self.sanitize_filename(filename)

            content = r.content

            if not content:

                return None, None, None

            file_hash = hashlib.md5(
                content
            ).hexdigest()

            return content, filename, file_hash

        except Exception as e:

            self.log(f"Download error: {url} | {e}")

            return None, None, None

    def save_file(self, filename, content):

        try:

            path = os.path.join(
                FILES_DIR,
                filename
            )

            with open(path, "wb") as f:
                f.write(content)

        except Exception as e:

            self.log(f"Save error: {e}")

    def send(self, content, filename, password):

        try:

            telegram_url = (
                f"https://api.telegram.org/bot"
                f"{BOT_TOKEN}/sendDocument"
            )

            password_text = (
                password
                if password
                else "No Password"
            )

            caption = f"""🚀 Napsternet Config

🔐 Password: {password_text}

📲 NapsternetV:
https://play.google.com/store/apps/details?id=com.napsternetv.napsternetv

📡 Channel:
@aristapnel
"""

            files = {
                "document": (
                    filename,
                    content
                )
            }

            data = {
                "chat_id": CHANNEL_ID,
                "caption": caption[:1024]
            }

            r = requests.post(
                telegram_url,
                files=files,
                data=data,
                timeout=180
            )

            self.log(f"Telegram status: {r.status_code}")

            if r.status_code != 200:

                self.log(r.text)

                return False

            return True

        except Exception as e:

            self.log(f"Send error: {e}")

            return False

    def process_channel(self, source):

        self.log("=" * 60)
        self.log(f"Processing: {source}")
        self.log("=" * 60)

        html = self.fetch_page(source)

        if not html:
            return 0

        posts = self.extract_links(html)

        if not posts:

            self.log("No posts found")

            return 0

        count = 0

        for post in posts:

            try:

                post_url = post["post_url"]

                file_url = self.resolve_download_link(
                    post_url
                )

                if not file_url:
                    continue

                content, filename, file_hash = self.download(
                    file_url
                )

                if not content:
                    continue

                if self.is_sent(
                    file_hash,
                    file_url
                ):

                    self.log(f"Duplicate: {filename}")

                    continue

                success = self.send(
                    content,
                    filename,
                    post["password"]
                )

                if success:

                    self.save_file(
                        filename,
                        content
                    )

                    self.mark_sent(
                        file_hash,
                        file_url
                    )

                    count += 1

                    self.log(f"Sent: {filename}")

                    time.sleep(
                        random.uniform(10, 20)
                    )

            except Exception as e:

                self.log(f"Process file error: {e}")

        self.log(f"Completed channel: {source}")
        self.log(f"Sent count: {count}")

        return count

    def run(self):

        self.log("=" * 60)
        self.log("NAPSTERNET FORWARDER")
        self.log(str(datetime.now()))
        self.log("=" * 60)

        total = 0

        for source in SOURCES:

            try:

                total += self.process_channel(source)

                time.sleep(
                    random.uniform(3, 8)
                )

            except Exception as e:

                self.log(f"Channel error: {source} | {e}")

        self.log("=" * 60)
        self.log(f"TOTAL SENT: {total}")
        self.log("=" * 60)


if __name__ == "__main__":

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing")

    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID missing")

    print("BOT_TOKEN loaded")
    print("CHANNEL_ID:", CHANNEL_ID)

    forwarder = NapsternetForwarder()

    forwarder.run()
