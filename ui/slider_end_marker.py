from ui.slider_time_utils import SliderTimeUtils

class EndMarker:
    """Represents and manages the section end marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
        self.app = slider_markers.app

    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the end marker at the specified position."""
        # Calculate actual vertical bounds for stems
        num_stems = len(self.slider_view.app.eng.stems) if hasattr(self.slider_view.app.eng, 'stems') else 0
        if num_stems == 0:
            return
            
        # Get label width and ensure x is after label
        label_width = self.slider_view.waveform.LABEL_WIDTH
        x = max(label_width, x)
        
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
            x, content_top - 5,
            x - triangle_width/2, content_top - 5 - triangle_height,
            x + triangle_width/2, content_top - 5 - triangle_height,
            fill="red", outline="black", width=1, tags="end_marker"
        )
    
    def handle_drag(self, x):
        """Update end time based on drag to x coordinate."""
        # Prevent end marker from going before start marker
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        start_x = self.slider_view.time_utils.time_to_x(start_time)
        if x <= start_x + 20:
            x = start_x + 20
            
        # Update end time
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.app.ent.set(SliderTimeUtils.format_time(new_time))
    
    def handle_release(self):
        """Handle release of end marker after dragging."""
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        
        # Resume playback if needed
        # if self.slider_markers.was_playing:
        #     self.slider_view.app.play_current()
        
        self.slider_view.app.sts.set(f"Section end: {SliderTimeUtils.format_time(end_time)}")