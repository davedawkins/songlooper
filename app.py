import os
import tkinter as tk
from tkinter import ttk, messagebox, Menu
from audio_engine import AudioEngine

from ui.song_selection import SongSelectionPanel
from ui.section_controls import SectionControlPanel
from ui.playback_controls import PlaybackControlPanel
from ui.slider_view import SliderView
from ui.stems_panel import StemsPanel
from ui.midi_settings import MidiSettingsPanel
from utils.settings import SettingsManager
from utils.midi_controller import MidiController

class GuitarPracticeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Guitar Practice Tool")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # --- Engine & State ---
        self.eng = AudioEngine()
        self.dir = ""
        
        # --- MIDI Controller ---
        try:
            self.midi_controller = MidiController()
        except Exception as e:
            print(f"Could not initialize MIDI controller: {e}")
            self.midi_controller = None
        
        # --- Persistent Vars ---
        self.fdr = tk.StringVar()  # Folder
        self.spd = tk.DoubleVar(value=1.0)  # Speed
        self.dly = tk.DoubleVar(value=0.5)  # Delay
        self.lop = tk.BooleanVar(value=True)  # Loop
        self.cin = tk.BooleanVar(value=False)  # Count-in
        self.snm = tk.StringVar()  # Section name
        self.svm = tk.BooleanVar(value=False)  # Section view mode
        self.stt = tk.StringVar(value="00:00.0")  # Start time
        self.ent = tk.StringVar(value="00:00.0")  # End time
        
        # Status variable
        self.sts = tk.StringVar(value="Ready")
        
        # Settings manager
        self.settings = SettingsManager()
        # Store reference to app in settings manager for MIDI settings
        self.settings.app = self
        
        # Build the UI
        self.setup_ui()
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Bind resize events to main window
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Load settings and start position updates
        self.load_settings()
        
        # Set up the mute status change callback in the audio engine
        self.eng.set_mute_callback(self.on_mute_status_change)
        
    def setup_ui(self):
        """Build the main UI frame and all components."""
        # Main frame
        self.frm = ttk.Frame(self.root, padding="10")
        self.frm.pack(fill=tk.BOTH, expand=True)
        
        # Create menu
        self.setup_menu()
        
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
        
        # Create notebook for tabbed panels
        self.notebook = ttk.Notebook(self.frm)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Stems panel (first tab)
        self.stems_panel = StemsPanel(self.notebook, self)
        self.notebook.add(self.stems_panel, text="Stems")
        
        # MIDI settings panel (second tab)
        if self.midi_controller is not None:
            self.midi_panel = MidiSettingsPanel(self.notebook, self)
            self.notebook.add(self.midi_panel, text="MIDI Control")
        
        # Status bar
        ttk.Label(self.frm, textvariable=self.sts, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_menu(self):
        """Set up application menu."""
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Songs Folder", command=self.browse_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Control menu
        control_menu = Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Control", menu=control_menu)
        control_menu.add_command(label="Play/Pause", command=self.play_pause_toggle)
        control_menu.add_command(label="Rewind to Start", command=self.rewind_section_start)
        
        # MIDI menu
        if self.midi_controller is not None:
            midi_menu = Menu(menu_bar, tearoff=0)
            menu_bar.add_cascade(label="MIDI", menu=midi_menu)
            midi_menu.add_command(label="MIDI Settings", command=self.open_midi_settings)
            midi_menu.add_command(label="Refresh MIDI Devices", 
                                command=lambda: self.midi_panel.refresh_devices() if hasattr(self, 'midi_panel') else None)
    
    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for the application."""
        # Bind to the root window for global keyboard handling
        self.root.bind_all("<space>", self.on_spacebar, add="+")
        self.root.bind_all("0", self.on_zero_key, add="+")
        self.root.bind_all("<Left>", self.on_left_arrow, add="+")
        
        # We also need to handle various widgets that might consume the spacebar
        # Apply spacebar handling to all interactive widgets
        self._bind_spacebar_to_all_widgets(self.frm)

    def _bind_spacebar_to_all_widgets(self, parent):
        """Recursively bind spacebar handler to all interactive widgets."""
        for widget in parent.winfo_children():
            # Add our spacebar handler to common interactive widgets
            if isinstance(widget, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton, 
                                ttk.Combobox, ttk.Entry, tk.Button)):
                widget.bind("<space>", self._intercept_spacebar, add="+")
            
            # Handle Text widgets specially
            if isinstance(widget, tk.Text):
                widget.bind("<space>", self._handle_text_space, add="+")
                
            # Recursively process any container widgets
            if widget.winfo_children():
                self._bind_spacebar_to_all_widgets(widget)

    def _intercept_spacebar(self, event):
        """Intercept spacebar events from widgets and handle them."""
        # Process the spacebar event
        self.on_spacebar(event)
        # Prevent the default widget behavior
        return "break"

    def _handle_text_space(self, event):
        """Special handler for text widgets to allow typing but also handle global shortcut."""
        # Process the spacebar event
        self.on_spacebar(event)
        # Allow the space to also be entered into the text
        return None

    def on_spacebar(self, event):
        """Handle spacebar press - toggle play/pause."""
        # Check if a Text or Entry widget has focus
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Text, ttk.Entry, tk.Entry)):
            # Let the key pass through to these widgets
            return None
        
        # Otherwise, toggle play/pause
        self.play_pause_toggle()
        return "break"  # Prevent default behavior

    def on_zero_key(self, event):
        """Handle 0 key press - go to start of section."""
        # Check if entry widget has focus (allow typing 0)
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Text, ttk.Entry, tk.Entry)):
            # Let the key pass through to these widgets
            return None
        
        self.rewind_section_start()
        return "break"  # Prevent default behavior

    def on_left_arrow(self, event):
        """Handle left arrow key press - go back 3 seconds."""
        # Check if a text widget has focus (allow cursor movement)
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Text, ttk.Entry, tk.Entry)):
            # Let the key pass through to text entry widgets
            return None
            
        if not self.eng.current_song:
            return "break"
            
        # Get current position and section start
        current_pos = self.eng.get_current_position()
        start_time = self.section_panel.parse_time(self.stt.get())
        
        # Calculate new position (3 seconds back, but not before section start)
        new_pos = max(start_time, current_pos - 3.0)
        
        # Update engine position
        was_playing = self.eng.is_playing()
        if was_playing:
            self.eng.pause()
        
        self.eng.set_start_position(new_pos)
        
        # Update UI
        self.slider_view.pos.set(new_pos)
        self.slider_view.update_marker_positions()
        
        # Resume if was playing
        if was_playing:
            self.play_current()
            self.sts.set(f"Moved back to {self.section_panel.format_time(new_pos)}")
        else:
            self.sts.set(f"Position: {self.section_panel.format_time(new_pos)}")
            
        return "break"  # Prevent default behavior
    
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
    
    def on_mute_status_change(self):
        """Callback for when a stem's mute status changes during playback."""
        if hasattr(self, 'slider_view'):
            self.slider_view.update_marker_positions()
    
    def update_song_position(self):
        """Poll engine position and update UI."""
        if self.eng.is_playing():
            pos = self.eng.get_current_position()
            total_duration = self.eng.get_total_duration()
            
            # Update position variable using data binding
            self.slider_view.pos.set(pos)
            
            # Check if we've hit the end marker for the section
            end_time_str = self.ent.get()
            end_time = self.section_panel.parse_time(end_time_str)
            
            if pos >= end_time:
                if self.lop.get():
                    # Loop back to start of section
                    self.eng.stop()
                    start_time = self.section_panel.parse_time(self.stt.get()) 
                    self.eng.set_start_position(start_time)
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
            start_time = self.section_panel.parse_time(self.stt.get())
            
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
                formatted_time = self.section_panel.format_time(old_pos)
                self.sts.set(f"Resumed from {formatted_time} at {self.spd.get()}x speed")
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
        start_time_str = self.stt.get()
        start_time = self.section_panel.parse_time(start_time_str)
        was_playing = self.eng.is_playing()
        
        # Stop playback
        self.eng.stop()
        
        # Update engine position
        self.eng.set_start_position(start_time)
        
        # Update slider position variable
        # This triggers the trace callback which updates the UI
        self.slider_view.pos.set(start_time)
        
        # Force an update of the marker positions
        self.slider_view.update_marker_positions()
        
        # Resume playback if it was playing
        if was_playing:
            self.play_current()
            formatted_time = self.section_panel.format_time(start_time)
            self.sts.set(f"Rewound and playing from {formatted_time}")
        else:
            formatted_time = self.section_panel.format_time(start_time)
            self.sts.set(f"Rewound to {formatted_time} (paused)")
    
    def open_midi_settings(self):
        """Open the MIDI settings dialog."""
        from ui.midi_dialog import MidiSettingsDialog
        dialog = MidiSettingsDialog(self.root, self)
    
    # MIDI navigation functions
    def go_to_next_section(self):
        """Navigate to the next section in the list."""
        if not hasattr(self, 'section_panel') or not self.eng.current_song:
            return
            
        # Get current section
        current_section = self.section_panel.xcb.get()
        sections = list(self.section_panel.xcb['values'])
        
        if not sections:
            return
            
        # Find current index
        try:
            current_index = sections.index(current_section)
            next_index = (current_index + 1) % len(sections)
            # Set the new section
            self.section_panel.xcb.set(sections[next_index])
            # Trigger the selection handler
            self.section_panel.on_section_selected(None)
            self.sts.set(f"Selected section: {sections[next_index]}")
        except ValueError:
            # Section not found in list
            if sections:
                self.section_panel.xcb.set(sections[0])
                self.section_panel.on_section_selected(None)
                self.sts.set(f"Selected section: {sections[0]}")
    
    def go_to_prev_section(self):
        """Navigate to the previous section in the list."""
        if not hasattr(self, 'section_panel') or not self.eng.current_song:
            return
            
        # Get current section
        current_section = self.section_panel.xcb.get()
        sections = list(self.section_panel.xcb['values'])
        
        if not sections:
            return
            
        # Find current index
        try:
            current_index = sections.index(current_section)
            prev_index = (current_index - 1) % len(sections)
            # Set the new section
            self.section_panel.xcb.set(sections[prev_index])
            # Trigger the selection handler
            self.section_panel.on_section_selected(None)
            self.sts.set(f"Selected section: {sections[prev_index]}")
        except ValueError:
            # Section not found in list
            if sections:
                self.section_panel.xcb.set(sections[-1])
                self.section_panel.on_section_selected(None)
                self.sts.set(f"Selected section: {sections[-1]}")
    
    def on_closing(self):
        """Handle window close."""
        if self.eng.is_playing():
            self.eng.stop()
            
        # Stop MIDI controller if active
        if hasattr(self, 'midi_controller') and self.midi_controller is not None:
            self.midi_controller.stop_midi_listener()
            
        self.settings.save_settings(self)
        self.root.destroy()