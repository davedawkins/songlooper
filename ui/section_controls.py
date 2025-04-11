import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from audio_engine import Section
from ui.slider_time_utils import SliderTimeUtils

class SectionControlPanel(ttk.LabelFrame):
    """Panel for managing song sections."""
    
    def __init__(self, parent, app):
        super().__init__(parent, padding="0")
        self.app = app
        
        # Local StringVars for editing time fields
        self.local_stt = tk.StringVar()
        self.local_ent = tk.StringVar()
        
        # Set up the UI
        self.setup_ui()
        
        # Sync local vars initially and on app var changes (if not focused)
        self._sync_local_times_from_app()
        self.app.stt.trace_add("write", self._on_app_time_var_changed)
        self.app.ent.trace_add("write", self._on_app_time_var_changed)
    
    def setup_ui(self):
        """Set up the section control UI."""
        # Configure column weights for the frame
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=2)
        
        self.nameField = tk.StringVar()
        self.app.snm.trace_add( "write", lambda *arg: self.nameField.set( self.app.snm.get() ) )

        # Row 0: Section selection and name
        ttk.Label(self, text="Section:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.xcb = ttk.Combobox(self, state="readonly", width=20)
        self.xcb.grid(row=0, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(0, 5))
        self.xcb.bind("<<ComboboxSelected>>", self.on_section_selected)
        
        ttk.Label(self, text="Name:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5))
        self.nme = ttk.Entry(self, textvariable=self.nameField, width=20)
        self.nme.grid(row=0, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(0, 5))
        
        # Row 1: Start and end times
        ttk.Label(self, text="Start:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.ste = ttk.Entry(self, textvariable=self.local_stt, width=12) # Bind to local var
        self.ste.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=5)
        self.ste.bind("<Return>", self.on_time_field_change)
        self.ste.bind("<FocusOut>", self.on_time_field_change)
        self.ste.bind("<Escape>", self._restore_time_on_escape) # Add Escape binding
        
        ttk.Label(self, text="End:").grid(row=1, column=2, sticky=tk.W, padx=(5, 5), pady=5)
        self.ene = ttk.Entry(self, textvariable=self.local_ent, width=12) # Bind to local var
        self.ene.grid(row=1, column=3, sticky=tk.W, padx=(0, 5), pady=5)
        self.ene.bind("<Return>", self.on_time_field_change)
        self.ene.bind("<FocusOut>", self.on_time_field_change)
        self.ene.bind("<Escape>", self._restore_time_on_escape) # Add Escape binding
        
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

        self.app.snm.trace_add("write", lambda *args: self.on_section_name_write() )

    def on_section_selected(self, event):
        """When user selects a section from dropdown, update UI."""
        section_name = self.xcb.get()
        if not section_name:
            return
            
        # Update section name field
        self.app.snm.set(section_name)
        
    def on_section_name_write(self):
        section_name = self.app.snm.get()
        self.xcb.set(section_name)

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
        print("Start time (on_section_name_write):", start_time)
        self.app.stt.set(SliderTimeUtils.format_time(start_time))
        self.app.ent.set(SliderTimeUtils.format_time(end_time))
        
        # Update markers
        self.app.slider_view.update_marker_positions()

        self.save_song_config()

        # Save settings
        # self.app.settings.save_settings(self.app)

    def on_time_field_change(self, event):
        """Handle changes to time fields via UI interaction (Commit Logic)."""
        try:
            # Parse time strings from LOCAL variables
            start_time = SliderTimeUtils.parse_time(self.local_stt.get())
            end_time = SliderTimeUtils.parse_time(self.local_ent.get())
            
            if start_time is None or end_time is None:
                # If parsing failed, show error and restore local fields from app vars
                messagebox.showerror("Invalid Time", f"Invalid time format entered.\nPlease use mm:ss.xxx or seconds.")
                self._sync_local_times_from_app()
                return
            
            # Validate values
            total_duration = self.app.eng.get_total_duration()
            
            # Clamp values
            start_time = max(0, start_time)
            end_time = min(total_duration, end_time)
            
            # Ensure start is before end, maintaining a small gap if possible
            min_gap = 0.01 # Minimum time difference
            if start_time >= end_time:
                if end_time > min_gap:
                     start_time = max(0, end_time - min_gap)
                else: # If end_time is very small, set start to 0 and end to min_gap
                     start_time = 0
                     end_time = min_gap
                # Ensure end time doesn't exceed total duration after adjustment
                end_time = min(total_duration, end_time)
                start_time = min(start_time, end_time - min_gap) # Re-clamp start time

            # Validation successful, COMMIT to application variables            
            self.app.stt.set(SliderTimeUtils.format_time(start_time))
            self.app.ent.set(SliderTimeUtils.format_time(end_time))
            
            # Update markers (relies on app vars)
            self.app.slider_view.update_marker_positions()
            
            # Handle playback repositioning if needed (relies on app vars)
            self.handle_time_field_playback_logic()

            # Set focus to the slider canvas only if Return was pressed
            if hasattr(event, 'keysym') and event.keysym == 'Return':
                self.app.slider_view.canvas.focus_set()

        except ValueError as e: # Catch potential errors during validation/formatting
            messagebox.showerror("Error", f"An error occurred processing time: {e}")
            self._sync_local_times_from_app() # Restore local fields on error

    
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
        
        # Get current time field values FROM APP VARS (committed state)
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        # Create new section
        new_section = Section(
            name=new_name,
            muted=False,
            level=1.0,
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
        new_name = self.nameField.get().strip()
        
        if not new_name:
            messagebox.showerror("Error", "Section name cannot be empty")
            return
            
        # Get current start and end times FROM APP VARS (committed state)
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        if section_name == "Full Song":
            # Creating a new section
            new_section = Section(
                name=new_name,
                muted=False,
                level=1.0,
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
            "bpm": self.app.bpm.get(),
            "current_section": self.app.snm.get(),
            "sections": [
                {
                    "name": s.name,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "muted": s.muted,
                    "level": s.level
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
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        # Update slider view - directly update markers instead of slider range
        self.app.slider_view.update_marker_positions()
        
        # If playing, no need to adjust; just let the update_song_position handle it
        if not self.app.eng.is_playing():
            current_pos = self.app.pos.get()
            # Ensure position is within the visible range
            if self.app.svm.get():
                if current_pos < start_time:
                    current_pos = start_time
                elif current_pos > end_time:
                    current_pos = end_time
            self.app.pos.set(current_pos)
            # self.app.slider_view.update_time_label(current_pos, self.app.eng.get_total_duration())
    
    def handle_time_field_playback_logic(self):
        """Apply playback logic after time field changes."""
        if not self.app.eng.is_playing():
            return
            
        current_pos = self.app.eng.get_current_position()
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        # If current playback position is out of bounds, adjust
        if current_pos < start_time:
            # Restart from new start
            self.app.eng.pause()
            self.app.eng.set_position(start_time)
            self.app.play_current()
            self.app.sts.set(f"Restarted playback from new start: {SliderTimeUtils.format_time(start_time)}")
        elif current_pos > end_time:
            # Stop playback
            self.app.eng.pause()
            self.app.set_play_button_text(False)
            self.app.eng.set_position(start_time)
            self.app.sts.set(f"Playback stopped: position beyond new end time")

    # --- New Helper Methods ---

    def _sync_local_times_from_app(self):
        """Copy current app time values to local editing StringVars."""
        self.local_stt.set(self.app.stt.get())
        self.local_ent.set(self.app.ent.get())

    def _on_app_time_var_changed(self, *args):
        """Update local vars when app vars change, unless entry has focus."""
        focused_widget = self.focus_get()
        if focused_widget != self.ste and focused_widget != self.ene:
            self._sync_local_times_from_app()

    def _restore_time_on_escape(self, event):
        """Restore the entry field value from the app's StringVar on Escape."""
        self._sync_local_times_from_app()
        self.app.slider_view.canvas.focus_set()
        # Return "break" to prevent further processing and keep focus
        return "break"

    def set_start_time_to_current_pos(self, event=None):
        """Set the local start time entry to the current playback position and commit."""
        current_pos = self.app.pos.get()
        formatted_time = SliderTimeUtils.format_time(current_pos)
        self.local_stt.set(formatted_time)
        # Trigger commit logic
        self.on_time_field_change(None) 
        print(f"Set start time to current position: {formatted_time}") # Optional feedback

    def set_end_time_to_current_pos(self, event=None):
        """Set the local end time entry to the current playback position and commit."""
        current_pos = self.app.pos.get()
        formatted_time = SliderTimeUtils.format_time(current_pos)
        self.local_ent.set(formatted_time)
        # Trigger commit logic
        self.on_time_field_change(None)
        print(f"Set end time to current position: {formatted_time}") # Optional feedback

