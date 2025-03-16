import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from audio_engine import Section

class SectionControlPanel(ttk.LabelFrame):
    """Panel for managing song sections."""
    
    def __init__(self, parent, app):
        super().__init__(parent, text="Section & Playback", padding="10")
        self.app = app
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the section control UI."""
        # Configure column weights for the frame
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=2)
        
        # Row 0: Section selection and name
        ttk.Label(self, text="Section:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.xcb = ttk.Combobox(self, state="readonly", width=20)
        self.xcb.grid(row=0, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(0, 5))
        self.xcb.bind("<<ComboboxSelected>>", self.on_section_selected)
        
        ttk.Label(self, text="Name:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5))
        self.nme = ttk.Entry(self, textvariable=self.app.snm, width=20)
        self.nme.grid(row=0, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(0, 5))
        
        # Row 1: Start and end times
        ttk.Label(self, text="Start:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.ste = ttk.Entry(self, textvariable=self.app.stt, width=12)
        self.ste.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=5)
        self.ste.bind("<Return>", self.on_time_field_change)
        self.ste.bind("<FocusOut>", self.on_time_field_change)
        
        ttk.Label(self, text="End:").grid(row=1, column=2, sticky=tk.W, padx=(5, 5), pady=5)
        self.ene = ttk.Entry(self, textvariable=self.app.ent, width=12)
        self.ene.grid(row=1, column=3, sticky=tk.W, padx=(0, 5), pady=5)
        self.ene.bind("<Return>", self.on_time_field_change)
        self.ene.bind("<FocusOut>", self.on_time_field_change)
        
        # Row 2: Section management buttons
        self.mbf = ttk.Frame(self)
        self.mbf.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=5)
        
        ttk.Button(self.mbf, text="New Section", command=self.new_section).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.mbf, text="Save Section", command=self.save_section).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.mbf, text="Delete Section", command=self.delete_section).pack(side=tk.LEFT, padx=5)
        
        # View mode toggle
        self.vmt = ttk.Checkbutton(self.mbf, text="Section View", variable=self.app.svm,
                                  command=self.toggle_view_mode)
        self.vmt.pack(side=tk.LEFT, padx=20)

    def on_section_selected(self, event):
        """When user selects a section from dropdown, update UI."""
        section_name = self.xcb.get()
        if not section_name:
            return
            
        # Update section name field
        self.app.snm.set(section_name)
        
        # Get section start/end times
        if section_name == "Full Song":
            start_time = 0.0
            end_time = self.app.eng.get_total_duration()
        else:
            for s in self.app.eng.current_song.sections:
                if s.name == section_name:
                    start_time = s.start_time
                    end_time = s.end_time
                    break
            else:
                # Default if section not found
                start_time = 0.0
                end_time = self.app.eng.get_total_duration()
        
        # Update time fields with formatted times
        self.app.stt.set(self.format_time(start_time))
        self.app.ent.set(self.format_time(end_time))
        
        # Update markers
        self.app.slider_view.update_marker_positions()
        
        # Save settings
        self.app.settings.save_settings(self.app)

    # Modify on_time_field_change method
    def on_time_field_change(self, event):
        """Handle changes to time fields via UI interaction."""
        try:
            # Parse time strings
            start_time_str = self.app.stt.get()
            end_time_str = self.app.ent.get()
            
            start_time = self.parse_time(start_time_str)
            end_time = self.parse_time(end_time_str)
            
            if start_time is None or end_time is None:
                # If parsing failed, restore to previous valid values and return
                self.app.stt.set(self.format_time(float(self.app.stt.get())))
                self.app.ent.set(self.format_time(float(self.app.ent.get())))
                return
            
            # Validate values
            total_duration = self.app.eng.get_total_duration()
            
            if start_time < 0:
                start_time = 0
            
            if end_time > total_duration:
                end_time = total_duration
            
            if start_time >= end_time:
                # Keep at least 1 second gap
                if end_time <= 1.0:
                    start_time = 0
                else:
                    start_time = end_time - 1.0
            
            # Update the values with formatted times
            self.app.stt.set(self.format_time(start_time))
            self.app.ent.set(self.format_time(end_time))
            
            # Update markers
            self.app.slider_view.update_marker_positions()
            
            # Handle playback repositioning if needed
            self.handle_time_field_playback_logic()
        except ValueError:
            # Restore to previous valid values
            self.app.stt.set(self.format_time(float(self.app.stt.get())))
            self.app.ent.set(self.format_time(float(self.app.ent.get())))

    
    def new_section(self):
        """Create a new section based on current one."""
        if not self.app.eng.current_song:
            messagebox.showerror("Error", "No song loaded")
            return
            
        # Generate a unique name
        base_name = "New Section"
        names = [s.name for s in self.app.eng.current_song.sections]
        new_name = base_name
        i = 1
        while new_name in names:
            new_name = f"{base_name} {i}"
            i += 1
        
        # Get current time field values
        start_time = self.parse_time(self.app.stt.get())
        end_time = self.parse_time(self.app.ent.get())
        
        # Create new section
        new_section = Section(
            name=new_name,
            start_time=start_time,
            end_time=end_time
        )
        
        # Add to the song
        self.app.eng.current_song.sections.append(new_section)
        
        # Update dropdown and select the new section
        self.update_section_combobox()
        self.xcb.set(new_name)
        self.app.snm.set(new_name)
        
        # Save config to disk
        self.save_song_config()
        
        self.app.sts.set(f"Created new section: {new_name}")
    
    def save_section(self):
        """Save current section with new name and boundaries."""
        if not self.app.eng.current_song:
            messagebox.showerror("Error", "No song loaded")
            return
            
        section_name = self.xcb.get()
        new_name = self.app.snm.get().strip()
        
        if not new_name:
            messagebox.showerror("Error", "Section name cannot be empty")
            return
            
        # Get current start and end times
        start_time = self.parse_time(self.app.stt.get())
        end_time = self.parse_time(self.app.ent.get())
        
        if section_name == "Full Song":
            # Creating a new section
            new_section = Section(
                name=new_name,
                start_time=start_time,
                end_time=end_time
            )
            self.app.eng.current_song.sections.append(new_section)
        else:
            # Updating existing
            for s in self.app.eng.current_song.sections:
                if s.name == section_name:
                    s.name = new_name
                    s.start_time = start_time
                    s.end_time = end_time
                    break
        
        # Update dropdown
        self.update_section_combobox()
        self.xcb.set(new_name)
        
        # Save config to disk
        self.save_song_config()
        
        self.app.sts.set(f"Saved section: {new_name}")
    
    def delete_section(self):
        """Delete the current section."""
        if not self.app.eng.current_song:
            messagebox.showerror("Error", "No song loaded")
            return
            
        section_name = self.xcb.get()
        if section_name == "Full Song":
            messagebox.showerror("Error", "Cannot delete Full Song")
            return
            
        # Find and remove the section
        for i, s in enumerate(self.app.eng.current_song.sections):
            if s.name == section_name:
                del self.app.eng.current_song.sections[i]
                break
        
        # Update dropdown and select Full Song
        self.update_section_combobox()
        self.xcb.set("Full Song")
        self.app.snm.set("Full Song")
        
        # Save config to disk
        self.save_song_config()
        
        self.app.sts.set(f"Deleted section: {section_name}")
    
    def save_song_config(self):
        """Save song config to disk."""
        if not self.app.eng.current_song:
            return
            
        config_path = os.path.join(self.app.eng.current_song.path, "config.json")
        
        # Create config dict
        config = {
            "title": self.app.eng.current_song.title,
            "bpm": int(self.app.bpm.get()),
            "sections": [
                {
                    "name": s.name,
                    "start_time": s.start_time,
                    "end_time": s.end_time
                }
                for s in self.app.eng.current_song.sections
            ]
        }
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
    
    def update_section_combobox(self):
        """Update section dropdown with current sections."""
        if not self.app.eng.current_song:
            self.xcb["values"] = []
            return
            
        sections = ["Full Song"] + [s.name for s in self.app.eng.current_song.sections]
        self.xcb["values"] = sections
        
        # Select first item if nothing is selected
        if not self.xcb.get() and sections:
            self.xcb.current(0)
            self.app.snm.set(sections[0])
    
    def toggle_view_mode(self):
        """Toggle between whole song view and section view."""
        start_time = self.parse_time(self.app.stt.get())
        end_time = self.parse_time(self.app.ent.get())
        
        # Update slider view - directly update markers instead of slider range
        self.app.slider_view.update_marker_positions()
        
        # If playing, no need to adjust; just let the update_song_position handle it
        if not self.app.eng.is_playing():
            current_pos = self.app.slider_view.pos.get()
            # Ensure position is within the visible range
            if self.app.svm.get():
                if current_pos < start_time:
                    current_pos = start_time
                elif current_pos > end_time:
                    current_pos = end_time
            self.app.slider_view.pos.set(current_pos)
            self.app.slider_view.update_time_label(current_pos, self.app.eng.get_total_duration())
    
    def handle_time_field_playback_logic(self):
        """Apply playback logic after time field changes."""
        if not self.app.eng.is_playing():
            return
            
        current_pos = self.app.eng.get_current_position()
        start_time = self.parse_time(self.app.stt.get())
        end_time = self.parse_time(self.app.ent.get())
        
        # If current playback position is out of bounds, adjust
        if current_pos < start_time:
            # Restart from new start
            self.app.eng.stop()
            self.app.eng.set_start_position(start_time)
            self.app.play_current()
            self.app.sts.set(f"Restarted playback from new start: {self.format_time(start_time)}")
        elif current_pos > end_time:
            # Stop playback
            self.app.eng.stop()
            self.app.set_play_button_text(False)
            self.app.eng.set_start_position(start_time)
            self.app.sts.set(f"Playback stopped: position beyond new end time")

    def format_time(self, seconds):
        """Format time in mm:ss.c format."""
        minutes, sec_frac = divmod(seconds, 60)
        sec = int(sec_frac)
        decisec = int((sec_frac - sec) * 10)  # Use deciseconds (1/10th second)
        return f"{int(minutes):02d}:{sec:02d}.{decisec}"

    def parse_time(self, time_str):
        """Parse time from either mm:ss.c format or float seconds."""
        if ":" in time_str:
            try:
                # Parse from mm:ss.c format
                parts = time_str.split(":")
                minutes = int(parts[0])
                if "." in parts[1]:
                    sec_parts = parts[1].split(".")
                    seconds = int(sec_parts[0])
                    if len(sec_parts[1]) > 0:
                        # Only use the first digit for deciseconds
                        decisec = int(sec_parts[1][0])
                        return minutes * 60 + seconds + decisec / 10
                    else:
                        return minutes * 60 + seconds
                else:
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            except (ValueError, IndexError):
                # Fall back to current value if parsing fails
                return None
        else:
            try:
                # Parse as raw seconds
                return float(time_str)
            except ValueError:
                return None