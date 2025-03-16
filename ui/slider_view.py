import tkinter as tk
from tkinter import ttk
import numpy as np

class SliderView(ttk.Frame):
    """Slider with markers for time navigation and section boundaries."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        
        # Get references to app variables
        self.stt = app.stt  # Start time
        self.ent = app.ent  # End time
        self.svm = app.svm  # Section view mode
        
        # Position tracking
        self.pos = tk.DoubleVar(value=0)
        # Add trace to position variable for data binding
        self.pos.trace_add("write", self.on_position_changed)
        
        # Marker tracking
        self.dragging_marker = None
        self.was_playing = False
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the slider view UI."""
        # Time label
        self.time_label = ttk.Label(self, text="00:00.0 / 00:00.0", width=20)
        self.time_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Slider canvas frame
        self.slider_frame = ttk.Frame(self)
        self.slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Canvas for markers with doubled height and white background
        self.canvas = tk.Canvas(self.slider_frame, height=60, bg="#FFFFFF", highlightthickness=0)
        self.canvas.pack(fill=tk.X, expand=True)
        
        # Add canvas bindings
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def on_position_changed(self, *args):
        """Called when the position variable changes, updates the UI."""
        if hasattr(self.app, 'eng') and self.app.eng.current_song:
            self.update_time_label(self.pos.get(), self.app.eng.get_total_duration())
            
        # Only update marker positions if not dragging to avoid conflicts
        if not self.dragging_marker:
            self.update_marker_positions()
    
    def update_time_label(self, current, total):
        """Update the time display label with format mm:ss.c."""
        time_text = f"{self.format_time(current)} / {self.format_time(total)}"
        self.time_label.config(text=time_text)
    
    def format_time(self, seconds):
        """Format time in mm:ss.c format."""
        minutes, sec_frac = divmod(seconds, 60)
        sec = int(sec_frac)
        decisec = int((sec_frac - sec) * 10)  # Only one decimal place
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
                return None
        else:
            try:
                # Parse as raw seconds
                return float(time_str)
            except ValueError:
                return None

    def draw_waveform(self):
        """Draw a waveform representation in the slider background."""
        if not hasattr(self.app, 'eng') or not self.app.eng.current_song or not self.app.eng.stems:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1:  # Canvas not yet drawn
            return
        
        # Clear previous waveform
        self.canvas.delete("waveform")
        
        # Calculate center line (y-position)
        center_y = canvas_height / 2
        
        # Create buffers to store waveform data
        waveform_data = None
        total_stems = 0
        
        # Combine all non-muted stems
        for stem_name, audio_data in self.app.eng.stems.items():
            if stem_name in self.app.eng.muted_stems:
                continue
                
            # Only use first channel for visualization
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]
                
            if waveform_data is None:
                waveform_data = np.abs(audio_data.copy())
            else:
                # Make sure lengths match
                min_len = min(len(waveform_data), len(audio_data))
                waveform_data = waveform_data[:min_len] + np.abs(audio_data[:min_len])
            
            total_stems += 1
        
        if waveform_data is None or total_stems == 0:
            return
        
        # Normalize to prevent stack overflow by dividing by number of stems
        if total_stems > 0:
            waveform_data = waveform_data / total_stems
        
        # Determine number of samples per pixel for better performance
        total_samples = len(waveform_data)
        
        # Determine visible range based on section view mode
        if self.svm.get():
            # In section view, only show the section part of the waveform
            start_time = self.parse_time(self.stt.get())
            end_time = self.parse_time(self.ent.get())
            
            if start_time is None or end_time is None:
                return
                
            start_sample = int(start_time * self.app.eng.stem_srs)
            end_sample = int(end_time * self.app.eng.stem_srs)
            
            # Ensure valid range
            start_sample = max(0, min(start_sample, total_samples - 1))
            end_sample = max(start_sample + 1, min(end_sample, total_samples))
            
            waveform_data = waveform_data[start_sample:end_sample]
            visible_samples = end_sample - start_sample
        else:
            # In full view, show the entire waveform
            visible_samples = total_samples
        
        # Limit the number of points we draw to improve performance
        # Aim for at most 2 points per horizontal pixel to avoid overdrawing
        samples_per_pixel = max(1, visible_samples // (canvas_width - 20))
        
        # Process the waveform data to generate points efficiently
        points = []
        
        # Track the max amplitude for normalization
        max_amp = np.max(waveform_data) if len(waveform_data) > 0 else 1.0
        if max_amp < 0.001:  # Avoid division by near-zero
            max_amp = 1.0
        
        # Calculate amplitude scale (40% of canvas height)
        amp_scale = canvas_height * 0.4
        
        # Efficient algorithm to convert waveform to display points
        # Process in chunks for better performance
        num_chunks = min(canvas_width - 20, 1000)  # Cap at 1000 points for performance
        chunk_size = max(1, visible_samples // num_chunks)
        
        for i in range(num_chunks):
            chunk_start = i * chunk_size
            chunk_end = min(visible_samples, (i + 1) * chunk_size)
            
            if chunk_start >= len(waveform_data):
                break
                
            # Get maximum amplitude in this chunk for peak visualization
            chunk_data = waveform_data[chunk_start:chunk_end]
            if len(chunk_data) == 0:
                continue
                
            peak = np.max(chunk_data)
            
            # Normalize and scale
            peak_scaled = (peak / max_amp) * amp_scale
            
            # Calculate x position
            x_pos = 10 + int((i / num_chunks) * (canvas_width - 20))
            
            # Add line from center to peak and center to -peak
            points.append((x_pos, center_y - peak_scaled, x_pos, center_y + peak_scaled))
        
        # Draw waveform lines
        for x1, y1, x2, y2 in points:
            self.canvas.create_line(
                x1, y1, x2, y2, 
                fill="#8080ff", 
                width=1, 
                tags="waveform"
            )

    def update_marker_positions(self):
        """Redraw all markers based on current position and section boundaries."""
        if not hasattr(self.app, 'eng') or not self.app.eng.current_song:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1:  # Not yet drawn
            self.app.root.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width <= 1:  # Still not ready
                return
        
        # Define constants for marker drawing
        triangle_width = 10
        triangle_height = 8
        margin = triangle_height + 2
        
        # Content area
        content_top = margin
        content_bottom = canvas_height - margin
        
        # Fetch current time values
        start_time_str = self.stt.get()
        end_time_str = self.ent.get()
        
        # Parse times (handle both formatted and float values)
        start_time = self.parse_time(start_time_str) or 0.0
        end_time = self.parse_time(end_time_str) or self.app.eng.get_total_duration()
        
        # Get current position
        current_pos = self.pos.get()
        
        # Calculate marker positions
        # Using time_to_x to ensure consistent mapping for all markers
        start_x = self.time_to_x(start_time)
        end_x = self.time_to_x(end_time)
        pos_x = self.time_to_x(current_pos)
        
        # Clear canvas
        self.canvas.delete("all")
        
        # 1. Draw background - solid white
        self.canvas.create_rectangle(
            0, 0, canvas_width, canvas_height,
            fill="#FFFFFF", outline=""
        )
        
        # 2. Draw background track line
        self.canvas.create_line(
            10, canvas_height / 2, 
            canvas_width - 10, canvas_height / 2,
            fill="#dddddd", width=2
        )
        
        # 3. Draw shaded area between start and end markers
        self.canvas.create_rectangle(
            start_x, content_top,
            end_x, content_bottom,
            fill="#e6f0ff", outline="", tags="section"
        )
        
        # 4. Draw waveform on top of shaded area
        self.draw_waveform()
        
        # 5. MARKERS - Order matters for overlapping (last drawn = top)
        
        # Draw position marker (black triangle pointing UP from bottom)
        pos_triangle_width = 12
        pos_triangle_height = 10
        
        # Draw position marker line
        self.canvas.create_line(
            pos_x, content_top, pos_x, content_bottom, 
            fill="black", width=1, dash=(2, 1), tags="position_marker"
        )
        
        # Draw position marker triangle at BOTTOM
        self.canvas.create_polygon(
            pos_x, content_bottom,
            pos_x - pos_triangle_width/2, content_bottom + pos_triangle_height,
            pos_x + pos_triangle_width/2, content_bottom + pos_triangle_height,
            fill="black", outline="black", width=1, tags="position_marker"
        )
        
        # Draw start marker (green triangle pointing DOWN from top)
        self.canvas.create_line(
            start_x, content_top, start_x, content_bottom, 
            fill="green", width=1, tags="start_marker"
        )
        
        self.canvas.create_polygon(
            start_x, content_top,
            start_x - triangle_width/2, content_top - triangle_height,
            start_x + triangle_width/2, content_top - triangle_height,
            fill="green", outline="black", width=1, tags="start_marker"
        )
        
        # Draw end marker (red triangle pointing DOWN from top)
        self.canvas.create_line(
            end_x, content_top, end_x, content_bottom, 
            fill="red", width=1, tags="end_marker"
        )
        
        self.canvas.create_polygon(
            end_x, content_top,
            end_x - triangle_width/2, content_top - triangle_height,
            end_x + triangle_width/2, content_top - triangle_height,
            fill="red", outline="black", width=1, tags="end_marker"
        )

    def update_position_from_x(self, x):
        """Update position based on x coordinate."""
        if not self.app.eng.current_song:
            return
            
        # Calculate time at this x position
        new_pos = self.x_to_time(x)
        
        # Update engine position
        was_playing = self.app.eng.is_playing()
        if was_playing:
            self.app.eng.stop()
        
        self.app.eng.set_start_position(new_pos)
        
        # Update position variable - triggers UI update through trace
        self.pos.set(new_pos)
        
        # Resume playback if needed
        if was_playing:
            self.app.play_current()
            self.app.sts.set(f"Position: {self.format_time(new_pos)}")
        else:
            self.app.sts.set(f"Position: {self.format_time(new_pos)}")

    def x_to_time(self, x):
        """Convert x coordinate to time value."""
        canvas_width = self.canvas.winfo_width()
        
        if self.svm.get():
            # Section view
            start_time = self.parse_time(self.stt.get())
            end_time = self.parse_time(self.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            # Adjust for the padding (10px on each side)
            usable_width = max(1, canvas_width - 20)
            position_ratio = max(0, min(1, (x - 10) / usable_width))
            return start_time + position_ratio * section_range
        else:
            # Full song view
            total_duration = max(0.1, self.app.eng.get_total_duration())
            
            # Adjust for the padding (10px on each side)
            usable_width = max(1, canvas_width - 20)
            position_ratio = max(0, min(1, (x - 10) / usable_width))
            return position_ratio * total_duration

    def time_to_x(self, time):
        """Convert time value to x coordinate."""
        canvas_width = self.canvas.winfo_width()
        
        if self.svm.get():
            # Section view
            start_time = self.parse_time(self.stt.get())
            end_time = self.parse_time(self.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            position_ratio = (time - start_time) / section_range
            position_ratio = max(0, min(1, position_ratio))
            # Add the left margin (10px)
            return 10 + position_ratio * (canvas_width - 20)
        else:
            # Full song view
            total_duration = max(0.1, self.app.eng.get_total_duration())
            
            position_ratio = time / total_duration
            position_ratio = max(0, min(1, position_ratio))
            # Add the left margin (10px)
            return 10 + position_ratio * (canvas_width - 20)
            
    def on_canvas_click(self, event):
        """Handle mouse click on canvas to select marker or set position."""
        print("Clicked")
        # Check Y position to determine which marker to select
        canvas_height = self.canvas.winfo_height()
        
        # Store the playback state to restore after dragging
        self.was_playing = hasattr(self.app, 'eng') and self.app.eng.is_playing()
        
        # Define Y ranges for different markers
        top_region = 15  # Top area for start/end markers
        bottom_region = canvas_height - 15  # Bottom area for position marker
        
        # Items under cursor
        items = self.canvas.find_closest(event.x, event.y)
        
        # Y-coordinate based selection
        if event.y < top_region:
            # Top region - check for start/end markers
            for item in items:
                tags = self.canvas.gettags(item)
                if "start_marker" in tags:
                    self.dragging_marker = "start"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
        
        elif event.y > bottom_region:
            # Bottom region - check for position marker
            for item in items:
                tags = self.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
        
        else:
            # Mid region - check all markers but with priority
            # First check for click on a marker line
            for item in items:
                tags = self.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
                elif "start_marker" in tags:
                    self.dragging_marker = "start"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    # Pause playback if playing
                    if self.was_playing:
                        self.app.eng.pause()
                    return
        
        # If we get here, user clicked on empty space - set position directly
        # Also pause if playing
        if self.was_playing:
            self.app.eng.pause()
        self.update_position_from_x(event.x)

    def on_canvas_drag(self, event):
        """Handle drag motion on canvas."""
        if not self.dragging_marker:
            return
        
        # Constrain x to canvas bounds
        canvas_width = self.canvas.winfo_width()
        x = max(10, min(event.x, canvas_width - 10))
        
        if self.dragging_marker == "start":
            # Prevent start marker from going past end marker
            end_time = self.parse_time(self.ent.get())
            end_x = self.time_to_x(end_time)
            if x >= end_x - 15:
                x = end_x - 15
            
            # Update start time
            new_time = self.x_to_time(x)
            self.stt.set(self.format_time(new_time))
            
        elif self.dragging_marker == "end":
            # Prevent end marker from going before start marker
            start_time = self.parse_time(self.stt.get())
            start_x = self.time_to_x(start_time)
            if x <= start_x + 15:
                x = start_x + 15
                
            # Update end time
            new_time = self.x_to_time(x)
            self.ent.set(self.format_time(new_time))
            
        elif self.dragging_marker == "position":
            # Update position time
            new_time = self.x_to_time(x)
            self.pos.set(new_time)
            
        # Redraw markers
        self.update_marker_positions()

    def on_canvas_release(self, event):
        """Handle release of mouse button after dragging."""
        if not self.dragging_marker:
            return
        
        if self.dragging_marker == "position":
            # When position marker is released, update the engine position
            new_pos = self.pos.get()
            
            # Update engine position
            self.app.eng.set_start_position(new_pos)
            
            # Resume playback if it was playing before
            if hasattr(self, 'was_playing') and self.was_playing:
                self.app.play_current()
                self.app.sts.set(f"Playback at {self.format_time(new_pos)}")
            else:
                self.app.sts.set(f"Position: {self.format_time(new_pos)}")
        
        elif self.dragging_marker == "start":
            # Check if current position is now before section start
            start_time = self.parse_time(self.stt.get())
            current_pos = self.app.eng.get_current_position()
            
            if hasattr(self, 'was_playing') and self.was_playing:
                # Restart playback from new section start
                self.app.eng.set_start_position(start_time)
                self.app.play_current()
                self.app.sts.set(f"Restarted playback from new start: {self.format_time(start_time)}")
            else:
                self.app.sts.set(f"Section start: {self.format_time(start_time)}")
                
        elif self.dragging_marker == "end":
            end_time = self.parse_time(self.ent.get())
            # Resume playback if needed
            if hasattr(self, 'was_playing') and self.was_playing:
                self.app.play_current()
            self.app.sts.set(f"Section end: {self.format_time(end_time)}")
        
        # Clear dragging state
        self.dragging_marker = None
        if hasattr(self, 'was_playing'):
            delattr(self, 'was_playing')