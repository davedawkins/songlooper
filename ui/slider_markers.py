"""Marker drawing and interaction handling for the slider view."""

import tkinter as tk

from ui.slider_start_marker import StartMarker
from ui.slider_end_marker import EndMarker
from ui.slider_position_marker import PositionMarker
from ui.slider_canvas_manager import CanvasManager
from ui.slider_marker_interaction_manager import MarkerInteractionManager
from ui.slider_time_utils import SliderTimeUtils


class SliderMarkers:
    """Handles drawing and interaction with markers in the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        self.app = slider_view.app

        # State variables for marker dragging
        self.dragging_marker = None
        self.was_playing = False
        
        # Create component instances
        self.position_marker = PositionMarker(self)
        self.start_marker = StartMarker(self)
        self.end_marker = EndMarker(self)
        self.canvas_manager = CanvasManager(self)
        self.interaction_manager = MarkerInteractionManager(self)
    
    def get_stem_vertical_bounds(self):
        """Get the actual vertical bounds of the stem waveforms."""
        # Get stem count (if stems are available)
        if not hasattr(self.slider_view.app, 'eng') or not self.slider_view.app.eng.stems:
            return (0, 0)  # Default if no stems
        
        num_stems = len(self.slider_view.app.eng.stems)
        if num_stems == 0:
            return (0, 0)  # Default if no stems
        
        # Calculate first and last stem positions the same way as in draw_waveform
        canvas_height = self.slider_view.canvas.winfo_height()
        top_margin = self.slider_view.waveform.TOP_MARGIN
        bottom_margin = self.slider_view.waveform.BOTTOM_MARGIN
        stem_spacing = self.slider_view.waveform.STEM_SPACING
        
        available_height = canvas_height - top_margin - bottom_margin
        stem_height = max(30, int((available_height - (stem_spacing * (num_stems - 1))) / num_stems))
        
        # Calculate top of first stem and bottom of last stem
        first_stem_top = top_margin
        last_stem_bottom = top_margin + num_stems * stem_height + (num_stems - 1) * stem_spacing
        
        return (first_stem_top, last_stem_bottom)
    
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
        
        # Get actual vertical bounds of the stem waveforms
        content_top, content_bottom = self.get_stem_vertical_bounds()
        
        # Fetch and parse current time values
        start_time_str = self.app.stt.get()
        end_time_str = self.app.ent.get()
        start_time = SliderTimeUtils.parse_time(start_time_str) or 0.0
        end_time = SliderTimeUtils.parse_time(end_time_str) or self.slider_view.app.eng.get_total_duration()
        current_pos = self.app.pos.get()
            
        # Calculate marker positions
        start_x = self.slider_view.time_utils.time_to_x(start_time)
        end_x = self.slider_view.time_utils.time_to_x(end_time)
        pos_x = self.slider_view.time_utils.time_to_x(current_pos)
        
        # Clear all elements to start fresh
        self.slider_view.canvas.delete("start_marker")
        self.slider_view.canvas.delete("end_marker")
        self.slider_view.canvas.delete("position_marker")
        self.slider_view.canvas.delete("section")
        
        # Prepare canvas
        self.canvas_manager.prepare_canvas(self.slider_view.canvas, canvas_width, canvas_height)
        
        # Draw section background first (lowest layer)
        self.canvas_manager.draw_section_background(
            self.slider_view.canvas, start_x, end_x, content_top, content_bottom
        )
        
        # Draw waveform on top of section background
        self.slider_view.waveform.draw_waveform()
        
        # Draw markers last (top layer)
        self.position_marker.draw(self.slider_view.canvas, pos_x, content_top, content_bottom)
        self.start_marker.draw(self.slider_view.canvas, start_x, content_top, content_bottom)
        self.end_marker.draw(self.slider_view.canvas, end_x, content_top, content_bottom)
                
    def on_canvas_click(self, event):
        """Handle mouse click on canvas to select marker or set position."""
        # Ignore clicks in the label area
        label_width = self.slider_view.waveform.LABEL_WIDTH
        if event.x <= label_width:
            return
            
        # Store the playback state to restore after dragging
        self.was_playing = hasattr(self.slider_view.app, 'eng') and self.slider_view.app.eng.is_playing()
        
        # Determine what was clicked
        marker_type = self.interaction_manager.get_marker_at_position(event)
        
        if marker_type:
            # A marker was clicked
            self.dragging_marker = marker_type
            
            # Pause playback if playing
            if self.was_playing and marker_type == "position":
                self.slider_view.app.eng.pause()
        else:
            # Empty space was clicked - set position directly
            if self.was_playing:
                self.slider_view.app.eng.pause()
            SliderTimeUtils.update_position_from_x(event.x)
    
    def on_canvas_drag(self, event):
        """Handle drag motion on canvas."""
        if not self.dragging_marker:
            return
        
        # Constrain x to canvas bounds
        x = self.interaction_manager.constrain_x_to_canvas(event.x)
        
        # Delegate to the appropriate marker handler
        if self.dragging_marker == "position":
            self.position_marker.handle_drag(x)
        elif self.dragging_marker == "start":
            self.start_marker.handle_drag(x)
        elif self.dragging_marker == "end":
            self.end_marker.handle_drag(x)
        
        # Redraw markers
        self.update_marker_positions()
    
    def on_canvas_release(self, event):
        """Handle release of mouse button after dragging."""
        if not self.dragging_marker:
            return
        
        # Delegate to the appropriate marker handler
        if self.dragging_marker == "position":
            self.position_marker.handle_release()
        elif self.dragging_marker == "start":
            self.start_marker.handle_release()
        elif self.dragging_marker == "end":
            self.end_marker.handle_release()
        
        # Clear dragging state
        self.dragging_marker = None