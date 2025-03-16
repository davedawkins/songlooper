from ui.slider_time_utils import SliderTimeUtils

class StartMarker:
    """Represents and manages the section start marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the start marker at the specified position."""
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
        
        # Draw start marker line - expand slightly beyond waveform area
        canvas.create_line(
            x, content_top - 5, x, content_bottom + 5, 
            fill="green", width=1, tags="start_marker"
        )
        
        # Draw start marker triangle OUTSIDE the waveform area (above it)
        canvas.create_polygon(
            x, content_top - 5,
            x - triangle_width/2, content_top - 5 - triangle_height,
            x + triangle_width/2, content_top - 5 - triangle_height,
            fill="green", outline="black", width=1, tags="start_marker"
        )
    
    def handle_drag(self, x):
        """Update start time based on drag to x coordinate."""
        # Prevent start marker from going past end marker
        end_time = SliderTimeUtils.parse_time(self.app.ent.get())
        end_x = self.slider_view.time_utils.time_to_x(end_time)
        if x >= end_x - 20:
            x = end_x - 20
        
        # Update start time
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.app.stt.set(SliderTimeUtils.format_time(new_time))
    
    def handle_release(self):
        """Handle release of start marker after dragging."""
        start_time = SliderTimeUtils.parse_time(self.app.stt.get())
        
        if self.slider_markers.was_playing:
            # Restart playback from new section start
            self.slider_view.app.eng.set_start_position(start_time)
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Restarted playback from new start: {SliderTimeUtils.format_time(start_time)}")
        else:
            self.slider_view.app.sts.set(f"Section start: {SliderTimeUtils.format_time(start_time)}")