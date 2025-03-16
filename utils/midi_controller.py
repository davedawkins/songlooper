import mido
import threading
import time
from typing import Dict, Callable, Optional, List, Any

class MidiController:
    """Handles MIDI input for footpedal control of the app."""
    
    def __init__(self):
        self.midi_thread = None
        self.stop_event = threading.Event()
        self.command_map: Dict[int, Callable] = {}
        self.active_ports: List[str] = []
        self.input_ports = []
        
    def start_midi_listener(self):
        """Start the MIDI listener thread."""
        if self.midi_thread and self.midi_thread.is_alive():
            return
            
        self.stop_event.clear()
        self.midi_thread = threading.Thread(target=self._midi_worker)
        self.midi_thread.daemon = True
        self.midi_thread.start()
        
    def stop_midi_listener(self):
        """Stop the MIDI listener thread."""
        if self.midi_thread and self.midi_thread.is_alive():
            self.stop_event.set()
            self.midi_thread.join(timeout=1.0)
            
        # Close all open ports
        for port in self.input_ports:
            port.close()
        self.input_ports = []
        
    def get_available_devices(self) -> List[str]:
        """Return a list of available MIDI input devices."""
        try:
            return mido.get_input_names()
        except Exception as e:
            print(f"Error getting MIDI devices: {e}")
            return []
    
    def set_active_ports(self, port_names: List[str]):
        """Set which MIDI ports to listen to."""
        self.active_ports = port_names
        
        # If the listener is active, restart it to pick up the new ports
        was_running = self.midi_thread and self.midi_thread.is_alive()
        if was_running:
            self.stop_midi_listener()
            self.start_midi_listener()
    
    def add_command(self, midi_note: int, callback: Callable):
        """Map a MIDI note number to a callback function."""
        self.command_map[midi_note] = callback
        
    def clear_commands(self):
        """Clear all command mappings."""
        self.command_map = {}
        
    def _midi_worker(self):
        """Worker thread that listens for MIDI events."""
        # Close any existing ports
        for port in self.input_ports:
            port.close()
        
        # Open all active ports
        self.input_ports = []
        available_ports = mido.get_input_names()
        
        for port_name in self.active_ports:
            if port_name in available_ports:
                try:
                    port = mido.open_input(port_name)
                    self.input_ports.append(port)
                except Exception as e:
                    print(f"Error opening MIDI port {port_name}: {e}")
        
        # If no ports were opened, try to open the first available port
        if not self.input_ports and available_ports:
            try:
                default_port = mido.open_input(available_ports[0])
                self.input_ports.append(default_port)
                print(f"No active ports specified, using {available_ports[0]}")
            except Exception as e:
                print(f"Error opening default MIDI port: {e}")
        
        if not self.input_ports:
            print("No MIDI input ports available")
            return
            
        print(f"Listening on MIDI ports: {[p.name for p in self.input_ports]}")
        
        # Process MIDI messages
        while not self.stop_event.is_set():
            for port in self.input_ports:
                for message in port.iter_pending():
                    self._handle_midi_message(message)
            
            # Short sleep to prevent CPU hogging
            time.sleep(0.001)
    
    def _handle_midi_message(self, message):
        """Process a MIDI message and execute mapped commands."""
        # Focus on note_on events for footpedal control
        if message.type == 'note_on' and message.velocity > 0:
            note = message.note
            if note in self.command_map:
                # Execute the callback function
                try:
                    self.command_map[note]()
                except Exception as e:
                    print(f"Error executing MIDI command for note {note}: {e}")
        
        # Also handle control change messages (common for foot controllers)
        elif message.type == 'control_change':
            # Some foot controllers send control changes instead of notes
            # Map the control number as if it were a note
            control = message.control
            # Typically, we only want to trigger on a "press" (high value)
            if message.value > 64 and control in self.command_map:
                try:
                    self.command_map[control]()
                except Exception as e:
                    print(f"Error executing MIDI command for control {control}: {e}")