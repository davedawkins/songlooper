import os
import json
from ui.slider_time_utils import SliderTimeUtils

class SettingsManager:
    """Manages loading and saving application settings."""
    
    SETTINGS_FILE = "settings.json"
    
    def __init__(self):
        # Settings data
        self.mut = {}  # Muted stems info
        # self.pss = None  # Pending section selection
        self.midi_settings = {
            "enabled": False,
            "device": "",
            "play_pause_note": 60,
            "rewind_note": 62,
            "next_section_note": 64,
            "prev_section_note": 65
        }
    
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
        
        self.current_song = data.get("current_song", "")
        app.spd.set(data.get("speed", 1.0))
        app.dly.set(data.get("loop_delay", 0.5))
        app.lop.set(data.get("loop_playback", True))
        app.cin.set(data.get("count_in", False))
        
        self.mut = data.get("muted_stems_info", {})

        # self.pss = data.get("current_section", None)
        
        # Load MIDI settings if available
        self.midi_settings = data.get("midi_settings", {})

        # self.section_name = data.get("current_section", "Full Song")

        # Load view times, default to 0.0 and 1.0 if not found
        app.vst.set(data.get("view_start_time", 0.0))
        app.vet.set(data.get("view_end_time", 1.0))

    def save_settings(self, app):
        """Save app settings to file."""
        # For section times, save the actual numeric values
        start_time = 0.0
        end_time = 0.0
        if hasattr(app, 'section_panel'):
            try:
                start_time = SliderTimeUtils.parse_time(app.stt.get())
                end_time = SliderTimeUtils.parse_time(app.ent.get())
            except (ValueError, AttributeError):
                pass
        
        data = {
            "songs_folder": app.dir,
            "current_song": app.song_panel.scb.get() if hasattr(app, 'song_panel') else "",
            "current_section": app.section_panel.xcb.get() if hasattr(app, 'section_panel') else "",
            "speed": app.spd.get(),
            "loop_delay": app.dly.get(),
            "loop_playback": app.lop.get(),
            "count_in": app.cin.get(),
            "muted_stems_info": self.mut,
            "midi_settings": self.midi_settings,
            "view_start_time": app.vst.get(), # Save view start time
            "view_end_time": app.vet.get()    # Save view end time
        }
        
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Could not save settings:", e)
    
    def save_midi_settings(self):
        """Update MIDI settings from the MIDI panel."""
        if not hasattr(self.app, 'midi_panel'):
            return
            
        # Check if MIDI is enabled
        midi_enabled = (hasattr(self.app, 'midi_controller') and 
                       self.app.midi_controller.midi_thread and 
                       self.app.midi_controller.midi_thread.is_alive())
        
        # Get device
        midi_device = self.app.midi_panel.midi_device.get()
        
        # Get note mappings
        try:
            play_pause_note = int(self.app.midi_panel.play_pause_note.get())
            rewind_note = int(self.app.midi_panel.rewind_note.get())
            next_section_note = int(self.app.midi_panel.next_section_note.get())
            prev_section_note = int(self.app.midi_panel.prev_section_note.get())
        except ValueError:
            # Use defaults if parsing fails
            play_pause_note = 60
            rewind_note = 62
            next_section_note = 64
            prev_section_note = 65
        
        # Update settings
        self.midi_settings = {
            "enabled": midi_enabled,
            "device": midi_device,
            "play_pause_note": play_pause_note,
            "rewind_note": rewind_note,
            "next_section_note": next_section_note,
            "prev_section_note": prev_section_note
        }
        
        # Save to file
        self.save_settings(self.app)