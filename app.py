import os
import tkinter as tk
from tkinter import ttk, messagebox, Menu
from audio_engine import AudioEngine
import tkinter.font as tkFont

from ui.song_selection import SongSelectionPanel
from ui.section_controls import SectionControlPanel
from ui.playback_controls import PlaybackControlPanel
from ui.slider_view import SliderView
from ui.stems_panel import StemsPanel
from ui.midi_settings import MidiSettingsPanel
from utils.settings import SettingsManager
from utils.midi_controller import MidiController
from ui.slider_time_utils import SliderTimeUtils
from tkhtmlview import HTMLLabel

import markdown

class TimeLabel(ttk.Label):

    def __init__(self,parent,app):
        super().__init__(parent)
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.config(text="00:00.0 / 00:00.0", width=20)
        self.pack(side=tk.LEFT, padx=(0, 5))

        self.app.pos.trace_add("write", lambda *args: self.update())
        
    def update(self):
        current = self.app.pos.get()
        total = self.app.eng.get_total_duration() if self.app.eng.current_song else 0.0

        time_text = f"{SliderTimeUtils.format_time(current)} / {SliderTimeUtils.format_time(total)}"
        self.config(text=time_text)

class GuitarPracticeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Guitar Practice Tool")
        self.root.geometry("1200x1200")
        self.root.minsize(600, 600)
        
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
        self.songName = tk.StringVar()
        self.stt = tk.StringVar(value="00:00.0")  # Section Start time
        self.ent = tk.StringVar(value="00:00.0")  # Section End time
        self.bpm = tk.DoubleVar(value=120) #  BPM

        # Add trace to speed variable to update engine immediately
        self.spd.trace_add("write", self._on_speed_changed)

        # Status variable
        self.sts = tk.StringVar(value="Ready")
        self.pos = tk.DoubleVar(value=0.0) # Song position

        # View range variables
        self.vst = tk.DoubleVar(value=0.0) # View start time
        self.vet = tk.DoubleVar(value=1.0) # View end time (will be updated by dur trace)

        # Settings manager
        self.settings = SettingsManager()
        # Store reference to app in settings manager for MIDI settings
        self.settings.app = self
        # Load settings and start position updates
        self.load_settings()
        
        # Build the UI
        self.setup_ui()
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Bind resize events to main window
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Load settings and start position updates
        self.apply_settings()
        
        # Set up the mute status change callback in the audio engine
        self.eng.add_mute_callback(self.on_mute_status_change)
        
        self.bpm.trace_add("write", lambda *args:self.section_panel.save_song_config())
        # Update trace for ent to also update markers
        self.ent.trace_add("write", lambda *args: self._on_ent_changed())
        # Update trace for stt to also update markers
        self.stt.trace_add("write", lambda *args: self._on_stt_changed())

        # Traces for view range changes
        self.vst.trace_add("write", lambda *args: self.slider_view.update_marker_positions() if hasattr(self, 'slider_view') else None)
        self.vet.trace_add("write", lambda *args: self.slider_view.update_marker_positions() if hasattr(self, 'slider_view') else None)

        # Set initial focus to the slider canvas after the UI is idle
        self.root.after_idle(lambda: self.slider_view.canvas.focus_set() if hasattr(self, 'slider_view') else None)

    def _on_stt_changed(self, *args):
        """Callback when the start time variable changes."""
        try:
            start_time = SliderTimeUtils.parse_time(self.stt.get())
            if hasattr(self, 'eng'):
                self.eng.set_start_position(start_time)
            if hasattr(self, 'slider_view'):
                self.slider_view.update_marker_positions()
        except Exception as e:
            print(f"Error handling stt change: {e}")

    def _on_ent_changed(self, *args):
        """Callback when the end time variable changes."""
        try:
            end_time = SliderTimeUtils.parse_time(self.ent.get())
            if hasattr(self, 'eng'):
                self.eng.set_end_position(end_time)
            if hasattr(self, 'slider_view'):
                self.slider_view.update_marker_positions()
        except Exception as e:
            print(f"Error handling ent change: {e}")

    def _on_speed_changed(self, *args):
        """Callback when the speed variable changes."""
        if hasattr(self, 'eng'): # Ensure engine exists
            try:
                new_speed = self.spd.get()
                self.eng.set_playback_speed(new_speed)
                # Optional: Update status bar if not already handled elsewhere
                # self.sts.set(f"Speed set to {new_speed}x")
            except Exception as e:
                print(f"Error setting engine speed: {e}")

    def save_settings(self):
        self.settings.save_settings(self)

    def setup_ui(self):
        """Build the main UI frame and all components."""
        # Main frame
        self.frm = ttk.Frame(self.root, padding=20)
        self.frm.pack(fill=tk.BOTH, expand=True)
        
        # Create menu
        self.setup_menu()
        
        # Top folder selection
        self.setup_folder_selection()
        
        # Create panels
        self.song_panel = SongSelectionPanel(self.frm, self)
        self.song_panel.pack(fill=tk.X, pady=(0, 2))
        
        self.section_panel = SectionControlPanel(self.frm, self)
        self.section_panel.pack(fill=tk.X, pady=(0, 2))
        
        self.playback_panel = PlaybackControlPanel(self.frm, self)
        self.playback_panel.pack(fill=tk.X, pady=(0, 2))

        # Create PanedWindow for Slider and Notebook
        self.paned_window = ttk.PanedWindow(self.frm, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        # Slider with markers
        self.slider_view = SliderView(self.paned_window, self)
        # self.slider_view.pack(fill=tk.BOTH, pady=(0, 2)) # Removed old packing
        self.paned_window.add(self.slider_view, weight=1) # Add slider to paned window

        # Transport buttons (Positioned after slider, before notebook in layout)
        self.setup_transport()

        # Create notebook for tabbed panels, setting initial height
        self.notebook = ttk.Notebook(self.paned_window, padding=[0,0,0,10], height=100) 
        # self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 0)) # Removed old packing
        # Add notebook to paned window with low weight
        self.paned_window.add(self.notebook, weight=0) 
        
        # monospace_font = tkFont.Font(family="Courier", size=12)  # Change "Courier" if needed

        # self.notes_frame = tk.Frame( self.notebook, bg="white")
        # self.notes_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # self.notes_frame2 = tk.Frame( self.notes_frame)
        # self.notes_frame2.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # self.notes_panel = HTMLLabel(self.notes_frame2, html="No notes", font=monospace_font, background="white", borderwidth=0, highlightthickness=0)
        # self.notes_panel.pack(fill=tk.BOTH, expand=True)
        # self.notebook.add(self.notes_frame, text="Notes")

        # Stems panel (first tab)
        # self.stems_panel = StemsPanel(self.notebook, self)
        # self.notebook.add(self.stems_panel, text="Stems")
        
        # MIDI settings panel (second tab)
        self.midi_panel = MidiSettingsPanel(self.notebook, self)
        self.notebook.add(self.midi_panel, text="MIDI Control")
        
        # Status bar
        ttk.Label(self.frm, textvariable=self.sts, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

        # self.songName.trace_add( "write", lambda *args: self.loadNotes())
    

    def toggle_stem(self, stem_name):
            """Toggle a stem's muted state."""
            app = self
            eng = app.eng
            print(f"App: Toggling stem '{stem_name}'")

            if not eng.current_song:
                return
                
            # Get the current state
            # current_state = self.stv[stem_name].get()
            # is_muted = stem_name in eng.muted_stems
            
            # Toggle mute state
            new_mute = eng.toggle_mute_stem(stem_name)
            song_title = eng.current_song.title if eng.current_song else ""
            
            # Update muted stems in settings
            if song_title not in app.settings.mut:
                app.settings.mut[song_title] = []
            
            if new_mute:
                if (stem_name not in app.settings.mut[song_title]):
                    app.settings.mut[song_title].append(stem_name)
                app.sts.set(f"Muted: {stem_name}")
            else:
                if (stem_name in app.settings.mut[song_title]):
                    app.settings.mut[song_title].remove(stem_name)
                app.sts.set(f"Unmuted: {stem_name}")
            
            # Update UI to reflect new state (opposite of muted state)
            # self.stv[stem_name].set(not new_mute)
            
            # Save settings immediately
            app.settings.save_settings(app)
            
            # Update the waveform to reflect mute changes
            if hasattr(app, 'slider_view'):
                app.slider_view.update_marker_positions()
        


    def wrapHtml( html : str ):
        return f"""
    <div style="background-color: white;">
    {html}
    </div>
    """

    # def loadNotes(self):
    #     song_name = self.songName.get()
    #     notes_path = os.path.join(self.dir,song_name, "notes.md")
    #     if os.path.exists(notes_path):
    #         with open(notes_path, "r", encoding="utf-8") as file:
    #             content = file.read()
    #             html_text = markdown.markdown(content)
    #             self.notes_panel.set_html( GuitarPracticeApp.wrapHtml(html_text) )
    #             print(html_text)
    #     else:
    #         self.notes_panel.set_html( GuitarPracticeApp.wrapHtml("(Add song notes to " + notes_path + ")") )
            
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
        # self.root.bind_all("<Left>", self.on_left_arrow, add="+") # REMOVED global left arrow

        # We also need to handle various widgets that might consume the spacebar
        # Apply spacebar handling to all interactive widgets
        self._bind_spacebar_to_all_widgets(self.frm)

        # Bind shortcuts specific to the slider canvas having focus
        # Ensure slider_view and section_panel are initialized before binding
        if hasattr(self, 'slider_view') and hasattr(self, 'section_panel'):
             # Use <KeyPress-i> for lowercase 'i', <KeyPress-I> for uppercase 'I'
             # Binding to the lowercase ensures it works regardless of Caps Lock state usually.
            self.slider_view.canvas.bind("<KeyPress-[>", self.section_panel.set_start_time_to_current_pos)
            self.slider_view.canvas.bind("<KeyPress-]>", self.section_panel.set_end_time_to_current_pos)
            # Bind speed controls to comma and period keys on the slider canvas
            self.slider_view.canvas.bind("<KeyPress-,>", self.decrease_speed) # '<' key
            self.slider_view.canvas.bind("<KeyPress-.>", self.increase_speed) # '>' key
            # Bind arrow keys for nudging end marker on the slider canvas - CHANGED TO J/L
            self.slider_view.canvas.bind("<KeyPress-j>", self.nudge_end_time_backward) # WAS <KeyPress-Left>
            self.slider_view.canvas.bind("<KeyPress-l>", self.nudge_end_time_forward) # WAS <KeyPress-Right>
            # Bind A/D keys for nudging start marker on the slider canvas
            self.slider_view.canvas.bind("<KeyPress-a>", self.nudge_start_time_backward)
            self.slider_view.canvas.bind("<KeyPress-d>", self.nudge_start_time_forward)
            # Bind S/E keys for moving position to start/end marker on the slider canvas
            self.slider_view.canvas.bind("<KeyPress-s>", self.move_pos_to_start)
            self.slider_view.canvas.bind("<KeyPress-e>", self.move_pos_to_end)
            # Bind Left/Right arrow keys for nudging play position
            self.slider_view.canvas.bind("<KeyPress-Left>", self.nudge_pos_backward)
            self.slider_view.canvas.bind("<KeyPress-Right>", self.nudge_pos_forward)
            # Bind Z/Shift-Z for view controls
            self.slider_view.canvas.bind("<KeyPress-z>", self.slider_view.toggle_zoom)
            self.slider_view.canvas.bind("<KeyPress-Z>", self.slider_view.reset_view) # Shift + z
            # Bind 1-9 keys for toggling stem mute on the slider canvas
            for i in range(1, 10):
                self.slider_view.canvas.bind(f"<KeyPress-{i}>", self.on_stem_key_press)


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

    def nudge_pos_backward(self, event=None):
        """Nudge the playback position backward by 0.25s."""
        if not self.eng.current_song:
            return "break"

        try:
            current_pos = self.pos.get()
            current_view_start = self.vst.get()
            was_playing = self.eng.is_playing()

            new_pos = max(0.0, current_pos - 0.25)

            if was_playing:
                self.eng.pause()

            self.eng.set_position(new_pos)
            self.pos.set(new_pos) # Update UI variable

            # Adjust view start if necessary
            if new_pos < current_view_start:
                self.vst.set(new_pos)

            formatted_time = SliderTimeUtils.format_time(new_pos)
            self.sts.set(f"Position nudged back to {formatted_time}")

            if was_playing:
                self.play_current() # Resume playback

        except Exception as e:
            print(f"Error nudging position backward: {e}")
            self.sts.set("Error nudging position")
        return "break" # Prevent default behavior

    def nudge_pos_forward(self, event=None):
        """Nudge the playback position forward by 0.25s."""
        if not self.eng.current_song:
            return "break"

        try:
            current_pos = self.pos.get()
            total_duration = self.eng.get_total_duration()
            current_view_end = self.vet.get()
            was_playing = self.eng.is_playing()

            new_pos = min(total_duration, current_pos + 0.25)

            if was_playing:
                self.eng.pause()

            self.eng.set_position(new_pos)
            self.pos.set(new_pos) # Update UI variable

            # Adjust view end if necessary
            if new_pos > current_view_end:
                self.vet.set(new_pos)

            formatted_time = SliderTimeUtils.format_time(new_pos)
            self.sts.set(f"Position nudged forward to {formatted_time}")

            if was_playing:
                self.play_current() # Resume playback

        except Exception as e:
            print(f"Error nudging position forward: {e}")
            self.sts.set("Error nudging position")
        return "break" # Prevent default behavior

    def move_pos_to_start(self, event=None):
        """Move the playback position to the section start marker."""
        if not self.eng.current_song:
            return "break"

        try:
            start_time = SliderTimeUtils.parse_time(self.stt.get())
            was_playing = self.eng.is_playing()

            if was_playing:
                self.eng.pause()

            self.eng.set_position(start_time)
            self.pos.set(start_time) # Update UI variable

            formatted_time = SliderTimeUtils.format_time(start_time)
            self.sts.set(f"Position moved to section start: {formatted_time}")

            if was_playing:
                self.play_current() # Resume playback

        except Exception as e:
            print(f"Error moving position to start: {e}")
            self.sts.set("Error moving position to start")
        return "break" # Prevent default behavior

    def move_pos_to_end(self, event=None):
        """Move the playback position to the section end marker."""
        if not self.eng.current_song:
            return "break"

        try:
            end_time = SliderTimeUtils.parse_time(self.ent.get())
            was_playing = self.eng.is_playing()

            if was_playing:
                self.eng.pause()

            # Ensure position is slightly before the absolute end if looping to avoid immediate loop
            # pos_to_set = end_time - 0.01 if self.lop.get() and end_time > 0 else end_time
            # Let's just set it to the end time for now. The engine handles looping logic.
            pos_to_set = end_time

            self.eng.set_position(pos_to_set)
            self.pos.set(pos_to_set) # Update UI variable

            formatted_time = SliderTimeUtils.format_time(end_time)
            self.sts.set(f"Position moved to section end: {formatted_time}")

            if was_playing:
                self.play_current() # Resume playback

        except Exception as e:
            print(f"Error moving position to end: {e}")
            self.sts.set("Error moving position to end")
        return "break" # Prevent default behavior

    def nudge_start_time_backward(self, event=None):
        """Nudge the section start time backward by 0.25s, extending view if needed."""
        if not self.eng.current_song:
            return "break"

        try:
            current_start_time = SliderTimeUtils.parse_time(self.stt.get())
            current_view_start = self.vst.get()

            new_start_time = current_start_time - 0.25
            # Clamp: Ensure new start time is not less than 0.0
            new_start_time = max(0.0, new_start_time)

            formatted_time = SliderTimeUtils.format_time(new_start_time)
            self.stt.set(formatted_time) # Trace will update engine and UI markers
            self.sts.set(f"Start time nudged back to {formatted_time}")

            # Extend view start if necessary
            if new_start_time < current_view_start:
                self.vst.set(new_start_time) # Trace will update UI markers

        except Exception as e:
            print(f"Error nudging start time backward: {e}")
            self.sts.set("Error nudging start time")
        return "break" # Prevent default behavior

    def nudge_start_time_forward(self, event=None):
        """Nudge the section start time forward by 0.25s."""
        if not self.eng.current_song:
            return "break"

        try:
            current_start_time = SliderTimeUtils.parse_time(self.stt.get())
            end_time = SliderTimeUtils.parse_time(self.ent.get())
            min_duration = 0.1 # Minimum allowed section duration

            new_start_time = current_start_time + 0.25
            # Clamp: Ensure new start time does not exceed end time - min_duration
            new_start_time = min(end_time - min_duration, new_start_time)

            formatted_time = SliderTimeUtils.format_time(new_start_time)
            self.stt.set(formatted_time) # Trace will update engine and UI markers
            self.sts.set(f"Start time nudged forward to {formatted_time}")

        except Exception as e:
            print(f"Error nudging start time forward: {e}")
            self.sts.set("Error nudging start time")
        return "break" # Prevent default behavior

    def nudge_end_time_backward(self, event=None):
        """Nudge the section end time backward by 0.25s."""
        if not self.eng.current_song:
            return "break"

        try:
            current_end_time = SliderTimeUtils.parse_time(self.ent.get())
            start_time = SliderTimeUtils.parse_time(self.stt.get())
            min_duration = 0.1 # Minimum allowed section duration

            new_end_time = current_end_time - 0.25
            # Clamp: Ensure new end time is not before start time + min_duration
            new_end_time = max(start_time + min_duration, new_end_time)

            formatted_time = SliderTimeUtils.format_time(new_end_time)
            self.ent.set(formatted_time) # Trace will update engine and UI markers
            self.sts.set(f"End time nudged back to {formatted_time}")

        except Exception as e:
            print(f"Error nudging end time backward: {e}")
            self.sts.set("Error nudging end time")
        return "break" # Prevent default behavior

    def nudge_end_time_forward(self, event=None):
        """Nudge the section end time forward by 0.25s, extending view if needed."""
        if not self.eng.current_song:
            return "break"

        try:
            current_end_time = SliderTimeUtils.parse_time(self.ent.get())
            total_duration = self.eng.get_total_duration()
            current_view_end = self.vet.get()

            new_end_time = current_end_time + 0.25
            # Clamp: Ensure new end time does not exceed total duration
            new_end_time = min(total_duration, new_end_time)

            formatted_time = SliderTimeUtils.format_time(new_end_time)
            self.ent.set(formatted_time) # Trace will update engine and UI markers
            self.sts.set(f"End time nudged forward to {formatted_time}")

            # Extend view end if necessary
            if new_end_time > current_view_end:
                self.vet.set(new_end_time) # Trace will update UI markers

        except Exception as e:
            print(f"Error nudging end time forward: {e}")
            self.sts.set("Error nudging end time")
        return "break" # Prevent default behavior

    def increase_speed(self, event=None):
        """Increase playback speed to the next available value."""
        if not hasattr(self, 'playback_panel'):
            return "break" # Panel not ready
            
        try:
            current_speed = self.spd.get()
            speeds = [float(s) for s in self.playback_panel.scx['values']]
            
            if current_speed in speeds:
                current_index = speeds.index(current_speed)
                if current_index < len(speeds) - 1:
                    next_speed = speeds[current_index + 1]
                    self.spd.set(next_speed)
                    self.sts.set(f"Speed set to {next_speed}x")
                    self.settings.save_settings(self) # Save setting
            else:
                # If current speed isn't exactly in the list, find the closest one and go up
                closest_speed = min(speeds, key=lambda s: abs(s - current_speed))
                closest_index = speeds.index(closest_speed)
                if closest_index < len(speeds) - 1:
                     next_speed = speeds[closest_index + 1]
                     self.spd.set(next_speed)
                     self.sts.set(f"Speed set to {next_speed}x")
                     self.settings.save_settings(self) # Save setting

        except Exception as e:
            print(f"Error increasing speed: {e}")
        return "break" # Prevent default behavior

    def decrease_speed(self, event=None):
        """Decrease playback speed to the previous available value."""
        if not hasattr(self, 'playback_panel'):
            return "break" # Panel not ready
            
        try:
            current_speed = self.spd.get()
            speeds = [float(s) for s in self.playback_panel.scx['values']]

            if current_speed in speeds:
                current_index = speeds.index(current_speed)
                if current_index > 0:
                    prev_speed = speeds[current_index - 1]
                    self.spd.set(prev_speed)
                    self.sts.set(f"Speed set to {prev_speed}x")
                    self.settings.save_settings(self) # Save setting
            else:
                 # If current speed isn't exactly in the list, find the closest one and go down
                closest_speed = min(speeds, key=lambda s: abs(s - current_speed))
                closest_index = speeds.index(closest_speed)
                if closest_index > 0:
                     prev_speed = speeds[closest_index - 1]
                     self.spd.set(prev_speed)
                     self.sts.set(f"Speed set to {prev_speed}x")
                     self.settings.save_settings(self) # Save setting

        except Exception as e:
            print(f"Error decreasing speed: {e}")
        return "break" # Prevent default behavior

    def on_stem_key_press(self, event):
        """Handle number key presses (1-9) to toggle stem mute when slider has focus."""
        if not self.eng.current_song:
            return "break" # No song loaded

        try:
            key_num = int(event.keysym) # Get the number pressed (1-9)
            stem_index = key_num - 1 # Convert to 0-based index

            stem_names = self.eng.get_stem_names()

            if 0 <= stem_index < len(stem_names):
                stem_name_to_toggle = stem_names[stem_index]
                self.toggle_stem(stem_name_to_toggle)
                # Status update is handled within toggle_stem
            else:
                # Optional: Provide feedback if the number doesn't correspond to a stem
                # self.sts.set(f"No stem associated with key {key_num}")
                pass

        except ValueError:
            # Should not happen if binding is correct, but good practice
            print(f"Error: Non-numeric key bound to on_stem_key_press: {event.keysym}")
        except Exception as e:
            print(f"Error handling stem key press: {e}")
            self.sts.set("Error toggling stem mute")

        return "break" # Prevent default behavior and further propagation

    def setup_folder_selection(self):
        """Setup the folder selection UI."""
        top = ttk.Frame(self.frm)
        top.pack(fill=tk.X, pady=(0, 0))
        
        ttk.Label(top, text="Songs Folder:").pack(side=tk.LEFT, padx=(0, 5))
        folder_entry = ttk.Entry(top, textvariable=self.fdr, width=50)
        folder_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(top, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)
    
    def setup_transport(self):
        """Setup transport control buttons."""
        # Note: Packing this into self.frm directly, above the PanedWindow
        tpf = ttk.Frame(self.frm)
        tpf.pack(fill=tk.X, pady=(0, 5)) # Adjusted padding

        # Rewind button
        ttk.Button(tpf, text="⏮", command=self.rewind_section_start).pack(side=tk.LEFT, padx=5)
        
        # Play/Pause toggle button
        self.ppb = ttk.Button(tpf, text="▶", command=self.play_pause_toggle)
        self.ppb.pack(side=tk.LEFT, padx=5)
    
        self.time_label = TimeLabel(tpf, self)
        # self.time_label.pack(side=tk.LEFT, padx=5) # Packing handled within TimeLabel's setup_ui

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

    def apply_settings(self):
        app = self
        current_song = self.settings.current_song
        # Read the view range values *already loaded* by load_settings
        # Keep 1.0 as initial fallback for vet before duration is known
        # Use a placeholder like -1 to distinguish missing/default from a valid 1.0
        # Note: load_settings defaults vet to 1.0 if not found in settings.json
        loaded_vst = app.vst.get()
        loaded_vet = app.vet.get()
        # Use the placeholder logic for vet if it's the default 1.0 from load_settings
        saved_vst = loaded_vst
        saved_vet = loaded_vet if loaded_vet > 1.0 else -1.0

        print(f"[Apply Settings] Using loaded view range: vst={saved_vst}, vet={saved_vet}") # DIAGNOSTIC

        if app.dir and os.path.isdir(app.dir):
            app.song_panel.refresh_song_list()
            if current_song in app.song_panel.scb["values"]:
                app.song_panel.scb.set(current_song)
                app.sts.set(f"Selected: {current_song}")
        
        song_loaded_successfully = False
        if app.song_panel.scb.get():
            # Store the intended view range before loading the song
            intended_vst = saved_vst
            intended_vet = saved_vet
            print(f"[Apply Settings] Intended view range before song load: vst={intended_vst}, vet={intended_vet}") # DIAGNOSTIC
            
            app.song_panel.load_selected_song() # This triggers duration update
            song_loaded_successfully = app.eng.current_song is not None
            print(f"[Apply Settings] Song loaded: {song_loaded_successfully}, Current song: {app.eng.current_song.title if app.eng.current_song else 'None'}") # DIAGNOSTIC
            # Update time label explicitly after loading song
            if hasattr(app, 'time_label'):
                app.time_label.update()

        # Apply MIDI settings (unchanged)
        midi_settings = self.settings.midi_settings
        if midi_settings:
            self.midi_settings = midi_settings
            
            # Apply MIDI settings if MIDI panel exists
            if hasattr(app, 'midi_panel'):
                app.midi_panel.midi_device.set(self.midi_settings.get("device", ""))
                app.midi_panel.play_pause_note.set(str(self.midi_settings.get("play_pause_note", 60)))
                app.midi_panel.rewind_note.set(str(self.midi_settings.get("rewind_note", 62)))
                app.midi_panel.next_section_note.set(str(self.midi_settings.get("next_section_note", 64)))
                app.midi_panel.prev_section_note.set(str(self.midi_settings.get("prev_section_note", 65)))
                
                # Apply the mappings
                app.midi_panel.apply_mappings()
                
                # Enable MIDI if it was enabled
                if self.midi_settings.get("enabled", False):
                    app.root.after(1000, app.midi_panel.toggle_midi)  # Delay to ensure UI is ready
        

        # Load section times in mm:ss.c format
        # This must happen after song is loaded so we have valid section data
        if app.eng.current_song:
            section_name = app.snm.get()
            print("Section: " + section_name)

            if section_name == "Full Song":
                start_time = 0.0
                end_time = app.eng.get_total_duration()
            else:
                # Find section with matching name
                for s in app.eng.current_song.sections:
                    if s.name == section_name:
                        start_time = s.start_time
                        end_time = s.end_time
                        break
                else:
                    # Default if section not found
                    print("Section not found: " + section_name)
                    start_time = 0.0
                    end_time = app.eng.get_total_duration()
            
            # Format times for display
            app.pos.set( app.eng.get_current_position() )
            print("Start time (apply settngs): " + str(start_time))
            app.stt.set(SliderTimeUtils.format_time(start_time))
            app.ent.set(SliderTimeUtils.format_time(end_time))

            # Apply the saved/intended view range *after* song duration is known
            # Get duration directly from engine
            total_duration = app.eng.get_total_duration()

            if total_duration > 0:
                 # Clamp intended_vst to valid range
                 final_vst = max(0.0, min(intended_vst, total_duration))
                 
                 # Determine final_vet: Use total_duration if intended_vet is invalid/missing/default placeholder
                 if intended_vet <= final_vst or intended_vet == -1.0:
                     final_vet = total_duration
                     print(f"[Apply Settings] Using total_duration for final_vet: {final_vet}") # DIAGNOSTIC
                 else:
                     # Otherwise, use the intended value, clamped to duration
                     final_vet = max(final_vst + 0.1, min(intended_vet, total_duration))
                     print(f"[Apply Settings] Using intended_vet (clamped) for final_vet: {final_vet}") # DIAGNOSTIC

                 # Ensure vst is strictly less than vet
                 if final_vst >= final_vet:
                     print(f"[Apply Settings] Adjusting final_vst ({final_vst}) because it was >= final_vet ({final_vet})") # DIAGNOSTIC
                     final_vst = max(0.0, final_vet - 0.1)

                 print(f"[Apply Settings] Setting view range (duration > 0): vst={final_vst}, vet={final_vet}") # DIAGNOSTIC
                 self.vst.set(final_vst)
                 self.vet.set(final_vet)
            else: # Fallback if duration is still 0 (song load failed?)
                 print(f"[Apply Settings] Fallback triggered: total_duration <= 0 ({total_duration})") # DIAGNOSTIC
                 # Set a minimal valid range instead of using 1.0
                 final_vst = max(0.0, intended_vst if intended_vst != -1.0 else 0.0) # Use saved vst if valid
                 final_vet = final_vst + 0.1 # Set vet slightly after vst
                 print(f"[Apply Settings] Setting view range (fallback): vst={final_vst}, vet={final_vet}") # DIAGNOSTIC
                 self.vst.set(final_vst)
                 self.vet.set(final_vet)
        else: # DIAGNOSTIC - Added else case for when app.eng.current_song is None
            print(f"[Apply Settings] No current song loaded, cannot set section times or view range based on duration.") # DIAGNOSTIC


        self.update_song_position()
    
    def on_window_resize(self, event):
        """Handle window resize events."""
        if (event.widget == self.root and hasattr(self, 'slider_view')):
            self.slider_view.update_marker_positions()
    
    def on_mute_status_change(self, stem_name, is_muted):
        """Callback for when a stem's mute status changes during playback."""
        print(f"App: Mute status changed for '{stem_name}' to {is_muted}")
        self.slider_view.update_marker_positions()
        # self.stems_panel.update_stem_mute_status(stem_name, is_muted)

    def update_song_position(self):
        """Poll engine position and update UI."""
        if self.eng.is_playing():
            pos = self.eng.get_current_position()
            # total_duration = self.eng.get_total_duration()
            
            # Update position variable using data binding
            self.pos.set(pos)

            # Check if we've hit the end marker for the section
            end_time_str = self.ent.get()
            end_time = SliderTimeUtils.parse_time(end_time_str)
            
            # if pos >= end_time:
            #     if self.lop.get():
            #         # Loop back to start of section
            #         self.eng.pause()
            #         start_time = SliderTimeUtils.parse_time(self.stt.get()) 
            #         self.eng.set_start_position(start_time)
            #         self.play_current()
            #         self.sts.set(f"Looped back to section start")
            #     else:
            #         # Stop playback at end marker
            #         self.eng.pause()
            #         self.set_play_button_text(False)
            #         self.sts.set(f"Reached end of section")
        
        # Schedule next update
        self.root.after(50, self.update_song_position)
    
    def play_pause_toggle(self):
        """Toggle between play and pause."""
        if self.eng.is_playing():
            self.pause_playback()
        else:
            self.play_current()
    
    def is_playing(self):
        """Check if the engine is currently playing."""
        return self.eng.is_playing()

    def play_current(self):
        """Play the current section from the engine's position."""
        if not self.eng.current_song:
            messagebox.showerror("Error", "No song loaded")
            return
        
        self.eng.set_count_in(self.cin.get())

        section_name = self.section_panel.xcb.get()
        if section_name == "Full Song":
            section_name = None
        
        try:
            current_pos = self.eng.get_current_position()
            start_time = SliderTimeUtils.parse_time(self.stt.get())
            end_time = SliderTimeUtils.parse_time(self.ent.get())

            self.eng.set_start_position(start_time)
            self.eng.set_end_position(end_time)

            # Only check lower boundary - we allow playing beyond the end marker
            if current_pos < start_time:
                self.eng.set_position(start_time)
                old_pos = start_time
            else:
                old_pos = current_pos
            
            self.eng.set_loop(self.lop.get())
            # self.eng.set_playback_speed(self.spd.get()) # Engine speed is now set via trace
            self.eng.set_loop_delay(self.dly.get())

            self.eng.play_section()
            
            # Update button
            self.set_play_button_text(True)
            
            # Status message
            if abs(old_pos - start_time) < 0.01:
                disp_sec = section_name or "Full Song"
                self.sts.set(f"Playing: {disp_sec} at {self.spd.get()}x speed")
            else:
                formatted_time = SliderTimeUtils.format_time(old_pos)
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
        start_time = SliderTimeUtils.parse_time(start_time_str)
        was_playing = self.eng.is_playing()
        
        # Stop playback
        self.eng.pause()
        
        # Update engine position
        self.eng.set_position(start_time)
        
        # Update slider position variable
        # This triggers the trace callback which updates the UI
        self.pos.set(start_time)
        
        # Force an update of the marker positions
        self.slider_view.update_marker_positions()
        
        # Resume playback if it was playing
        if was_playing:
            self.play_current()
            formatted_time = SliderTimeUtils.format_time(start_time)
            self.sts.set(f"Rewound and playing from {formatted_time}")
        else:
            formatted_time = SliderTimeUtils.format_time(start_time)
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
            
        current_section = self.snm.get() # Use app.snm directly
        sections = list(self.section_panel.xcb['values'])

        if not sections:
            return
            
        try:
            current_index = sections.index(current_section)
            next_index = (current_index + 1) % len(sections)
            next_section_name = sections[next_index]
            # Set the new section (this triggers on_section_name_write via trace, which saves)
            self.snm.set(next_section_name) 
            self.sts.set(f"Selected section: {next_section_name}")
            # REMOVED: Save the song config - now handled by snm trace
            # self.section_panel.save_song_config() 
        except ValueError:
            # Section not found in list
            if sections:
                first_section_name = sections[0]
                self.snm.set(first_section_name) # Triggers trace/save
                self.sts.set(f"Selected section: {first_section_name}")
    
    def go_to_prev_section(self):
        """Navigate to the previous section in the list."""
        if not hasattr(self, 'section_panel') or not self.eng.current_song:
            return
            
        current_section = self.snm.get() # Use app.snm directly
        sections = list(self.section_panel.xcb['values'])
        
        if not sections:
            return
            
        try:
            current_index = sections.index(current_section)
            prev_index = (current_index - 1) % len(sections)
            prev_section_name = sections[prev_index]
            # Set the new section (this triggers on_section_name_write via trace, which saves)
            self.snm.set(prev_section_name)
            self.sts.set(f"Selected section: {prev_section_name}")
            # REMOVED: Save the song config - now handled by snm trace
            # self.section_panel.save_song_config()
        except ValueError:
            # Section not found in list
            if sections:
                last_section_name = sections[-1]
                self.snm.set(last_section_name) # Triggers trace/save
                self.sts.set(f"Selected section: {last_section_name}")
                # REMOVED: Save the song config
                # self.section_panel.save_song_config()
    
    def on_closing(self):
        """Handle window close."""
        if self.eng.is_playing():
            self.eng.pause()
            
        # Stop MIDI controller if active
        if hasattr(self, 'midi_controller') and self.midi_controller is not None:
            self.midi_controller.stop_midi_listener()
            
        self.settings.save_settings(self)
        self.root.destroy()