from ui.slider_time_utils import SliderTimeUtils

class StartMarker:
    """Represents and manages the section start marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
        self.app = slider_markers.app

    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the start marker at the specified position."""
        # Calculate actual vertical bounds for stems (or use provided content bounds)
        num_stems = len(self.slider_view.app.eng.stems) if hasattr(self.slider_view.app.eng, 'stems') and self.slider_view.app.eng.stems else 0
        # if num_stems == 0:
        #     return # Don't draw if no stems? Or draw based on content_top/bottom? Let's draw anyway.
            
        # Get label width and ensure x is after label + padding
        label_width = self.slider_view.waveform.LABEL_WIDTH
        waveform_start_x = label_width + 10
        x = max(waveform_start_x, x) # Ensure marker starts within waveform area
        
        # Marker properties
        triangle_width = 12
        triangle_height = 10
        
        # Draw start marker line - expand slightly beyond waveform area
        canvas.create_line(
            x, content_top - 5, x, content_bottom + 5, 
            fill="green", width=1, tags="start_marker"
        )
        
        # Draw start marker triangle OUTSIDE the waveform area (above it)
        canvas.create_polygon(
            x - triangle_width / 2, content_top - 5 - triangle_height,
            x + triangle_width / 2, content_top - 5 - triangle_height,
            x, content_top - 5,
            fill="green", tags="start_marker"
        )

    def handle_drag(self, x):
        """Update start time based on drag to x coordinate, respecting view and end marker."""
        # Get view boundaries
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        view_start_x = self.slider_view.time_utils.time_to_x(view_start_time)
        view_end_x = self.slider_view.time_utils.time_to_x(view_end_time)

        # Get end marker position
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        end_x = self.slider_view.time_utils.time_to_x(end_time)
        
        # Clamp x:
        # 1. Must be >= view_start_x (plus a pixel to be safe)
        x = max(view_start_x + 1, x)
        # 2. Must be <= end_x (minus padding)
        x = min(x, end_x - 20) # Keep existing gap logic relative to end marker
        # 3. Must be <= view_end_x (redundant if end_x is already within view, but safe)
        x = min(x, view_end_x -1)

        # Update start time based on clamped x
        new_time = self.slider_view.time_utils.x_to_time(x)

        # Clamp new_time:
        # 1. Must be >= view_start_time
        new_time = max(view_start_time, new_time)
        # 2. Must be <= end_time (minus a small delta)
        min_gap = 0.01
        new_time = min(new_time, end_time - min_gap)
        # 3. Must be <= view_end_time (redundant if end_time is within view, but safe)
        new_time = min(new_time, view_end_time)

        print("Start time (handle drag):", new_time)
        # Update the application's start time variable
        # Use trace=False if direct update causes issues, but usually fine
        self.app.stt.set(SliderTimeUtils.format_time(new_time))

    def handle_release(self):
        """Handle release of start marker after dragging."""
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        
        # Logic to restart playback was removed, handled elsewhere if needed
        # self.slider_view.app.eng.set_start_position(start_time) # Engine boundary updated via trace on stt

        self.slider_view.app.sts.set(f"Section start: {SliderTimeUtils.format_time(start_time)}")
        # Potentially trigger section save or config update here if desired
        # self.app.section_panel.save_song_config()