"""Waveform drawing functionality for the slider view with individual stem displays."""

import numpy as np
from ui.slider_time_utils import SliderTimeUtils
import re


def short_name(text):
    parts = re.split(r"[ _-]+", text)
    return parts[len(parts)-1] if len(parts) > 1 else text

class SliderWaveform:
    """Handles drawing and rendering of individual audio waveforms for each stem in the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        self.app = slider_view.app
        
        # Constants for layout
        self.LABEL_WIDTH = 180
        self.TOP_MARGIN = 50
        self.BOTTOM_MARGIN = 50
        self.STEM_SPACING = 15
        self._waveform_cache = {}
        self.stem_names = [] # Keep track of drawn stem names for hit testing
        self.stem_height = 0 # Keep track of calculated stem height
    
    def invalidate_cache(self):
        """Clear the waveform cache. Should be called when stems or the song changes."""
        self._waveform_cache.clear()
        self.stem_names = []
        self.stem_height = 0

    def stemHitTest(self, x, y):
        """Check if a click at (x, y) hits a stem label."""
        label_start = 0
        if x > label_start and x < label_start + self.LABEL_WIDTH:
            # Check if y is within the range of any stem
            for i, stem_name in enumerate(self.stem_names):
                # Use calculated stem_height and spacing from last draw
                stem_top = self.TOP_MARGIN + i * (self.stem_height + self.STEM_SPACING)
                stem_bottom = stem_top + self.stem_height
                if y > stem_top and y < stem_bottom:
                    return stem_name

        return None

    def _compute_waveform_points(self, audio_data, num_chunks):
        """Compute peak points for waveform display."""
        points = []
        visible_samples = len(audio_data)
        if visible_samples == 0 or num_chunks == 0:
            return points
            
        chunk_size = max(1, visible_samples // num_chunks)
        for j in range(num_chunks):
            chunk_start = j * chunk_size
            chunk_end = min(visible_samples, (j + 1) * chunk_size)
            if chunk_start >= len(audio_data):
                break
            chunk_data = audio_data[chunk_start:chunk_end]
            if len(chunk_data) == 0:
                continue
            # Use max of absolute values for peak
            peak = np.max(np.abs(chunk_data)) if len(chunk_data) > 0 else 0.0
            points.append((j, peak))
        return points

    def draw_waveform(self):
        """Draw individual waveform representations for each stem."""
        if not hasattr(self.slider_view.app, 'eng') or not self.slider_view.app.eng.current_song or not self.slider_view.app.eng.stems:
            self.slider_view.canvas.delete("waveform", "stem_label", "stem_bg") # Clear if no song/stems
            return
        
        # Get canvas dimensions
        canvas_width = self.slider_view.canvas.winfo_width()
        canvas_height = self.slider_view.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:  # Canvas not yet drawn or too small
            return
        
        # Clear previous drawing elements
        self.slider_view.canvas.delete("waveform")
        self.slider_view.canvas.delete("stem_label")
        self.slider_view.canvas.delete("stem_bg")
        
        # Get stems
        stems = self.slider_view.app.eng.stems
        if not stems:
            return
        
        # Pre-cache basic info if cache is empty
        if not self._waveform_cache:
            for stem_name in stems:
                audio_data = stems[stem_name]
                # Ensure audio_data is 1D (mono) for processing
                if audio_data.ndim > 1:
                    audio_data = audio_data[:, 0] # Take the first channel
                
                # Calculate max amplitude for normalization (avoid division by zero)
                max_amp = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 1.0
                if max_amp < 0.001: # Prevent division by very small numbers
                    max_amp = 1.0
                
                # Generate display name
                display_name = short_name(stem_name)
                if len(display_name) > 20: # Truncate long names
                    display_name = display_name[:18] + "..."
                
                # Initialize cache entry
                self._waveform_cache[stem_name] = {
                    "audio_data": audio_data, # Store mono data
                    "max_amp": max_amp,
                    "display_name": display_name,
                    "points": None, # Points computed later based on view
                    "range": None   # View range (start_sample, end_sample)
                }
        
        # Calculate height for each stem
        stem_names = list(stems.keys())
        num_stems = len(stem_names)
        
        # Calculate available height for waveforms
        available_height = canvas_height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        # Ensure positive height calculation, minimum height 30
        stem_height = max(30, int((available_height - (self.STEM_SPACING * max(0, num_stems - 1))) / num_stems)) if num_stems > 0 else 30

        # Store for hit testing
        self.stem_names = stem_names
        self.stem_height = stem_height

        # Draw vertical separator line between labels and waveforms
        self.slider_view.canvas.create_line(
            self.LABEL_WIDTH, 0, 
            self.LABEL_WIDTH, canvas_height,
            fill="#cccccc", width=1, tags="stem_bg"
        )
        
        # Get current view range from app variables
        view_start_time = self.app.vst.get()
        view_end_time = self.app.vet.get()
        sample_rate = self.app.eng.stem_srs
        
        # Draw each stem's waveform
        for i, stem_name in enumerate(stem_names):
            # Calculate y-position for this stem
            stem_top = self.TOP_MARGIN + i * (stem_height + self.STEM_SPACING)
            stem_bottom = stem_top + self.stem_height
            stem_center = (stem_top + stem_bottom) / 2
            
            # Check if stem is muted
            is_muted = stem_name in self.slider_view.app.eng.muted_stems
            
            # Draw stem label background
            self.slider_view.canvas.create_rectangle(
                0, stem_top - self.STEM_SPACING//2, # Extend slightly into spacing
                self.LABEL_WIDTH, stem_bottom + self.STEM_SPACING//2,
                fill="#e8e8e8", outline="", tags="stem_bg"
            )
            
            # Get cached data
            if stem_name not in self._waveform_cache: continue # Should not happen if pre-cached
            cached = self._waveform_cache[stem_name]
            display_name = cached["display_name"]
            max_amp = cached["max_amp"]
            audio_data = cached["audio_data"] # Use cached mono data
            
            # Calculate sample range based on view times
            total_samples = len(audio_data)
            start_sample = max(0, min(total_samples, int(view_start_time * sample_rate)))
            end_sample = max(start_sample, min(total_samples, int(view_end_time * sample_rate)))

            current_range = (start_sample, end_sample)
            cached_range = cached.get("range", None) # Use .get for safety

            # Recompute points if view range changed or points not computed yet
            if cached.get("points", None) is None or cached_range != current_range:
                view_audio = audio_data[start_sample:end_sample]
                # Calculate number of chunks based on visible waveform width
                waveform_width = max(1, canvas_width - self.LABEL_WIDTH - 20) # Usable width for waveform
                num_chunks = min(waveform_width, 1000) # Limit chunks for performance
                
                cached["points"] = self._compute_waveform_points(view_audio, num_chunks)
                cached["range"] = current_range

            points_raw = cached["points"]
            
            # Draw stem label text
            self.slider_view.canvas.create_text(
                10, stem_center, # Position label within its background area
                text=display_name, anchor="w",
                tags="stem_label",
                fill="#666666" if is_muted else "#000000"
            )
            
            # Draw horizontal separator line between stems
            if i > 0:
                y_sep = stem_top - self.STEM_SPACING//2
                self.slider_view.canvas.create_line(
                    0, y_sep, canvas_width, y_sep, # Full width separator
                    fill="#dddddd", width=1, tags="stem_bg"
                )
            
            # Skip drawing waveform if no points
            if not points_raw:
                continue
                
            # Draw waveform lines
            amp_scale = stem_height * 0.45 # Scale amplitude to fit within stem height nicely
            fill_color = "#aaaaaa" if is_muted else "#5080ff" # Muted color lighter
            
            # Calculate usable width for waveform drawing
            waveform_start_x = self.LABEL_WIDTH + 10
            waveform_draw_width = max(1, canvas_width - self.LABEL_WIDTH - 20)

            # Create coordinate list for polygon (filled waveform)
            poly_coords = []
            poly_coords.append((waveform_start_x, stem_center)) # Start at center left

            num_points = len(points_raw)
            for j, peak in points_raw:
                peak_scaled = (peak / max_amp) * amp_scale if max_amp > 0 else 0
                # Map point index j to x coordinate within the waveform area
                x_pos = waveform_start_x + int((j / num_points) * waveform_draw_width) if num_points > 0 else waveform_start_x
                poly_coords.append((x_pos, stem_center - peak_scaled))

            # Add points for the bottom half in reverse order
            for j, peak in reversed(points_raw):
                 peak_scaled = (peak / max_amp) * amp_scale if max_amp > 0 else 0
                 x_pos = waveform_start_x + int((j / num_points) * waveform_draw_width) if num_points > 0 else waveform_start_x
                 poly_coords.append((x_pos, stem_center + peak_scaled))

            poly_coords.append((waveform_start_x, stem_center)) # End at center left

            # Draw filled polygon if coordinates are valid
            if len(poly_coords) > 2:
                self.slider_view.canvas.create_polygon(
                    poly_coords,
                    fill=fill_color,
                    outline="", # No outline for the polygon
                    tags="waveform"
                )