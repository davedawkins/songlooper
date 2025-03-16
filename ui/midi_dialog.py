import tkinter as tk
from tkinter import ttk, messagebox
from utils.midi_controller import MidiController

class MidiSettingsDialog:
    """Standalone dialog for MIDI settings."""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create a new Toplevel window
        self.dialog = tk.Toplevel(parent)
        # self.dialog.title("MIDI Controller Settings")
        self.dialog.geometry("450x400")
        self.dialog.minsize(400, 350)
        self.dialog.transient(parent)  # Set to be on top of the parent window
        self.dialog.grab_set()  # Make window modal
        
        # Center on parent
        self.center_on_parent()
        
        # MIDI state variables (sync with app if they exist)
        if hasattr(app, 'midi_panel'):
            self.midi_device = app.midi_panel.midi_device
            self.play_pause_note = app.midi_panel.play_pause_note
            self.rewind_note = app.midi_panel.rewind_note
            self.next_section_note = app.midi_panel.next_section_note
            self.prev_section_note = app.midi_panel.prev_section_note
            self.midi_status = app.midi_panel.midi_status
        else:
            self.midi_device = tk.StringVar()
            self.play_pause_note = tk.StringVar(value="60")
            self.rewind_note = tk.StringVar(value="62")
            self.next_section_note = tk.StringVar(value="64")
            self.prev_section_note = tk.StringVar(value="65")
            self.midi_status = tk.StringVar(value="MIDI: Disabled")
        
        # MIDI learn mode variables
        self.learn_mode = False
        self.learning_variable = None
        self.original_command_map = {}
        
        # Set up the UI
        self.setup_ui()
        
        # Initial refresh of devices
        self.refresh_devices()
    
    def center_on_parent(self):
        """Center the dialog on the parent window."""
        parent = self.parent
        
        # Get parent geometry
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Calculate position
        width = 450
        height = 400
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        # Set geometry
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Set up the dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top row: Status and enable/disable
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, textvariable=self.midi_status).pack(side=tk.LEFT, padx=(0, 10))
        
        self.toggle_button = ttk.Button(
            top_frame, 
            text="Enable MIDI" if self.midi_status.get() == "MIDI: Disabled" else "Disable MIDI", 
            command=self.toggle_midi
        )
        self.toggle_button.pack(side=tk.LEFT)
        
        ttk.Button(
            top_frame, 
            text="Refresh Devices", 
            command=self.refresh_devices
        ).pack(side=tk.LEFT, padx=5)
        
        # Second row: Device selection
        device_frame = ttk.Frame(main_frame)
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(device_frame, text="MIDI Device:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_combo = ttk.Combobox(
            device_frame, 
            textvariable=self.midi_device, 
            state="readonly",
            width=30
        )
        self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=10)
        
        # Mapping section
        mapping_frame = ttk.LabelFrame(main_frame, text="Control Mapping", padding=10)
        mapping_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Configure grid
        mapping_frame.columnconfigure(0, weight=1)
        mapping_frame.columnconfigure(1, weight=1)
        mapping_frame.columnconfigure(2, weight=1)
        
        # Instructions
        instruction_label = ttk.Label(
            mapping_frame, 
            text="Assign MIDI notes or CC messages to app functions.\n"
                 "Use 'Learn' to detect a pedal press or manually enter the note number.",
            wraplength=400,
            justify=tk.LEFT
        )
        instruction_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(0, 10))
        
        # Play/Pause mapping
        ttk.Label(mapping_frame, text="Play/Pause:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.play_pause_note, width=5).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.play_pause_note)
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Rewind mapping
        ttk.Label(mapping_frame, text="Rewind:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.rewind_note, width=5).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.rewind_note)
        ).grid(row=2, column=2, padx=5, pady=5)
        
        # Next Section mapping
        ttk.Label(mapping_frame, text="Next Section:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.next_section_note, width=5).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.next_section_note)
        ).grid(row=3, column=2, padx=5, pady=5)
        
        # Previous Section mapping
        ttk.Label(mapping_frame, text="Previous Section:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.prev_section_note, width=5).grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.prev_section_note)
        ).grid(row=4, column=2, padx=5, pady=5)
        
        # Footer with buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            button_frame, 
            text="Apply", 
            command=self.apply_settings
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Close", 
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def toggle_midi(self):
        """Toggle MIDI input on/off."""
        if not hasattr(self.app, 'midi_controller') or self.app.midi_controller is None:
            messagebox.showerror("Error", "MIDI controller not initialized")
            return
            
        # Check current state by checking if the MIDI thread is active
        is_active = self.app.midi_controller.midi_thread and self.app.midi_controller.midi_thread.is_alive()
        
        if is_active:
            # Disable MIDI
            self.app.midi_controller.stop_midi_listener()
            self.midi_status.set("MIDI: Disabled")
            self.toggle_button.config(text="Enable MIDI")
            self.app.sts.set("MIDI control disabled")
        else:
            # Enable MIDI
            if not self.midi_device.get():
                # If no device is selected, try to select the first available
                devices = self.app.midi_controller.get_available_devices()
                if devices:
                    self.midi_device.set(devices[0])
                    self.app.midi_controller.set_active_ports([devices[0]])
                else:
                    messagebox.showerror("Error", "No MIDI devices available")
                    return
            
            # Start listener
            self.app.midi_controller.start_midi_listener()
            self.midi_status.set("MIDI: Enabled")
            self.toggle_button.config(text="Disable MIDI")
            self.app.sts.set(f"MIDI control enabled: {self.midi_device.get()}")
        
        # Update settings
        if hasattr(self.app, 'settings'):
            self.app.settings.midi_settings["enabled"] = not is_active
            self.app.settings.save_settings(self.app)
    
    def refresh_devices(self):
        """Refresh the list of available MIDI devices."""
        if not hasattr(self.app, 'midi_controller') or self.app.midi_controller is None:
            messagebox.showerror("Error", "MIDI controller not initialized")
            return
            
        devices = self.app.midi_controller.get_available_devices()
        self.device_combo['values'] = devices
        
        if devices:
            if self.midi_device.get() not in devices:
                self.midi_device.set(devices[0])
            self.app.sts.set(f"Found {len(devices)} MIDI devices")
        else:
            self.midi_device.set("")
            self.app.sts.set("No MIDI devices found")
    
    def on_device_selected(self, event):
        """Handle device selection from dropdown."""
        selected_device = self.midi_device.get()
        if selected_device and hasattr(self.app, 'midi_controller'):
            self.app.midi_controller.set_active_ports([selected_device])
            self.app.sts.set(f"Selected MIDI device: {selected_device}")
            
            # Update settings
            if hasattr(self.app, 'settings'):
                self.app.settings.midi_settings["device"] = selected_device
                self.app.settings.save_settings(self.app)
    
    def start_learn_mode(self, target_var):
        """Enter MIDI learn mode for a specific control."""
        if not hasattr(self.app, 'midi_controller') or not self.app.midi_controller.midi_thread:
            # Try to start MIDI if it's not active
            if self.app.midi_controller:
                self.app.midi_controller.start_midi_listener()
                self.midi_status.set("MIDI: Enabled")
                self.toggle_button.config(text="Disable MIDI")
            else:
                messagebox.showerror("Error", "MIDI controller not available")
                return
            
        # Set learn mode
        self.learn_mode = True
        self.learning_variable = target_var
        
        # Change status
        self.app.sts.set("MIDI Learn Mode: Press your foot controller pedal now...")
        
        # Store original command map and create a temporary one for learning
        self.original_command_map = self.app.midi_controller.command_map.copy()
        self.app.midi_controller.clear_commands()
        
        # Add a temporary handler for all possible notes and control changes
        for note in range(128):
            self.app.midi_controller.add_command(note, lambda n=note: self.learn_midi_note(n))
    
    def learn_midi_note(self, note):
        """Handle a MIDI note during learn mode."""
        if self.learn_mode and self.learning_variable:
            # Set the note in the variable
            self.learning_variable.set(str(note))
            
            # Exit learn mode
            self.learn_mode = False
            self.app.sts.set(f"MIDI control learned: Note/CC {note}")
            
            # Restore the original command map
            self.app.midi_controller.clear_commands()
            self.apply_settings()
    
    def apply_settings(self):
        """Apply the current MIDI settings."""
        if not hasattr(self.app, 'midi_controller') or self.app.midi_controller is None:
            messagebox.showerror("Error", "MIDI controller not initialized")
            return
            
        # Clear existing mappings
        self.app.midi_controller.clear_commands()
        
        # Add new mappings
        try:
            # Play/Pause
            play_note = int(self.play_pause_note.get())
            self.app.midi_controller.add_command(play_note, self.app.play_pause_toggle)
            
            # Rewind
            rewind_note = int(self.rewind_note.get())
            self.app.midi_controller.add_command(rewind_note, self.app.rewind_section_start)
            
            # Next Section
            next_note = int(self.next_section_note.get())
            self.app.midi_controller.add_command(next_note, self.go_to_next_section)
            
            # Previous Section
            prev_note = int(self.prev_section_note.get())
            self.app.midi_controller.add_command(prev_note, self.go_to_prev_section)
            
            self.app.sts.set("MIDI control mappings applied")
            
            # Update settings
            if hasattr(self.app, 'settings'):
                self.app.settings.midi_settings.update({
                    "play_pause_note": play_note,
                    "rewind_note": rewind_note,
                    "next_section_note": next_note,
                    "prev_section_note": prev_note,
                    "device": self.midi_device.get()
                })
                self.app.settings.save_settings(self.app)
                
        except ValueError:
            messagebox.showerror("Error", "Invalid MIDI note values")
    
    def go_to_next_section(self):
        """Navigate to the next section in the list."""
        if not hasattr(self.app, 'section_panel') or not self.app.eng.current_song:
            return
            
        # Get current section
        current_section = self.app.section_panel.xcb.get()
        sections = list(self.app.section_panel.xcb['values'])
        
        if not sections:
            return
            
        # Find current index
        try:
            current_index = sections.index(current_section)
            next_index = (current_index + 1) % len(sections)
            # Set the new section
            self.app.section_panel.xcb.set(sections[next_index])
            # Trigger the selection handler
            self.app.section_panel.on_section_selected(None)
            self.app.sts.set(f"Selected section: {sections[next_index]}")
        except ValueError:
            # Section not found in list
            if sections:
                self.app.section_panel.xcb.set(sections[0])
                self.app.section_panel.on_section_selected(None)
                self.app.sts.set(f"Selected section: {sections[0]}")
    
    def go_to_prev_section(self):
        """Navigate to the previous section in the list."""
        if not hasattr(self.app, 'section_panel') or not self.app.eng.current_song:
            return
            
        # Get current section
        current_section = self.app.section_panel.xcb.get()
        sections = list(self.app.section_panel.xcb['values'])
        
        if not sections:
            return
            
        # Find current index
        try:
            current_index = sections.index(current_section)
            prev_index = (current_index - 1) % len(sections)
            # Set the new section
            self.app.section_panel.xcb.set(sections[prev_index])
            # Trigger the selection handler
            self.app.section_panel.on_section_selected(None)
            self.app.sts.set(f"Selected section: {sections[prev_index]}")
        except ValueError:
            # Section not found in list
            if sections:
                self.app.section_panel.xcb.set(sections[-1])
                self.app.section_panel.on_section_selected(None)
                self.app.sts.set(f"Selected section: {sections[-1]}")