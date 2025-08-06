# File: cli.py
# Copyright 2025 Jay Lang
# 
# This file is part of the EyeMotion project. EyeMotion is free software: you
# can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# EyeMotion is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# EyeMotion. If not, see <https://www.gnu.org/licenses/>. 

from dataclasses import dataclass
from typing import Callable, List, Union

import esper
import msgspec
import select
import socket
import struct
import sys

# MARK: Commands
class Command(msgspec.Struct, tag=True):
    name: str
    arguments: List[str]

# .. which is sent over a local networking connection...
IPC_ADDRESS = ('127.0.0.1', 55365)

# .. and for which a response is returned
class Response(msgspec.Struct, tag=True):
    succeeded: bool
    message: str

# MARK: Encode/decode

LENGTH_FORMAT = '!I'
LENGTH_SIZE = 4

def encode_object(object):
    encoded_object = msgspec.json.encode(object)

    length_prefix = struct.pack(LENGTH_FORMAT, len(encoded_object))
    return length_prefix + encoded_object

def split_encoded_length_from_object(encoded_object_bytes):
    if len(encoded_object_bytes) >= LENGTH_SIZE:
        length = struct.unpack(LENGTH_FORMAT, encoded_object_bytes[:LENGTH_SIZE])[0]
        return length, encoded_object_bytes[LENGTH_SIZE:]

def decode_object(encoded_object_bytes):
    object_length, to_parse = split_encoded_length_from_object(encoded_object_bytes)

    if object_length is not None and len(to_parse) >= object_length:
        decoder = msgspec.json.Decoder(Union[Command, Response])
        return decoder.decode(to_parse), to_parse[object_length:]
    else:
        return None, encoded_object_bytes

# MARK: Server code

class SocketReader:
    def __init__(self, socket):
        self._socket = socket
        self._message_buffer = bytearray()
    
    def _socket_is_readable(self, blocking=True):
        timeout = 0 if not blocking else None
        readable, _, _ = select.select([self._socket], [], [], timeout)
        return self._socket in readable
    
    def read(self, blocking=True):
        if self._socket_is_readable(blocking):
            new_data = self._socket.recv(16384)
            if len(new_data) == 0:
                raise ConnectionError("Peer has disconnected")

            self._message_buffer.extend(new_data)
            parsed_message, self._message_buffer = decode_object(self._message_buffer)

            return parsed_message

class SocketWriter:
    def __init__(self, socket):
        self._socket = socket
        self._objects_to_send = []
    
    def _socket_is_writeable(self, blocking=True):
        timeout = 0 if not blocking else None
        _, writeable, _, = select.select([], [self._socket], [], timeout)
        return self._socket in writeable
    
    def enqueue_object(self, obj):
        encoded_object = encode_object(obj)
        self._objects_to_send.append(encoded_object)
    
    def send_enqueued_objects(self, blocking=True):
        while self._socket_is_writeable(blocking):
            try: to_send = self._objects_to_send[0]
            except IndexError: break

            bytes_sent = self._socket.send(to_send)
            if bytes_sent == 0:
                raise ConnectionError("Peer has disconnected")
            elif bytes_sent < len(to_send):
                self._objects_to_send[0] = to_send[bytes_sent:] 
            else:
                self._objects_to_send.pop(0)

# MARK: Endpoint

@dataclass
class Connection:
    reader: SocketReader
    writer: SocketWriter

class Listener(socket.socket): pass

def reset_connection():
    for ent, _ in esper.get_component(Connection): esper.delete_entity(ent)

    l = Listener(socket.AF_INET, socket.SOCK_STREAM)

    l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    try: l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
    except AttributeError: pass # windoze zzzz

    l.bind(IPC_ADDRESS)
    l.listen()
    esper.create_entity(l)

CLI_RESET_CONNECTION = "cli_reset_connection"
esper.set_handler(CLI_RESET_CONNECTION, reset_connection)

class Accept(esper.Processor):
    def process(self):
        for ent, listener in esper.get_component(Listener):
            # 1. Is a client connecting?
            readable, _, _ = select.select([listener], [], [], 0)
            if listener not in readable: return

            # 2. Cool, pick 'em up.
            connection_socket, _ = listener.accept()
            connection_socket.setblocking(False)

            esper.create_entity(Connection(
                SocketReader(connection_socket),
                SocketWriter(connection_socket),
            ))
            esper.delete_entity(ent)

class CurrentConnection:
    def __enter__(self):
        for _, conn in esper.get_component(Connection): return conn

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type == ConnectionError:
            esper.dispatch_event(CLI_RESET_CONNECTION)
            return True

# MARK: Response

def respond(success, message=""):
    response_obj = Response(success, message)
    with CurrentConnection() as conn:
        if conn is not None: conn.writer.enqueue_object(response_obj)

CLI_RESPONSE_READY = "cli_response_ready"
esper.set_handler(CLI_RESPONSE_READY, respond)

class FlushResponses(esper.Processor):
    def process(self):
        with CurrentConnection() as conn:
            if conn is not None: conn.writer.send_enqueued_objects(blocking=False)

# MARK: Parsing
@dataclass
class Parser:
    key: str
    description: str
    parse: Callable

class Parse(esper.Processor):
    def _emit_help_response(self, return_success):
        response_message = "Supported commands:"
        for _, parser in esper.get_component(Parser):
            response_message += f"\n\t=> {parser.key}: {parser.description}"
        
        response_message += "\n\t=> help: show this message"
        esper.dispatch_event(CLI_RESPONSE_READY, return_success, response_message)

    def process(self):
        # 1. Pull off our command from our client connection:
        with CurrentConnection() as conn:
            if conn is None or (command := conn.reader.read(blocking=False)) is None:
                return
            
            for _, parser in esper.get_component(Parser):
                if parser.key == command.name:
                    parser.parse(command.arguments)
                    return

            self._emit_help_response(command.name == "help")

def add_parser(key, description, callback):
    esper.create_entity(Parser(key, description, callback))

CLI_ADD_PARSER = "cli_add_parser"
esper.set_handler(CLI_ADD_PARSER, add_parser)

# MARK: Silly client code

class ServerConnection:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try: self._socket.connect(IPC_ADDRESS)
        except:
            print("Could not connect to the EyeMotion service. Is it running?")
            sys.exit(1)
        
        self._reader, self._writer = SocketReader(self._socket), SocketWriter(self._socket)

    def send_and_await_response(self, command):
        try:
            self._writer.enqueue_object(command); self._writer.send_enqueued_objects()
            return self._reader.read()
        except ConnectionError:
            print("Lost connection to the EyeMotion service -- is the headset still running?")
            sys.exit(1)

def read_user_input(previous_command_succeeded):
    prompt = "[*] > " if previous_command_succeeded else "[!] > "
    try: return input(prompt)
    except EOFError: sys.exit(0)

def eval_user_input_as_command(user_input):
    split_input = user_input.strip().split()
    if split_input == []: return None

    return Command(split_input[0], split_input[1:])

# MARK: Main

if __name__ == "__main__":
    conn = ServerConnection()
    command_succeeded = True

    while True:
        user_input = read_user_input(command_succeeded)
        command = eval_user_input_as_command(user_input)

        if command is None:
            command_succeeded = True
            continue

        response = conn.send_and_await_response(command)

        command_succeeded = response.succeeded
        if response.message != "": print(response.message)

# ... if we're running in a module context, set up ECS and poke the listener
else:
    for t in [Accept, Parse, FlushResponses]:
        esper.add_processor(t())
    esper.dispatch_event(CLI_RESET_CONNECTION)
