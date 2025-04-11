import tkinter as tk
from tkinter import ttk, messagebox

class MidiSettingsPanel(ttk.LabelFrame):
    """Panel for configuring MIDI device input and controls."""
    
    def __init__(self, parent, app):
        super().__init__(parent, padding="0")
        self.app = app
        
        # MIDI status variable
        self.midi_status = tk.StringVar(value="MIDI: Disabled")
        
        # MIDI device variable
        self.midi_device = tk.StringVar()
        
        # MIDI note mapping variables
        self.play_pause_note = tk.StringVar(value="60")
        self.rewind_note = tk.StringVar(value="62")
        self.next_section_note = tk.StringVar(value="64")
        self.prev_section_note = tk.StringVar(value="65")
        
        # MIDI learn mode variables
        self.learn_mode = False
        self.learning_variable = None
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the MIDI settings UI."""
        # Main frame for settings
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top row: Status and enable/disable
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, textvariable=self.midi_status).pack(side=tk.LEFT, padx=(0, 10))
        
        self.toggle_button = ttk.Button(
            top_frame, 
            text="Enable MIDI", 
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
        
        # Mapping section
        mapping_frame = ttk.LabelFrame(main_frame, text="Control Mapping", padding=5)
        mapping_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        mapping_frame.columnconfigure(0, weight=1)
        mapping_frame.columnconfigure(1, weight=1)
        mapping_frame.columnconfigure(2, weight=1)
        
        # Play/Pause mapping
        ttk.Label(mapping_frame, text="Play/Pause:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.play_pause_note, width=5).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.play_pause_note)
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Rewind mapping
        ttk.Label(mapping_frame, text="Rewind:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.rewind_note, width=5).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.rewind_note)
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Next Section mapping
        ttk.Label(mapping_frame, text="Next Section:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.next_section_note, width=5).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.next_section_note)
        ).grid(row=2, column=2, padx=5, pady=5)
        
        # Previous Section mapping
        ttk.Label(mapping_frame, text="Previous Section:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(mapping_frame, textvariable=self.prev_section_note, width=5).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(
            mapping_frame, 
            text="Learn", 
            command=lambda: self.start_learn_mode(self.prev_section_note)
        ).grid(row=3, column=2, padx=5, pady=5)
        
        # Apply button
        ttk.Button(
            main_frame, 
            text="Apply Mappings", 
            command=self.apply_mappings
        ).pack(pady=(10, 0), anchor=tk.E)
    
    def toggle_midi(self):
        """Toggle MIDI input on/off."""
        if not hasattr(self.app, 'midi_controller'):
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
    
    def refresh_devices(self):
        """Refresh the list of available MIDI devices."""
        if not hasattr(self.app, 'midi_controller'):
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
    
    def start_learn_mode(self, target_var):
        """Enter MIDI learn mode for a specific control."""
        if not hasattr(self.app, 'midi_controller') or not self.app.midi_controller.midi_thread:
            messagebox.showerror("Error", "MIDI controller not active")
            return
            
        # Set learn mode
        self.learn_mode = True
        self.learning_variable = target_var
        
        # Change status
        self.app.sts.set("MIDI Learn Mode: Press your foot controller pedal now...")
        
        # Store original command map and create a temporary one for learning
        self.original_command_map = self.app.midi_controller.command_map.copy()
        self.app.midi_controller.clear_commands()
        
        # Add a temporary handler for all possible notes
        for note in range(128):
            self.app.midi_controller.add_command(note, lambda n=note: self.learn_midi_note(n))
    
    def learn_midi_note(self, note):
        """Handle a MIDI note during learn mode."""
        if self.learn_mode and self.learning_variable:
            # Set the note in the variable
            self.learning_variable.set(str(note))
            
            # Exit learn mode
            self.learn_mode = False
            self.app.sts.set(f"MIDI control learned: Note {note}")
            
            # Restore the original command map
            self.app.midi_controller.clear_commands()
            self.apply_mappings()
    
    def apply_mappings(self):
        """Apply the current MIDI note mappings."""
        if not hasattr(self.app, 'midi_controller'):
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
            
            # Save to settings
            self.app.settings.save_midi_settings()
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