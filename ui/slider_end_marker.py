from ui.slider_time_utils import SliderTimeUtils

class EndMarker:
    """Represents and manages the section end marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
        self.app = slider_markers.app

    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the end marker at the specified position."""
        # Calculate actual vertical bounds for stems (or use provided content bounds)
        num_stems = len(self.slider_view.app.eng.stems) if hasattr(self.slider_view.app.eng, 'stems') and self.slider_view.app.eng.stems else 0
        # if num_stems == 0:
        #     return # Don't draw if no stems? Or draw based on content_top/bottom? Let's draw anyway.
            
        # Get label width and ensure x is after label + padding
        label_width = self.slider_view.waveform.LABEL_WIDTH
        waveform_start_x = label_width + 10
        canvas_width = canvas.winfo_width()
        waveform_end_x = canvas_width - 10 # End of waveform area before padding

        x = max(waveform_start_x, x) # Ensure marker starts within waveform area
        x = min(waveform_end_x, x) # Ensure marker ends within waveform area
        
        # Marker properties
        triangle_width = 12
        triangle_height = 10
        
        # Draw end marker line - expand slightly beyond waveform area
        canvas.create_line(
            x, content_top - 5, x, content_bottom + 5, 
            fill="red", width=1, tags="end_marker"
        )
        
        # Draw end marker triangle OUTSIDE the waveform area (above it)
        canvas.create_polygon(
            x - triangle_width / 2, content_top - 5 - triangle_height,
            x + triangle_width / 2, content_top - 5 - triangle_height,
            x, content_top - 5,
            fill="red", tags="end_marker"
        )

    def handle_drag(self, x):
        """Update end time based on drag to x coordinate, respecting view and start marker."""
        # Get view boundaries
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        view_start_x = self.slider_view.time_utils.time_to_x(view_start_time)
        view_end_x = self.slider_view.time_utils.time_to_x(view_end_time)

        # Get start marker position
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        start_x = self.slider_view.time_utils.time_to_x(start_time)
            
        # Clamp x:
        # 1. Must be >= start_x (plus padding)
        x = max(x, start_x + 20) # Keep existing gap logic relative to start marker
        # 2. Must be <= view_end_x (minus a pixel to be safe)
        x = min(x, view_end_x - 1)
        # 3. Must be >= view_start_x (redundant if start_x is within view, but safe)
        x = max(x, view_start_x + 1)

        # Update end time based on clamped x
        new_time = self.slider_view.time_utils.x_to_time(x)

        # Clamp new_time:
        # 1. Must be >= start_time (plus a small delta)
        min_gap = 0.01
        new_time = max(new_time, start_time + min_gap)
        # 2. Must be <= view_end_time
        new_time = min(new_time, view_end_time)
        # 3. Must be >= view_start_time (redundant if start_time is within view, but safe)
        new_time = max(new_time, view_start_time)

        # Update the application's end time variable
        self.app.ent.set(SliderTimeUtils.format_time(new_time))
    
    def handle_release(self):
        """Handle release of end marker after dragging."""
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        # Logic to resume playback was removed, handled elsewhere if needed
        # self.slider_view.app.eng.set_end_position(end_time) # Engine boundary updated via trace on ent

        self.slider_view.app.sts.set(f"Section end: {SliderTimeUtils.format_time(end_time)}")
        # Potentially trigger section save or config update here if desired
        # self.app.section_panel.save_song_config()