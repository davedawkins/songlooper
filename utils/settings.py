import os
import json

class SettingsManager:
    """Manages loading and saving application settings."""
    
    SETTINGS_FILE = "settings.json"
    
    def __init__(self):
        # Settings data
        self.mut = {}  # Muted stems info
        self.pss = None  # Pending section selection
    
    def load_settings(self, app):
        """Load settings from file and apply to app."""
        if not os.path.exists(self.SETTINGS_FILE):
            return
            
        try:
            with open(self.SETTINGS_FILE, "r") as f:
                data = json.load(f)
        except Exception as e:
            print("Could not load settings.json:", e)
            return
        
        # Apply settings to app
        app.dir = data.get("songs_folder", "")
        app.fdr.set(app.dir)
        
        current_song = data.get("current_song", "")
        if app.dir and os.path.isdir(app.dir):
            app.song_panel.refresh_song_list()
            if current_song in app.song_panel.scb["values"]:
                app.song_panel.scb.set(current_song)
                app.sts.set(f"Selected: {current_song}")
        
        if app.song_panel.scb.get():
            app.song_panel.load_selected_song()
        
        app.spd.set(data.get("speed", 1.0))
        app.dly.set(data.get("loop_delay", 0.5))
        app.lop.set(data.get("loop_playback", True))
        app.cin.set(data.get("count_in", False))
        
        self.mut = data.get("muted_stems_info", {})
        self.pss = data.get("current_section", None)
    
    def save_settings(self, app):
        """Save app settings to file."""
        data = {
            "songs_folder": app.dir,
            "current_song": app.song_panel.scb.get() if hasattr(app, 'song_panel') else "",
            "current_section": app.section_panel.xcb.get() if hasattr(app, 'section_panel') else "",
            "speed": app.spd.get(),
            "loop_delay": app.dly.get(),
            "loop_playback": app.lop.get(),
            "count_in": app.cin.get(),
            "muted_stems_info": self.mut
        }
        
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Could not save settings:", e)
