import argparse
import json
import os
import sys
from typing import List, Dict, Optional

class ValidationError(Exception):
    pass

class Header:
    def __init__(self, version: int, width: int, height: int, timestamp: Optional[int] = None, 
                 command: Optional[str] = None, theme: Optional[Dict[str, str]] = None, 
                 title: Optional[str] = None, idle_time_limit: Optional[float] = None, 
                 env: Optional[Dict[str, str]] = None):
        self.version = version
        self.width = width
        self.height = height
        self.timestamp = timestamp
        self.command = command
        self.theme = theme or {}
        self.title = title
        self.idle_time_limit = idle_time_limit
        self.env = env or {}

    @staticmethod
    def validate(header):
        if not header:
            raise ValidationError("header must not be nil")
        if header.version != 2:
            raise ValidationError("only casts with version 2 are valid")
        if header.width <= 0:
            raise ValidationError("a valid width (>0) must be specified")
        if header.height <= 0:
            raise ValidationError("a valid height (>0) must be specified")
        return True

class Event:
    def __init__(self, time: float, event_type: str, data: str):
        self.time = time
        self.type = event_type
        self.data = data

    @staticmethod
    def validate(event):
        if not event:
            raise ValidationError("event must not be nil")
        if event.type not in ["i", "o"]:
            raise ValidationError("type must either be 'o' or 'i'")
        return True

class Cast:
    def __init__(self, header: Header, event_stream: List[Event]):
        self.header = header
        self.event_stream = event_stream

    @staticmethod
    def validate(cast):
        if not cast:
            raise ValidationError("cast must not be nil")
        Header.validate(cast.header)
        Cast.validate_event_stream(cast.event_stream)
        return True

    @staticmethod
    def validate_event_stream(event_stream: List[Event]):
        last_time = -1
        for event in event_stream:
            if event.time < last_time:
                raise ValidationError("events must be ordered by time")
            Event.validate(event)
            last_time = event.time
        return True

    @staticmethod
    def encode(writer, cast):
        if not writer:
            raise ValidationError("a writer must be specified")
        if not cast:
            raise ValidationError("a cast must be specified")

        # Use compact encoding for the header
        header_json = json.dumps(cast.header.__dict__)
        writer.write(header_json + '\n')

        for event in cast.event_stream:
            json.dump([event.time, event.type, event.data], writer)
            writer.write('\n')
        return True

    @staticmethod
    def decode(reader):
        if not reader:
            raise ValidationError("reader must not be nil")

        try:
            first_line = reader.readline().strip()
            if not first_line:
                raise ValidationError("Header line is empty")
            header = json.loads(first_line)
            header_obj = Header(**header)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Error decoding header: {e}")

        event_stream = []
        for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                event_data = json.loads(line)
                event = Event(event_data[0], event_data[1], event_data[2])
                event_stream.append(event)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Error decoding event: {e}")

        cast = Cast(header_obj, event_stream)
        Cast.validate(cast)
        return cast

class QuantizeRange:
    def __init__(self, from_: float, to: float):
        self.From = from_
        self.To = to

    def in_range(self, value: float) -> bool:
        return self.From <= value < self.To

    def range_overlaps(self, another: 'QuantizeRange') -> bool:
        return self.in_range(another.From) or self.in_range(another.To)

class QuantizeTransformation:
    def __init__(self, ranges: List[QuantizeRange]):
        self.ranges = ranges

    def transform(self, cast: Cast):
        if not cast:
            raise ValidationError("cast must not be nil")
        if not cast.event_stream:
            raise ValidationError("event stream must not be empty")
        if not self.ranges:
            raise ValidationError("at least one quantization range must be specified")

        deltas = [0] * len(cast.event_stream)
        for i in range(len(cast.event_stream) - 1):
            delta = cast.event_stream[i + 1].time - cast.event_stream[i].time

            for q_range in self.ranges:
                if q_range.in_range(delta):
                    delta = q_range.From
                    break

            deltas[i] = delta

        for i in range(len(cast.event_stream) - 1):
            cast.event_stream[i + 1].time = cast.event_stream[i].time + deltas[i]

        return True

def parse_quantize_range(input: str) -> QuantizeRange:
    parts = input.split(',')
    if len(parts) > 2:
        raise ValidationError("invalid range format: must be `value[,value]`")

    from_ = float(parts[0])
    to = float(parts[1]) if len(parts) == 2 else float('inf')

    if from_ < 0:
        raise ValidationError("constraint not verified: from >= 0")
    if to <= from_:
        raise ValidationError("constraint not verified: from < to")

    return QuantizeRange(from_, to)

def parse_quantize_ranges(inputs: List[str]) -> List[QuantizeRange]:
    ranges = []
    for input in inputs:
        ranges.append(parse_quantize_range(input))
    return ranges

class Transformer:
    def __init__(self, transformation: QuantizeTransformation, input_file: Optional[str], output_file: Optional[str], debug: bool):
        if not transformation:
            raise ValidationError("a transformation must be specified")
        
        self.transformation = transformation
        self.input_file = input_file
        self.output_file = output_file
        self.debug = debug

    def transform(self):
        try:
            if self.debug:
                print(f"Reading file: {self.input_file}")
            with open(self.input_file, 'r') as infile:
                cast = Cast.decode(infile)
                Cast.validate(cast)
                self.transformation.transform(cast)
            
            if self.debug:
                print(f"Writing file: {self.output_file}")
            with open(self.output_file, 'w') as outfile:
                Cast.encode(outfile, cast)
        except Exception as e:
            raise ValidationError(f"Error processing file {self.input_file}: {e}")

def quantize_action(script_dir: str, debug: bool):
    input_dir = os.path.join(script_dir, 'static', 'splits')
    if debug:
        print(f"Input directory: {input_dir}")
    
    default_range = ["2"]
    quantize_ranges = parse_quantize_ranges(default_range)
    transformation = QuantizeTransformation(quantize_ranges)

    for filename in os.listdir(input_dir):
        if filename.endswith(".cast"):
            input_path = os.path.join(input_dir, filename)
            output_path = input_path

            if debug:
                print(f"Processing file: {input_path}")
            try:
                transformer = Transformer(transformation, input_path, output_path, debug)
                transformer.transform()
            except ValidationError as e:
                print(f"ValidationError processing file {input_path}: {e}")
            except Exception as e:
                print(f"Unexpected error processing file {input_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Quantize Asciinema Casts in a directory.')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.realpath(__file__))
    try:
        quantize_action(script_dir, args.debug)
    except ValidationError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
