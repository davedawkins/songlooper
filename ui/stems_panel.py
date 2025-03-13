import tkinter as tk
from tkinter import ttk

class StemsPanel(ttk.LabelFrame):
    """Panel for controlling the visibility of individual audio stems."""
    
    def __init__(self, parent, app):
        super().__init__(parent, text="Stems", padding="10")
        self.app = app
        
        # Stem state variables dictionary
        self.stv = {}
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the stems panel UI."""
        self.stc = ttk.Frame(self)
        self.stc.pack(fill=tk.BOTH, expand=True)
    
    def update_stems_panel(self):
        """Update the stems panel with current stem names."""
        # Clear existing controls
        for widget in self.stc.winfo_children():
            widget.destroy()
        
        # Get stems and create checkboxes
        stem_names = self.app.eng.get_stem_names()
        self.stv = {}
        
        for i, stem in enumerate(stem_names):
            var = tk.BooleanVar(value=True)
            self.stv[stem] = var
            
            def on_check(s=stem):
                self.toggle_stem(s)
                self.app.settings.save_settings(self.app)
            
            ttk.Checkbutton(
                self.stc, 
                text=stem, 
                variable=var, 
                command=on_check
            ).grid(row=i//3, column=i%3, sticky=tk.W, padx=10, pady=2)
    
    def toggle_stem(self, stem_name):
        """Toggle a stem's muted state."""
        new_mute = self.app.eng.toggle_mute_stem(stem_name)
        song_title = self.app.eng.current_song.title if self.app.eng.current_song else ""
        
        # Update muted stems in settings
        if song_title not in self.app.settings.mut:
            self.app.settings.mut[song_title] = []
        
        if new_mute:
            if stem_name not in self.app.settings.mut[song_title]:
                self.app.settings.mut[song_title].append(stem_name)
        else:
            if stem_name in self.app.settings.mut[song_title]:
                self.app.settings.mut[song_title].remove(stem_name)
        
        self.stv[stem_name].set(not new_mute)
