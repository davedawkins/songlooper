import os
import tkinter as tk
from tkinter import ttk, messagebox
from audio_engine import AudioEngine

from ui.song_selection import SongSelectionPanel
from ui.section_controls import SectionControlPanel
from ui.playback_controls import PlaybackControlPanel
from ui.slider_view import SliderView
from ui.stems_panel import StemsPanel
from utils.settings import SettingsManager

class GuitarPracticeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Guitar Practice Tool")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # --- Engine & State ---
        self.eng = AudioEngine()
        self.dir = ""
        
        # --- Persistent Vars ---
        self.fdr = tk.StringVar()  # Folder
        self.spd = tk.DoubleVar(value=1.0)  # Speed
        self.dly = tk.DoubleVar(value=0.5)  # Delay
        self.lop = tk.BooleanVar(value=True)  # Loop
        self.cin = tk.BooleanVar(value=False)  # Count-in
        self.snm = tk.StringVar()  # Section name
        self.svm = tk.BooleanVar(value=False)  # Section view mode
        self.stt = tk.DoubleVar(value=0.0)  # Start time
        self.ent = tk.DoubleVar(value=0.0)  # End time
        
        # Status variable
        self.sts = tk.StringVar(value="Ready")
        
        # Settings manager
        self.settings = SettingsManager()
        
        # Build the UI
        self.setup_ui()
        
        # Bind resize events to main window
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Load settings and start position updates
        self.load_settings()
        
    def setup_ui(self):
        """Build the main UI frame and all components."""
        # Main frame
        self.frm = ttk.Frame(self.root, padding="10")
        self.frm.pack(fill=tk.BOTH, expand=True)
        
        # Top folder selection
        self.setup_folder_selection()
        
        # Create panels
        self.song_panel = SongSelectionPanel(self.frm, self)
        self.song_panel.pack(fill=tk.X, pady=(0, 10))
        
        self.section_panel = SectionControlPanel(self.frm, self)
        self.section_panel.pack(fill=tk.X, pady=(0, 10))
        
        self.playback_panel = PlaybackControlPanel(self.frm, self)
        self.playback_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Slider with markers
        self.slider_view = SliderView(self.frm, self)
        self.slider_view.pack(fill=tk.X, pady=(0, 10))
        
        # Transport buttons
        self.setup_transport()
        
        # Stems
        self.stems_panel = StemsPanel(self.frm, self)
        self.stems_panel.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        ttk.Label(self.frm, textvariable=self.sts, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_folder_selection(self):
        """Setup the folder selection UI."""
        top = ttk.Frame(self.frm)
        top.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top, text="Songs Folder:").pack(side=tk.LEFT, padx=(0, 5))
        folder_entry = ttk.Entry(top, textvariable=self.fdr, width=50)
        folder_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(top, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)
    
    def setup_transport(self):
        """Setup transport control buttons."""
        tpf = ttk.Frame(self.frm)
        tpf.pack(fill=tk.X, pady=(0, 10))

        # Rewind button
        ttk.Button(tpf, text="⏮", command=self.rewind_section_start).pack(side=tk.LEFT, padx=5)
        
        # Play/Pause toggle button
        self.ppb = ttk.Button(tpf, text="▶", command=self.play_pause_toggle)
        self.ppb.pack(side=tk.LEFT, padx=5)
    
    def browse_folder(self):
        """Open folder dialog and load songs."""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Songs Folder")
        if folder:
            self.dir = folder
            self.fdr.set(folder)
            self.song_panel.refresh_song_list()
            self.settings.save_settings(self)
    
    def load_settings(self):
        """Load settings and start position updates."""
        self.settings.load_settings(self)
        self.update_song_position()
    
    def on_window_resize(self, event):
        """Handle window resize events."""
        if event.widget == self.root and hasattr(self, 'slider_view'):
            self.slider_view.update_marker_positions()
    
    def update_song_position(self):
        """Poll engine position and update UI."""
        if self.eng.is_playing():
            pos = self.eng.get_current_position()
            total_duration = self.eng.get_total_duration()
            
            # Update position variable using data binding
            self.slider_view.pos.set(pos)
            
            # Check if we've hit the end marker for the section
            end_time = self.ent.get()
            if pos >= end_time:
                if self.lop.get():
                    # Loop back to start of section
                    self.eng.stop()
                    self.eng.set_start_position(self.stt.get())
                    self.play_current()
                    self.sts.set(f"Looped back to section start")
                else:
                    # Stop playback at end marker
                    self.eng.stop()
                    self.set_play_button_text(False)
                    self.sts.set(f"Reached end of section")
        
        # Schedule next update
        self.root.after(50, self.update_song_position)
    
    def play_pause_toggle(self):
        """Toggle between play and pause."""
        if self.eng.is_playing():
            self.pause_playback()
        else:
            self.play_current()
    
    def play_current(self):
        """Play the current section from the engine's position."""
        if not self.eng.current_song:
            messagebox.showerror("Error", "No song loaded")
            return
        
        section_name = self.section_panel.xcb.get()
        if section_name == "Full Song":
            section_name = None
        
        try:
            current_pos = self.eng.get_current_position()
            start_time = self.stt.get()
            
            # Only check lower boundary - we allow playing beyond the end marker
            if current_pos < start_time:
                self.eng.set_start_position(start_time)
                old_pos = start_time
            else:
                old_pos = current_pos
            
            self.eng.play_section(
                section_name=None,  # Always use full song for actual playback range
                loop=self.lop.get(),
                speed=self.spd.get(),
                loop_delay=self.dly.get()
            )
            
            # Update button
            self.set_play_button_text(True)
            
            # Status message
            if abs(old_pos - start_time) < 0.01:
                disp_sec = section_name or "Full Song"
                self.sts.set(f"Playing: {disp_sec} at {self.spd.get()}x speed")
            else:
                self.sts.set(f"Resumed from {old_pos:.1f}s at {self.spd.get()}x speed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play: {str(e)}")
    
    def pause_playback(self):
        """Pause the current playback."""
        if self.eng.is_playing():
            self.eng.pause()
            self.sts.set("Paused")
        self.set_play_button_text(False)
    
    def set_play_button_text(self, playing):
        """Update play/pause button text."""
        if playing:
            self.ppb.config(text="⏹")
        else:
            self.ppb.config(text="▶")
    
    def rewind_section_start(self):
        """Go to start of current section."""
        if not self.eng.current_song:
            return
        
        # Get start time for the current section
        new_start = self.stt.get()
        was_playing = self.eng.is_playing()
        
        # Stop playback
        self.eng.stop()
        
        # Update engine position
        self.eng.set_start_position(new_start)
        
        # Update slider position variable
        # This triggers the trace callback which updates the UI
        self.slider_view.pos.set(new_start)
        
        # Force an update of the marker positions
        self.slider_view.update_marker_positions()
        
        # Resume playback if it was playing
        if was_playing:
            self.play_current()
            self.sts.set(f"Rewound and playing from {new_start:.1f}s")
        else:
            self.sts.set(f"Rewound to {new_start:.1f}s (paused)")
    
    def on_closing(self):
        """Handle window close."""
        if self.eng.is_playing():
            self.eng.stop()
        self.settings.save_settings(self)
        self.root.destroy()