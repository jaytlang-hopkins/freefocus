# File: ipc/clientserver.py
# Copyright 2025 Jay Lang
# 
# This file is part of the FreeFocus project. FreeFocus is free software: you
# can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# FreeFocus is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# FreeFocus. If not, see <https://www.gnu.org/licenses/>. 
from dataclasses import dataclass
from typing import Callable, List, Union

import atexit
import esper
import msgspec
import multiprocessing
import select
import socket
import struct

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

# MARK: IPC Bedrock

def query_socket_capabilities(socket):
    readable, writeable = select.select([socket], [socket], [], 0)[:2]
    capabilities = []

    if socket in readable: capabilities.append(Readable)
    if socket in writeable: capabilities.append(Writeable)
    return capabilities

@dataclass
class Connection:
    socket: socket.socket
    message_buffer: bytearray
    objects_to_send: List[Response]

class Readable: pass
class Writeable: pass

class Select(esper.Processor):
    def process(self):
        for ent, conn in esper.get_component(Connection):
            capabilities = query_socket_capabilities(conn.socket)
            for capability in Readable, Writeable:
                if capability in capabilities: esper.add_component(ent, capability())
                elif esper.has_component(ent, capability): esper.remove_component(ent, capability)

class Read(esper.Processor):
    def process(self):
        for ent, (conn, _) in esper.get_components(Connection, Readable):
            new_data = conn.socket.recv(16384)

            if len(new_data) == 0:
                raise ConnectionError("Peer has disconnected")

            conn.message_buffer.extend(new_data)
            parsed_message, conn.message_buffer = decode_object(conn.message_buffer)

            if parsed_message is not None: esper.create_entity(parsed_message)

class Flush(esper.Processor):
    def process(self):
        for ent, (conn, _) in esper.get_components(Connection, Writeable):
            if len(conn.objects_to_send) > 0:
                to_send = conn.objects_to_send[0]
                bytes_sent = conn.socket.send(to_send)

                if bytes_sent == 0:
                    raise ConnectionError("Peer has disconnected")

                elif bytes_sent < len(to_send): conn.objects_to_send[0] = to_send[bytes_sent:] 
                else: conn.objects_to_send.pop(0)

for processor in Select, Read, Flush:
    esper.add_processor(processor())

# MARK: Client process

IPC_CLIENT_INITIALIZE = "ipc_client_initialize"
IPC_CLIENT_FORWARD_INPUT = "ipc_forward_input"
IPC_CLIENT_RECEIVED_RESPONSE = "ipc_received_response"

class SendCommand(esper.Processor):
    def process(self):
        for _, conn in esper.get_component(Connection):
            for ent, cmd in esper.get_component(Command):
                encoded_command = encode_object(cmd)
                conn.objects_to_send.append(encoded_command)
                esper.delete_entity(ent)

class GetResponse(esper.Processor):
    def process(self):
        for ent, response in esper.get_component(Response):
            esper.dispatch_event(IPC_CLIENT_RECEIVED_RESPONSE, response.succeeded, response.message)
            esper.delete_entity(ent)

def forward_user_input(user_input):
    split_input = user_input.strip().split()
    if split_input == []: return None

    esper.create_entity(Command(split_input[0], split_input[1:]))

class Listener(socket.socket): pass

class Listen(esper.Processor):
    def _ensure_listener(self):
        if any(esper.get_component(Listener)): return

        l = Listener(socket.AF_INET, socket.SOCK_STREAM)

        l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        try: l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
        except AttributeError: pass # windoze zzzz

        l.bind(IPC_ADDRESS); l.listen()
        esper.create_entity(l)

    def process(self):
        if any(esper.get_component(Connection)): return
        self._ensure_listener()

        for ent, listener in esper.get_component(Listener):
            if Readable in query_socket_capabilities(listener):
                connection_socket, _ = listener.accept()
                connection_socket.setblocking(False)

                esper.create_entity(Connection(
                    socket=connection_socket,
                    message_buffer=bytearray(),
                    objects_to_send=[]
                ))

                esper.delete_entity(ent)

def initialize_client():
    for p in SendCommand, GetResponse, Listen: esper.add_processor(p())
    esper.set_handler(IPC_CLIENT_FORWARD_INPUT, forward_user_input)

esper.set_handler(IPC_CLIENT_INITIALIZE, initialize_client)

# MARK: Server process

IPC_SERVER_ADD_PARSER = "ipc_server_add_parser"
IPC_SERVER_INITIALIZE = "ipc_server_initialize"
IPC_SERVER_RESPONSE_READY = "ipc_server_response_ready"

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
        esper.create_entity(Response(return_success, response_message))

    def process(self):
        # 1. Pull off our command from our client connection:
        for ent, command in esper.get_component(Command):
            esper.delete_entity(ent)

            for _, parser in esper.get_component(Parser):
                if parser.key == command.name:
                    parser.parse(command.arguments)
                    return

            self._emit_help_response(command.name == "help")

def add_parser(key, description, callback):
    esper.create_entity(Parser(key, description, callback))

class PendingConnection(socket.socket): pass

class Connect(esper.Processor):
    def _ensure_connection_attempt(self):
        if any(esper.get_component(PendingConnection)): return

        s = PendingConnection(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False)

        try: s.connect(IPC_ADDRESS)
        except BlockingIOError: pass

        esper.create_entity(s)

    def process(self):
        if any(esper.get_component(Connection)): return

        self._ensure_connection_attempt()
        for ent, socket in esper.get_component(PendingConnection):
            if Writeable not in query_socket_capabilities(socket): continue

            esper.create_entity(Connection(
                socket=socket,
                message_buffer=bytearray(),
                objects_to_send=[]
            ))
            esper.delete_entity(ent)

class Respond(esper.Processor):
    def process(self):
        for _, conn in esper.get_component(Connection):
            for ent, response in esper.get_component(Response):
                encoded_response = encode_object(response)
                conn.objects_to_send.append(encoded_response)
                esper.delete_entity(ent)

def respond(succeeded, message=""):
    esper.create_entity(Response(succeeded, message))

def initialize_server():
    for p in Parse, Connect, Respond: esper.add_processor(p())

    esper.set_handler(IPC_SERVER_ADD_PARSER, add_parser)
    esper.set_handler(IPC_SERVER_RESPONSE_READY, respond)

esper.set_handler(IPC_SERVER_INITIALIZE, initialize_server)

# MARK: Fork
def engine_entry(*args):
    esper.dispatch_event(IPC_SERVER_INITIALIZE)

    from . import engine
    esper.dispatch_event(engine.ENGINE_START_RUNLOOP, *args)

def fork_engine(*args):
    esper.dispatch_event(IPC_CLIENT_INITIALIZE)

    p = multiprocessing.Process(target=engine_entry, args=args, name="FreeFocus Daemon")
    p.start()

    def terminate_engine(): p.terminate(); p.join()
    atexit.register(terminate_engine)

IPC_FORK_ENGINE = "ipc_fork_engine"
esper.set_handler(IPC_FORK_ENGINE, fork_engine)