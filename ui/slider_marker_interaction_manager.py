class MarkerInteractionManager:
    """Manages interactions with markers through mouse events."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def get_marker_at_position(self, event):
        """Determine which marker (if any) was clicked."""
        # Check Y position to determine which marker to select
        canvas_height = self.slider_view.canvas.winfo_height()
        
        # Define Y ranges for different markers
        top_region = 50  # Top area for start/end markers
        bottom_region = canvas_height - 50  # Bottom area for position marker
        
        # Get label width
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        # Ignore clicks in the label area
        if event.x <= label_width:
            return None
        
        # Items under cursor
        items = self.slider_view.canvas.find_closest(event.x, event.y)
        
        # Y-coordinate based selection
        if event.y < top_region:
            # Top region - check for start/end markers
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "start_marker" in tags:
                    return "start"
                elif "end_marker" in tags:
                    return "end"
        
        elif event.y > bottom_region:
            # Bottom region - check for position marker
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "position_marker" in tags:
                    return "position"
        
        else:
            # Mid region - check for marker lines that span through all stems
            for item in items:
                tags = self.slider_view.canvas.gettags(item)
                if "position_marker" in tags:
                    return "position"
                elif "start_marker" in tags:
                    return "start"
                elif "end_marker" in tags:
                    return "end"
        
        # If no marker was clicked, return None to indicate clicking on empty space
        return None
    
    def constrain_x_to_canvas(self, x):
        """Constrain x coordinate to valid canvas range."""
        # Account for stem labels width
        canvas_width = self.slider_view.canvas.winfo_width()
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        return max(label_width + 10, min(x, canvas_width - 10))