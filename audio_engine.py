import os
import time
import threading
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
from dataclasses import dataclass
from typing import List, Optional
import pyrubberband as pyrb

@dataclass
class Section:
    name: str
    muted: bool
    level: float
    start_time: float
    end_time: float

@dataclass
class SongConfig:
    title: str
    path: str
    bpm: float
    sections: List[Section]
    current_section: str

class AudioEngine:
    def __init__(self):
        self.current_song: Optional[SongConfig] = None
        
        self.playing = False
        self.loop = False
        self.playback_speed = 1.0
        self.loop_delay = 0.0
        
        # Stems
        self.stems = {}
        self.stem_srs = 0
        self.muted_stems = set()
        self.processed_stems = {}
        
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        self.count_in = False
        
        # We'll store a "start_position" (seconds) for the next playback.
        self._start_position = 0.0
        self._end_position = 0.0

        # We track the actual playback position in real time:
        self._current_position = 0.0
        
        # Callback for when mute status changes
        self.mute_status_change_callback = { }
        self.next_mute_cb_id = 0


    # -------------------------------------------------------
    #   GETTERS / SETTERS
    # -------------------------------------------------------
    def set_position(self, pos: float):
        """Next playback will begin from 'pos' seconds."""
        self._current_position = pos

    def set_loop( self, loop : bool):
        self.loop = loop

    def set_playback_speed( self, speed : float):
        self.playback_speed = speed

    def set_loop_delay( self, delay : float):
        self.loop_delay = delay

    def get_start_position(self) -> float:
        return self._start_position

    def set_start_position(self, pos: float):
        """Next playback will end at 'pos' seconds."""
        self._start_position = pos

    def set_end_position(self, pos: float):
        """Next playback will end at 'pos' seconds."""
        print("set_end_position: " + str(pos))
        self._end_position = pos

    def get_end_position(self) -> float:
        return self._end_position
    
    def get_current_position(self) -> float:
        """Approximate last-known position in the original track."""
        return self._current_position

    def is_playing(self) -> bool:
        return self.playing
        
    def add_mute_callback(self, callback):
        """Set a callback function to be called when mute status changes."""
        client_id = self.next_mute_cb_id
        self.next_mute_cb_id += 1
        self.mute_status_change_callback[client_id] = callback
        return client_id

    def remove_mute_callback(self, client_id):
        """Remove a previously registered callback."""
        if client_id in self.mute_status_change_callback:
            del self.mute_status_change_callback[client_id]
        else:
            print(f"Warning: Callback ID {client_id} not found.")
    # -------------------------------------------------------
    #   SONG LOADING
    # -------------------------------------------------------
    def get_available_songs(self, base_folder: str) -> List[str]:
        """Return subfolders that contain a config.json file."""
        return [
            folder for folder in os.listdir(base_folder)
            if os.path.isdir(os.path.join(base_folder, folder)) and
               os.path.exists(os.path.join(base_folder, folder, 'config.json'))
        ]
    
    def find_section(self, section_name):
        target = None
        for s in self.current_song.sections:
            if s.name == section_name:
                target = s
                break
        return target

    def load_song(self, song_folder: str) -> SongConfig:
        config_path = os.path.join(song_folder, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config.json in {song_folder}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        sections = []
        for sec in config_data.get('sections', []):
            sections.append(Section(sec['name'], sec.get("muted", False), sec.get("level", 1.0), sec['start_time'], sec['end_time']))
        
        song_cfg = SongConfig(
            title=config_data.get('title', os.path.basename(song_folder)),
            path=song_folder,
            bpm=config_data.get('bpm', 120.0),
            sections=sections,
            current_section=config_data.get("current_section", "Full Song")
        )
        
        # Clear old stems
        self.stems.clear()
        self.processed_stems.clear()
        
        # Load each audio file
        for file in os.listdir(song_folder):
            if file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                stem_name = os.path.splitext(file)[0]
                file_path = os.path.join(song_folder, file)
                audio_data, samplerate = sf.read(file_path)
                self.stems[stem_name] = audio_data
                self.stem_srs = samplerate
        
        if not self.stems:
            raise FileNotFoundError(f"No audio files in {song_folder}")
        
        self.current_song = song_cfg
        self.muted_stems = set()
        
        # Reset positions
        self._start_position = 0.0
        self._current_position = 0.0
        self._end_position = self.get_total_duration()

        current_section = self.find_section( song_cfg.current_section )

        if current_section:
            print("loaded: " + str(current_section))
            self._start_position = current_section.start_time
            self._current_position = current_section.start_time
            self._end_position = current_section.end_time

        return song_cfg
    
    def get_stem_names(self) -> List[str]:
        return list(self.stems.keys())

    def play_section(self):
        """Play from _start_position to the end of the chosen section (or full track)."""
        if not self.current_song:
            raise ValueError("No song loaded.")
        
        # Stop any existing playback
        self.stop()
        
        # Clear so we can start fresh
        self.stop_event.clear()

        # If the user start_position is before the section's start, clamp
        print("Playing init: cur=" + str(self._current_position) + " start=" + str(self._start_position))

        if self._current_position < self._start_position or self._current_position > self._end_position:
            self._current_position = self._start_position
        
        self.playing = True

        # Start worker thread
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()

    def stop(self):
        self.pause()
        
    def pause(self):
        """Pause = Stop plus store the last-known position in _start_position."""
        if self.playing:
            self.stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=30.0)
            self.playing = False
        
            # Now we preserve the current_position
            # self._start_position = self._current_position

    def set_count_in(self, enabled: bool):
        self.count_in = enabled

    # -------------------------------------------------------
    #   TIME-STRETCH
    # -------------------------------------------------------
    def custom_time_stretch(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """Use RubberBand to time-stretch without pitch change."""
        return pyrb.time_stretch(audio, self.stem_srs, speed)

    def _time_stretch_section(self, stem_name: str, audio_slice: np.ndarray, speed: float) -> np.ndarray:
        """Cache time-stretch results so we don't recalc multiple times."""
        slice_key = (stem_name, len(audio_slice), speed)
        if slice_key in self.processed_stems:
            return self.processed_stems[slice_key]
        
        if audio_slice.ndim == 1:
            stretched = self.custom_time_stretch(audio_slice, speed)
            out = stretched.astype(np.float32)
        else:
            channels = audio_slice.shape[1]
            ch_list = []
            for ch in range(channels):
                single_ch = audio_slice[:, ch]
                st = self.custom_time_stretch(single_ch, speed)
                ch_list.append(st.astype(np.float32))
            out = np.column_stack(ch_list)
        
        self.processed_stems[slice_key] = out
        return out

    # -------------------------------------------------------
    #   MUTE / UNMUTE
    # -------------------------------------------------------
    def toggle_mute_stem(self, stem_name: str) -> bool:
        """Toggle a stem's muted state. Returns True if now muted, else False."""
        if stem_name not in self.stems:
            return False
        
        if stem_name in self.muted_stems:
            self.muted_stems.remove(stem_name)
            is_muted = False
        else:
            self.muted_stems.add(stem_name)
            is_muted = True
            
        # Notify callback about the change if one is registered
        for client_id, callback in self.mute_status_change_callback.items():
            if callable(callback):
                callback(stem_name, is_muted)
        # if self.mute_status_change_callback:
        #     self.mute_status_change_callback(stem_name, is_muted)
            
        return is_muted

    # -------------------------------------------------------
    #   DURATION
    # -------------------------------------------------------
    def get_total_duration(self) -> float:
        """Return the total length (in sec) of the full track (largest stem)."""
        if not self.stems:
            return 0.0
        return max(len(x) for x in self.stems.values()) / self.stem_srs

    # -------------------------------------------------------
    #   INTERNAL PLAYBACK WORKER
    # -------------------------------------------------------
    def _playback_worker(self):
        """Reads from self.current_section, streams audio from _start_position to end_time,
           possibly loops if self.loop is True."""

        # print("_playback: " + str(self._current_position) + " : " + str(self._start_position))
        # Optional count-in

        need_count_in = self.count_in and self._current_position == self._start_position

        start_sec = self._current_position
        end_sec = self._end_position
        
        while not self.stop_event.is_set():

            if need_count_in:
                need_count_in = False
                self._play_count_in()
                if self.stop_event.is_set():
                    self.playing = False
                    return

            section_duration = end_sec - start_sec
            if section_duration <= 0:
                if self.loop:
                    start_sec = self._start_position
                    self._current_position = start_sec
                    continue
                else:
                    break
            
            start_sample = int(start_sec * self.stem_srs)
            end_sample = int(end_sec * self.stem_srs)
            orig_len = end_sample - start_sample
            if orig_len <= 0:
                if self.loop:
                    start_sec = self._start_position
                    self._current_position = start_sec
                    continue
                else:
                    break
            
            new_length = int(section_duration * self.stem_srs / self.playback_speed)
            
            channels = 1
            for sdata in self.stems.values():
                if len(sdata.shape) > 1:
                    channels = max(channels, sdata.shape[1])
            
            mixed_section = np.zeros((new_length, channels), dtype=np.float32)
            
            for stem_name, audio_data in self.stems.items():
                if stem_name in self.muted_stems:
                    continue
                snippet = audio_data[start_sample:end_sample]
                stretched = self._time_stretch_section(stem_name, snippet, self.playback_speed)
                
                length_to_mix = min(len(mixed_section), len(stretched))
                if stretched.ndim == 1:
                    for c in range(channels):
                        mixed_section[:length_to_mix, c] += stretched[:length_to_mix]
                else:
                    out_ch = min(channels, stretched.shape[1])
                    mixed_section[:length_to_mix, :out_ch] += stretched[:length_to_mix, :out_ch]
            
            frames_consumed = 0
            should_recompute = [False]  # Using list as mutable reference for the callback closure
            
            def callback(outdata, frames, time_info, status):
                nonlocal frames_consumed, mixed_section
                
                # Check if we need to recompute the mix due to mute status change
                if should_recompute[0]:
                    should_recompute[0] = False  # Reset flag

                    remaining_samples = len(mixed_section)

                    if remaining_samples > 0:
                        # Calculate current position in samples
                        current_sample_pos = start_sample + int((frames_consumed / float(self.stem_srs)) * self.playback_speed * self.stem_srs)
                        end_sample_pos = end_sample
                        
                        # Skip if we're outside of valid range
                        if current_sample_pos >= end_sample_pos:
                            return
                        
                        # Create a new mixed section from the current position
                        new_mixed = np.zeros((remaining_samples, channels), dtype=np.float32)
                        for stem_name, audio_data in self.stems.items():
                            if stem_name in self.muted_stems:
                                continue
                            
                            remaining_orig_samples = end_sample_pos - current_sample_pos
                            if remaining_orig_samples <= 0:
                                continue
                                
                            snippet = audio_data[current_sample_pos:end_sample_pos]
                            stretched = self._time_stretch_section(stem_name, snippet, self.playback_speed)
                            
                            stretch_len = min(remaining_samples, len(stretched))
                            if stretched.ndim == 1:
                                for c in range(channels):
                                    new_mixed[:stretch_len, c] += stretched[:stretch_len]
                            else:
                                out_ch = min(channels, stretched.shape[1])
                                new_mixed[:stretch_len, :out_ch] += stretched[:stretch_len, :out_ch]
                        
                        # Replace the remaining part of the mixed section
                        mixed_section = new_mixed
                
                if status:
                    print(status)
                
                if frames > len(mixed_section):
                    outdata[:len(mixed_section)] = mixed_section
                    outdata[len(mixed_section):] = 0
                    frames_consumed += len(mixed_section)
                    mixed_section = np.zeros((0, channels), dtype=np.float32)
                    # self.stop_event.set()
                    self._current_position = end_sec
                else:
                    outdata[:] = mixed_section[:frames]
                    mixed_section = mixed_section[frames:]
                    frames_consumed += frames
                
                    played_sec = (frames_consumed / float(self.stem_srs)) * self.playback_speed
                    self._current_position = start_sec + played_sec

            # Define mute status change handler
            def handle_mute_change(stem_name, is_muted):
                should_recompute[0] = True
            
            # Set callback for mute changes
            callback_id = self.add_mute_callback(handle_mute_change)
            
            try:
                with sd.OutputStream(samplerate=self.stem_srs,
                                    channels=channels,
                                    blocksize=1024,
                                    dtype=np.float32,
                                    callback=callback):
                    while len(mixed_section) > 0 and not self.stop_event.is_set() and (self._end_position - self._current_position) > 0.001:
                        time.sleep(0.05)
            finally:
                # Restore the original callback
                self.remove_mute_callback(callback_id)

            if self.stop_event.is_set():
                print("Stopped")
                break
            
            if len(mixed_section) == 0 and (self._end_position - self._current_position) > 0.001:
                # End position likely changed to a larger value, go around but with current position
                print("End changed?")
                start_sec = self._current_position
                end_sec = self._end_position
                continue

            if not self.loop:
                break
            
            start_sec = self._current_position
            end_sec = self._end_position

            print("Delaying " + str(self.loop_delay))
            time.sleep(self.loop_delay)

            print("Restarting: " + str(self._start_position))
            need_count_in = self.count_in

            # start_sec = self.
            self._current_position = self._start_position
        
        self.playing = False
        # Do NOT forcibly set _start_position to end here.

    # -------------------------------------------------------
    #   COUNT-IN
    # -------------------------------------------------------
    def _play_count_in(self):
        """Play 4 quick clicks at BPM, or until user stops."""
        if not self.current_song or not self.current_song.bpm:
            return
        
        bpm = self.current_song.bpm
        beat_interval = 60.0 / bpm
        sr = 44100
        click_dur = 0.05
        t = np.linspace(0, click_dur, int(sr*click_dur), endpoint=False)
        click = 0.5*np.sin(2*np.pi*880*t)
        
        for _ in range(4):
            sd.play(click, sr)
            sd.wait()
            if self.stop_event.is_set():
                return
            remain = beat_interval - click_dur
            if remain > 0:
                time.sleep(remain)