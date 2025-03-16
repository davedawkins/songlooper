import tkinter as tk
from tkinter import ttk

class StemsPanel(ttk.LabelFrame):
    """Panel for controlling the visibility of individual audio stems."""
    
    def __init__(self, parent, app):
        super().__init__(parent, text="Stems", padding="12")
        self.app = app
        
        # Stem state variables dictionary
        self.stv = {}
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the stems panel UI."""
        # Create a frame with scrollbar for the stems
        self.outer_frame = ttk.Frame(self)
        self.outer_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Add scrollbar
        self.scrollbar = ttk.Scrollbar(self.outer_frame, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for scrolling
        self.canvas = tk.Canvas(self.outer_frame, yscrollcommand=self.scrollbar.set, borderwidth=0, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar.config(command=self.canvas.yview)
        
        # Create frame for stem controls inside the canvas
        self.stc = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.stc, anchor='nw')
        
        # Configure canvas to resize with frame
        self.stc.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
    
    def on_frame_configure(self, event):
        """Update the canvas scrollregion when the inner frame changes size."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """Update the inner frame width when the canvas changes size."""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def update_stems_panel(self):
        """Update the stems panel with current stem names."""
        # Clear existing controls
        for widget in self.stc.winfo_children():
            widget.destroy()
        
        # Get stems and create checkboxes
        stem_names = self.app.eng.get_stem_names()
        self.stv = {}
        
        # Configure the grid for the stems frame
        self.stc.columnconfigure(0, weight=1)
        
        # Add a header
        header_frame = ttk.Frame(self.stc)
        header_frame.grid(row=0, column=0, sticky=tk.EW, padx=8, pady=(5,10))
        
        ttk.Label(header_frame, text="Stem", font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Mute", font=("", 10, "bold")).pack(side=tk.RIGHT, padx=5)
        
        ttk.Separator(self.stc, orient="horizontal").grid(row=1, column=0, sticky=tk.EW, padx=5)
        
        for i, stem in enumerate(stem_names):
            var = tk.BooleanVar(value=True)
            self.stv[stem] = var
            
            # Check if stem is already muted
            if hasattr(self.app, 'eng') and self.app.eng.current_song:
                song_title = self.app.eng.current_song.title
                if song_title in self.app.settings.mut and stem in self.app.settings.mut[song_title]:
                    var.set(False)
            
            # Function to handle checkbox state change
            def on_check(s=stem):
                self.toggle_stem(s)
            
            # Create a frame for each stem row with proper padding
            stem_frame = ttk.Frame(self.stc, padding=(10, 8))
            stem_frame.grid(row=i+2, column=0, sticky=tk.EW)
            
            # Stem name label (using original stem name)
            ttk.Label(stem_frame, text=stem).pack(side=tk.LEFT, padx=5)
            
            # Add checkbox on the right
            cb = ttk.Checkbutton(
                stem_frame, 
                variable=var,
                command=on_check
            )
            cb.pack(side=tk.RIGHT, padx=5)
            
            # Add a thin separator between stems (except after the last one)
            if i < len(stem_names) - 1:
                sep = ttk.Separator(self.stc, orient="horizontal")
                sep.grid(row=i+3, column=0, sticky=tk.EW, padx=12)
    
    def toggle_stem(self, stem_name):
        """Toggle a stem's muted state."""
        if not self.app.eng.current_song:
            return
            
        # Get the current state
        current_state = self.stv[stem_name].get()
        
        # Toggle mute state
        new_mute = self.app.eng.toggle_mute_stem(stem_name)
        song_title = self.app.eng.current_song.title if self.app.eng.current_song else ""
        
        # Update muted stems in settings
        if song_title not in self.app.settings.mut:
            self.app.settings.mut[song_title] = []
        
        if new_mute:
            if stem_name not in self.app.settings.mut[song_title]:
                self.app.settings.mut[song_title].append(stem_name)
            self.app.sts.set(f"Muted: {stem_name}")
        else:
            if stem_name in self.app.settings.mut[song_title]:
                self.app.settings.mut[song_title].remove(stem_name)
            self.app.sts.set(f"Unmuted: {stem_name}")
        
        # Update UI to reflect new state (opposite of muted state)
        self.stv[stem_name].set(not new_mute)
        
        # Save settings immediately
        self.app.settings.save_settings(self.app)
        
        # Update the waveform to reflect mute changes
        if hasattr(self.app, 'slider_view'):
            self.app.slider_view.update_marker_positions()
    