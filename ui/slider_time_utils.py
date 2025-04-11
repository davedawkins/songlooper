"""Utility functions for time handling and conversions in the slider view."""

import tkinter as tk
import re

class SliderTimeUtils:
    """Handles time formatting, parsing, and coordinate conversions for the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        self.app = slider_view.app
        
    @staticmethod
    def format_time(seconds):
        """Format time in mm:ss.xxx format."""
        if seconds is None or seconds < 0:
            seconds = 0
        minutes, sec_frac = divmod(seconds, 60)
        sec = int(sec_frac)
        msec = int((sec_frac - sec) * 1000)  # 3 decimal places for milliseconds
        return f"{int(minutes):02d}:{sec:02d}.{msec:03d}"

    @staticmethod
    def parse_time(time_str):
        """Parse time from either mm:ss.xxx format or float seconds."""
        if isinstance(time_str, (int, float)):
            return float(time_str) # Already a number
            
        if not isinstance(time_str, str):
            return None # Invalid input type

        time_str = time_str.strip()
        
        # Try parsing mm:ss.xxx format
        match = re.match(r"(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?$", time_str)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            msec_str = match.group(3)
            msec = int(msec_str.ljust(3, '0')) if msec_str else 0 # Pad milliseconds if needed
            
            total_seconds = minutes * 60 + seconds + msec / 1000.0
            return total_seconds
            
        # Try parsing as float seconds
        try:
            total_seconds = float(time_str)
            return total_seconds
        except ValueError:
            return None # Failed to parse in any known format

    # def update_time_label(self, current, total):
    #     """Update the time display label with format mm:ss.c."""
    #     time_text = f"{SliderTimeUtils.format_time(current)} / {SliderTimeUtils.format_time(total)}"
    #     self.slider_view.time_label.config(text=time_text)
    
    def time_to_x(self, time):
        """Convert time value to x coordinate based on current view range."""
        canvas_width = self.slider_view.canvas.winfo_width()
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        # Get current view range
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        view_range = max(0.1, view_end_time - view_start_time) # Avoid division by zero
        
        # Calculate position ratio within the view range
        # Clamp time to be within the view range for calculation
        clamped_time = max(view_start_time, min(time, view_end_time))
        position_ratio = (clamped_time - view_start_time) / view_range
        position_ratio = max(0, min(1, position_ratio)) # Ensure ratio is between 0 and 1
        
        # Scale to usable waveform area (after label width, with padding)
        usable_width = max(1, canvas_width - label_width - 20) # 10px padding on each side
        x_coordinate = label_width + 10 + position_ratio * usable_width
        
        # Ensure x is not less than the start of the waveform area
        return max(label_width + 10, x_coordinate)

    def x_to_time(self, x):
        """Convert x coordinate to time value based on current view range."""
        canvas_width = self.slider_view.canvas.winfo_width()
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        # Define the usable area for the waveform
        waveform_start_x = label_width + 10
        waveform_end_x = canvas_width - 10
        usable_width = max(1, waveform_end_x - waveform_start_x)
        
        # Clamp x coordinate to be within the usable waveform area
        clamped_x = max(waveform_start_x, min(x, waveform_end_x))
        
        # Calculate position ratio within the usable area
        position_ratio = (clamped_x - waveform_start_x) / usable_width
        position_ratio = max(0, min(1, position_ratio)) # Ensure ratio is between 0 and 1
        
        # Get current view range
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        view_range = max(0.1, view_end_time - view_start_time)
        
        # Calculate time based on the ratio within the view range
        time_value = view_start_time + position_ratio * view_range
        
        # Clamp time to be strictly within the view boundaries
        return max(view_start_time, min(time_value, view_end_time))

    def update_position_from_x(self, x):
        """Update playback position based on click/drag x coordinate."""
        if not self.slider_view.app.eng.current_song:
            return
            
        # Only consider clicks within the waveform area (after label)
        label_width = self.slider_view.waveform.LABEL_WIDTH
        waveform_start_x = label_width + 10
        if x < waveform_start_x:
            return # Click was in the label area or padding
            
        # Calculate time at this x position based on current view
        new_pos = self.x_to_time(x)
        
        # Clamp new_pos to be within the current view range (should be handled by x_to_time, but double-check)
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        new_pos = max(view_start_time, min(new_pos, view_end_time))

        # Update engine position
        was_playing = self.slider_view.app.eng.is_playing()
        if was_playing:
            self.slider_view.app.eng.pause()
        
        print("update_position_from_x: Setting engine position: " + str(new_pos))
        self.slider_view.app.eng.set_position(new_pos)
        
        # Update position variable - triggers UI update through trace
        self.app.pos.set(new_pos)
        
        # Resume playback if needed
        if was_playing:
            # Make sure playback respects current section boundaries if looping
            section_start = SliderTimeUtils.parse_time(self.app.stt.get())
            section_end = SliderTimeUtils.parse_time(self.app.ent.get())
            
            # If the new position is outside the current section, adjust before playing
            if new_pos < section_start or new_pos > section_end:
                 # If looping, maybe jump to section start? Or just play from new_pos?
                 # Current behavior: play from new_pos, loop will handle wrapping if needed.
                 # If not looping, playback will stop at section_end anyway.
                 pass # Keep new_pos

            self.slider_view.app.play_current()
            self.app.sts.set(f"Jumped to {self.format_time(new_pos)}")
        else:
             self.app.sts.set(f"Position set to {self.format_time(new_pos)}")