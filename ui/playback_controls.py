import tkinter as tk
from tkinter import ttk

class PlaybackControlPanel(ttk.Frame):
    """Panel for controlling playback speed, looping, and other playback options."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the playback controls UI."""
        # # BPM variable
        # self.bpm = tk.StringVar(value="120")
        
        # Playback controls in a frame
        self.pbf = ttk.Frame(self)
        self.pbf.pack(fill=tk.X, expand=True, pady=5)
        
        ttk.Label(self.pbf, text="Speed:").pack(side=tk.LEFT, padx=(0, 5))
        speeds = [0.25, 0.5, 0.75, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0]
        self.scx = ttk.Combobox(self.pbf, values=speeds, textvariable=self.app.spd, width=6)
        self.scx.pack(side=tk.LEFT, padx=(0, 15))
        self.scx.bind("<<ComboboxSelected>>", lambda e: self.app.settings.save_settings(self.app))
        
        ttk.Label(self.pbf, text="Loop Delay (s):").pack(side=tk.LEFT, padx=(0, 5))
        delays = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        self.dcb = ttk.Combobox(self.pbf, values=delays, textvariable=self.app.dly, width=6)
        self.dcb.pack(side=tk.LEFT, padx=(0, 15))
        self.dcb.bind("<<ComboboxSelected>>", lambda e: self.app.settings.save_settings(self.app))
        
        lop = ttk.Checkbutton(self.pbf, text="Loop Playback", variable=self.app.lop,
                              command=lambda: self.app.settings.save_settings(self.app))
        lop.pack(side=tk.LEFT, padx=(0, 15))
        
        cin = ttk.Checkbutton(self.pbf, text="Count-in", variable=self.app.cin,
                              command=self.toggle_count_in)
        cin.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(self.pbf, text="BPM:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(self.pbf, textvariable=self.app.bpm, width=5).pack(side=tk.LEFT)

    def toggle_count_in(self):
        """Toggle count-in feature."""
        self.app.eng.set_count_in(self.app.cin.get())
        self.app.settings.save_settings(self.app)
    
    # def update_bpm(self, bpm_value):
    #     """Update the BPM display."""
    #     self.bpm.set(bpm_value)
