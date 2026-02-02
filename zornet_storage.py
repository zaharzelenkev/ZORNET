# zornet_storage.py
import json
from pathlib import Path

class ZornetStorage:
    def __init__(self):
        self.storage_file = Path("zornet_data.json")
        self.data = self._load_data()
    
    def _load_data(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"users": {}}
        return {"users": {}}
    
    def _save_data(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def save_user_links(self, username, links):
        if "users" not in self.data:
            self.data["users"] = {}
        
        if username not in self.data["users"]:
            self.data["users"][username] = {}
        
        self.data["users"][username]["quick_links"] = links
        self._save_data()
    
    def get_user_links(self, username):
        return self.data.get("users", {}).get(username, {}).get("quick_links")
    
    def get_or_create_default_links(self, username):
        links = self.get_user_links(username)
        if not links:
            default_links = [
                {"name": "Google", "url": "https://www.google.com", "icon": "🔍"},
                {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
                {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
                {"name": "ChatGPT", "url": "https://chat.openai.com", "icon": "🤖"},
            ]
            self.save_user_links(username, default_links)
            return default_links
        return links
