"""Marker drawing and interaction handling for the slider view."""

import tkinter as tk

class SliderMarkers:
    """Handles drawing and interaction with markers in the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        
        # State variables for marker dragging
        self.dragging_marker = None
        self.was_playing = False
    
    def update_marker_positions(self):
        """Redraw all markers based on current position and section boundaries."""
        if not hasattr(self.slider_view.app, 'eng') or not self.slider_view.app.eng.current_song:
            return
        
        # Get canvas dimensions
        canvas_width = self.slider_view.canvas.winfo_width()
        canvas_height = self.slider_view.canvas.winfo_height()
        
        if canvas_width <= 1:  # Not yet drawn
            self.slider_view.app.root.update_idletasks()
            canvas_width = self.slider_view.canvas.winfo_width()
            canvas_height = self.slider_view.canvas.winfo_height()
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
        start_time_str = self.slider_view.stt.get()
        end_time_str = self.slider_view.ent.get()
        
        # Parse times (handle both formatted and float values)
        start_time = self.slider_view.time_utils.parse_time(start_time_str) or 0.0
        end_time = self.slider_view.time_utils.parse_time(end_time_str) or self.slider_view.app.eng.get_total_duration()
        
        # Get current position
        current_pos = self.slider_view.pos.get()
        
        # Calculate marker positions
        # Using time_to_x to ensure consistent mapping for all markers
        start_x = self.slider_view.time_utils.time_to_x(start_time)
        end_x = self.slider_view.time_utils.time_to_x(end_time)
        pos_x = self.slider_view.time_utils.time_to_x(current_pos)
        
        # Clear canvas
        self.slider_view.canvas.delete("all")
        
        # 1. Draw background - solid white
        self.slider_view.canvas.create_rectangle(
            0, 0, canvas_width, canvas_height,
            fill="#FFFFFF", outline=""
        )
        
        # 2. Draw background track line
        self.slider_view.canvas.create_line(
            10, canvas_height / 2, 
            canvas_width - 10, canvas_height / 2,
            fill="#dddddd", width=2
        )
        
        # 3. Draw shaded area between start and end markers
        self.slider_view.canvas.create_rectangle(
            start_x, content_top,
            end_x, content_bottom,
            fill="#e6f0ff", outline="", tags="section"
        )
        
        # 4. Draw waveform on top of shaded area
        self.slider_view.waveform.draw_waveform()
        
        # 5. MARKERS - Order matters for overlapping (last drawn = top)
        
        # Draw position marker (black triangle pointing UP from bottom)
        pos_triangle_width = 12
        pos_triangle_height = 10
        
        # Draw position marker line
        self.slider_view.canvas.create_line(
            pos_x, content_top, pos_x, content_bottom, 
            fill="black", width=1, dash=(2, 1), tags="position_marker"
        )
        
        # Draw position marker triangle at BOTTOM
        self.slider_view.canvas.create_polygon(
            pos_x, content_bottom,
            pos_x - pos_triangle_width/2, content_bottom + pos_triangle_height,
            pos_x + pos_triangle_width/2, content_bottom + pos_triangle_height,
            fill="black", outline="black", width=1, tags="position_marker"
        )
        
        # Draw start marker (green triangle pointing DOWN from top)
        self.slider_view.canvas.create_line(
            start_x, content_top, start_x, content_bottom, 
            fill="green", width=1, tags="start_marker"
        )
        
        self.slider_view.canvas.create_polygon(
            start_x, content_top,
            start_x - triangle_width/2, content_top - triangle_height,
            start_x + triangle_width/2, content_top - triangle_height,
            fill="green", outline="black", width=1, tags="start_marker"
        )
        
        # Draw end marker (red triangle pointing DOWN from top)
        self.slider_view.canvas.create_line(
            end_x, content_top, end_x, content_bottom, 
            fill="red", width=1, tags="end_marker"
        )
        
        self.slider_view.canvas.create_polygon(
            end_x, content_top,
            end_x - triangle_width/2, content_top - triangle_height,
            end_x + triangle_width/2, content_top - triangle_height,
            fill="red", outline="black", width=1, tags="end_marker"
        )
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas to select marker or set position."""
        # Check Y position to determine which marker to select
        canvas_height = self.slider_view.canvas.winfo_height()
        
        # Store the playback state to restore after dragging
        self.was_playing = hasattr(self.slider_view.app, 'eng') and self.slider_view.app.eng.is_playing()
        
        # Define Y ranges for different markers
        top_region = 15  # Top area for start/end markers
        bottom_region = canvas_height - 15  # Bottom area for position marker
        
        # Items under cursor
        items = self.slider_view.canvas.find_closest(event.x, event.y)
        
        # Y-coordinate based selection
        if event.y < top_region:
            # Top region - check for start/end markers
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "start_marker" in tags:
                    self.dragging_marker = "start"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
        
        elif event.y > bottom_region:
            # Bottom region - check for position marker
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
        
        else:
            # Mid region - check all markers but with priority
            # First check for click on a marker line
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
                elif "start_marker" in tags:
                    self.dragging_marker = "start"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    # Pause playback if playing
                    if self.was_playing:
                        self.slider_view.app.eng.pause()
                    return
        
        # If we get here, user clicked on empty space - set position directly
        # Also pause if playing
        if self.was_playing:
            self.slider_view.app.eng.pause()
        self.slider_view.time_utils.update_position_from_x(event.x)
    
    def on_canvas_drag(self, event):
        """Handle drag motion on canvas."""
        if not self.dragging_marker:
            return
        
        # Constrain x to canvas bounds
        canvas_width = self.slider_view.canvas.winfo_width()
        x = max(10, min(event.x, canvas_width - 10))
        
        if self.dragging_marker == "start":
            # Prevent start marker from going past end marker
            end_time = self.slider_view.time_utils.parse_time(self.slider_view.ent.get())
            end_x = self.slider_view.time_utils.time_to_x(end_time)
            if x >= end_x - 15:
                x = end_x - 15
            
            # Update start time
            new_time = self.slider_view.time_utils.x_to_time(x)
            self.slider_view.stt.set(self.slider_view.time_utils.format_time(new_time))
            
        elif self.dragging_marker == "end":
            # Prevent end marker from going before start marker
            start_time = self.slider_view.time_utils.parse_time(self.slider_view.stt.get())
            start_x = self.slider_view.time_utils.time_to_x(start_time)
            if x <= start_x + 15:
                x = start_x + 15
                
            # Update end time
            new_time = self.slider_view.time_utils.x_to_time(x)
            self.slider_view.ent.set(self.slider_view.time_utils.format_time(new_time))
            
        elif self.dragging_marker == "position":
            # Update position time
            new_time = self.slider_view.time_utils.x_to_time(x)
            self.slider_view.pos.set(new_time)
            
        # Redraw markers
        self.update_marker_positions()
    
    def on_canvas_release(self, event):
        """Handle release of mouse button after dragging."""
        if not self.dragging_marker:
            return
        
        if self.dragging_marker == "position":
            # When position marker is released, update the engine position
            new_pos = self.slider_view.pos.get()
            
            # Update engine position
            self.slider_view.app.eng.set_start_position(new_pos)
            
            # Resume playback if it was playing before
            if hasattr(self, 'was_playing') and self.was_playing:
                self.slider_view.app.play_current()
                self.slider_view.app.sts.set(f"Playback at {self.slider_view.time_utils.format_time(new_pos)}")
            else:
                self.slider_view.app.sts.set(f"Position: {self.slider_view.time_utils.format_time(new_pos)}")
        
        elif self.dragging_marker == "start":
            # Check if current position is now before section start
            start_time = self.slider_view.time_utils.parse_time(self.slider_view.stt.get())
            current_pos = self.slider_view.app.eng.get_current_position()
            
            if hasattr(self, 'was_playing') and self.was_playing:
                # Restart playback from new section start
                self.slider_view.app.eng.set_start_position(start_time)
                self.slider_view.app.play_current()
                self.slider_view.app.sts.set(f"Restarted playback from new start: {self.slider_view.time_utils.format_time(start_time)}")
            else:
                self.slider_view.app.sts.set(f"Section start: {self.slider_view.time_utils.format_time(start_time)}")
                
        elif self.dragging_marker == "end":
            end_time = self.slider_view.time_utils.parse_time(self.slider_view.ent.get())
            # Resume playback if needed
            if hasattr(self, 'was_playing') and self.was_playing:
                self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Section end: {self.slider_view.time_utils.format_time(end_time)}")
        
        # Clear dragging state
        self.dragging_marker = None
        if hasattr(self, 'was_playing'):
            delattr(self, 'was_playing')