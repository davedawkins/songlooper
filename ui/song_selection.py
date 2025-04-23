import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

class SongSelectionPanel(ttk.LabelFrame):
    """Panel for selecting and loading songs."""
    
    def __init__(self, parent, app):
        super().__init__(parent, padding="10")
        self.app = app
        
        # Setup internal layout
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the song selection UI."""
        ttk.Label(self, text="Available Songs:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.scb = ttk.Combobox(self, state="readonly", width=40)
        self.scb.grid(row=0, column=1, sticky=tk.W+tk.E, padx=(0, 5))
        self.scb.bind("<<ComboboxSelected>>", self.on_song_selected)
        
        # ttk.Button(self, text="Load Song", command=self.load_selected_song).grid(row=0, column=2, padx=5)
        ttk.Button(self, text="Refresh List", command=self.refresh_song_list).grid(row=0, column=3)
        
        # Configure grid column weights for resizing
        self.columnconfigure(1, weight=1)
    
    def on_song_selected(self, event):
        """Handle song selection from dropdown."""
        self.app.sts.set(f"Selected: {self.scb.get()}")
        self.app.settings.save_settings(self.app)
        self.app.root.after(0, self.load_selected_song)
        # self.load_selected_song()

    def refresh_song_list(self):
        """Refresh the list of available songs."""
        if not self.app.dir or not os.path.isdir(self.app.dir):
            messagebox.showerror("Error", "Please select a valid songs folder")
            return
        
        try:
            # First get available songs
            song_list = self.app.eng.get_available_songs(self.app.dir)
            
            # Check for songs without config files and create default configs
            for song_folder in os.listdir(self.app.dir):
                full_path = os.path.join(self.app.dir, song_folder)
                if not os.path.isdir(full_path):
                    continue
                    
                config_path = os.path.join(full_path, "config.json")
                if not os.path.exists(config_path):
                    # Create default config for this song
                    self.create_default_config(full_path)
                    # If this wasn't in the list, add it
                    if song_folder not in song_list:
                        song_list.append(song_folder)
            
            # Sort alphabetically
            song_list.sort()
            
            self.scb["values"] = song_list
            if song_list:
                self.scb.current(0)
                self.app.sts.set(f"Found {len(song_list)} songs")
            else:
                self.app.sts.set("No songs found in the selected folder")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load songs: {str(e)}")
    
    def create_default_config(self, song_folder):
        """Create a default config.json for a song folder."""
        try:
            # Use folder name as title
            title = os.path.basename(song_folder)
            
            # Create default config
            config = {
                "title": title,
                "bpm": 120.0,  # Default BPM
                "sections": []  # No sections initially
            }
            
            # Write config to file
            config_path = os.path.join(song_folder, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            print(f"Created default config for {title}")
        except Exception as e:
            print(f"Error creating default config: {str(e)}")

    # In SongSelectionPanel class, modify the load_selected_song method
    def load_selected_song(self):
        """Load the currently selected song."""

        song_name = self.scb.get()

        if not song_name:
            messagebox.showerror("Error", "Please select a song")
            return
        
        song_folder = os.path.join(self.app.dir,song_name)
        try:
            # Force stop any current playback
            self.app.eng.pause()
            self.app.set_play_button_text(False)
            
            # Reset speed to 1.0
            self.app.spd.set(1.0)
            
            song_config = self.app.eng.load_song(song_folder)
            self.app.sts.set(f"Loaded: {song_config.title}")
            
            # BPM (pass to playback panel)
            # self.app.playback_panel.update_bpm(str(int(song_config.bpm)))
            self.app.bpm.set(str(int(song_config.bpm)))
            
            # Sections
            self.app.section_panel.update_section_combobox()
            
            # Initialize section boundaries
            if self.app.section_panel.xcb.get() == "Full Song":
                start_time = 0.0
                end_time = self.app.eng.get_total_duration()
            else:
                for s in song_config.sections:
                    if s.name == self.app.section_panel.xcb.get():
                        start_time = s.start_time
                        end_time = s.end_time
                        break
                else:  # Default if section not found
                    start_time = 0.0
                    end_time = self.app.eng.get_total_duration()
            
            # Set section name and times
            self.app.snm.set(song_config.current_section)
            print("Start time (load selected song):", start_time)
            self.app.stt.set(round(start_time, 4))
            self.app.ent.set(round(end_time, 4))
            
            # Update UI components
            # self.app.stems_panel.update_stems_panel()
            self.app.section_panel.update_section_combobox()
            self.app.slider_view.waveform.invalidate_cache() # Invalidate cache on song load
            
            # Reset view range to full song duration on manual load
            total_duration = self.app.eng.get_total_duration()
            self.app.vst.set(0.0)
            self.app.vet.set(total_duration if total_duration > 0 else 1.0)
            print(f"[Load Song] Resetting view range: vst=0.0, vet={self.app.vet.get()}") # DIAGNOSTIC
            
            self.app.slider_view.update_marker_positions() # Redraw slider with new view range
            
            # Apply muted stems from settings
            if song_config.title in self.app.settings.mut:
                for stem_name in self.app.settings.mut[song_config.title]:
                    self.app.eng.toggle_mute_stem(stem_name)
                    # if stem_name in self.app.stems_panel.stv:
                    #     self.app.stems_panel.stv[stem_name].set(False)
            
            # Reset to 0
            # self.app.eng.set_start_position(0.0)
            
            self.app.settings.save_settings(self.app)
            self.app.songName.set( song_name )
            # Update time label explicitly after loading song and setting other UI elements
            if hasattr(self.app, 'time_label'):
                self.app.time_label.update()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load song: {str(e)}")