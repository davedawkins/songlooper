"""Waveform drawing functionality for the slider view."""

import numpy as np

class SliderWaveform:
    """Handles drawing and rendering of audio waveforms in the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
    
    def draw_waveform(self):
        """Draw a waveform representation in the slider background."""
        if not hasattr(self.slider_view.app, 'eng') or not self.slider_view.app.eng.current_song or not self.slider_view.app.eng.stems:
            return
        
        # Get canvas dimensions
        canvas_width = self.slider_view.canvas.winfo_width()
        canvas_height = self.slider_view.canvas.winfo_height()
        
        if canvas_width <= 1:  # Canvas not yet drawn
            return
        
        # Clear previous waveform
        self.slider_view.canvas.delete("waveform")
        
        # Calculate center line (y-position)
        center_y = canvas_height / 2
        
        # Create buffers to store waveform data
        waveform_data = None
        total_stems = 0
        
        # Combine all non-muted stems
        for stem_name, audio_data in self.slider_view.app.eng.stems.items():
            if stem_name in self.slider_view.app.eng.muted_stems:
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
        if self.slider_view.svm.get():
            # In section view, only show the section part of the waveform
            start_time = self.slider_view.time_utils.parse_time(self.slider_view.stt.get())
            end_time = self.slider_view.time_utils.parse_time(self.slider_view.ent.get())
            
            if start_time is None or end_time is None:
                return
                
            start_sample = int(start_time * self.slider_view.app.eng.stem_srs)
            end_sample = int(end_time * self.slider_view.app.eng.stem_srs)
            
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
            self.slider_view.canvas.create_line(
                x1, y1, x2, y2, 
                fill="#8080ff", 
                width=1, 
                tags="waveform"
            )