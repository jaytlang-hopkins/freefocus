# File: ui.py
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

import ctypes
import esper
import moderngl
import numpy as np
import random
import sys

from collections import namedtuple
from dataclasses import dataclass
from typing import Optional

# MARK: GPU code

VERTEX_IN_POSITION = "in_position"
VERTEX_IN_OFFSET = "in_offset"
VERTEX_IN_SCALE = "in_scale"
VERTEX_IN_COLOR = "in_color"

vertex_shader = f"""
#version 330

in vec2 {VERTEX_IN_POSITION};
in vec2 {VERTEX_IN_OFFSET};
in vec2 {VERTEX_IN_SCALE};
in vec4 {VERTEX_IN_COLOR};

out vec4 vertex_color;

void main() {{
    vec2 scaled = {VERTEX_IN_POSITION} * {VERTEX_IN_SCALE};
    vec2 true_position = scaled + {VERTEX_IN_OFFSET};

    gl_Position = vec4(true_position, 0.0, 1.0);
    vertex_color = {VERTEX_IN_COLOR};
}}
"""

fragment_shader = """
#version 330
in vec4 vertex_color;
out vec4 fragment_color;
void main() {
    fragment_color = vertex_color;
}
"""

# MARK: GL init

WINDOW_SIZE = 2560 // 2, 1440
MAX_RECTANGLES = 100

@dataclass
class GLContext:
    framebuffer: moderngl.Framebuffer
    texture: moderngl.Texture
    vao: moderngl.VertexArray

    offset_buffer: np.ndarray
    scale_buffer: np.ndarray
    color_buffer: np.ndarray

def shared_vertex_buffer(context):
    unit_quad = np.array([
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
        [0.0, 0.0],
    ], dtype='f4')

    vbo = context.buffer(unit_quad.tobytes())
    return (vbo, '2f', VERTEX_IN_POSITION)

def shared_index_buffer(context):
    indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
    return context.buffer(indices.tobytes())

def instance_buffer_for_shader_input(context, input):
    dtype = '4f/i' if input == VERTEX_IN_COLOR else '2f/i'
    # You may claim this is brittle, but I think it's succinct. Just be careful.
    ibo = context.buffer(reserve=MAX_RECTANGLES * 4 * int(dtype[0]))
    return (ibo, dtype, input)

def setup_gl():
    # 1. Wire up the GPU
    context = moderngl.create_context(standalone=True)
    texture = context.texture(WINDOW_SIZE, components=4)
    framebuffer = context.framebuffer(color_attachments=[texture]); framebuffer.use()

    program = context.program(vertex_shader, fragment_shader)

    # 2. Allocate graphics memory
    graphics_memory = {VERTEX_IN_POSITION: shared_vertex_buffer(context)}
    for input in VERTEX_IN_OFFSET, VERTEX_IN_SCALE, VERTEX_IN_COLOR:
        graphics_memory[input] = instance_buffer_for_shader_input(context, input)
    
    # 3. Point our vertex array at all this space
    vao = context.vertex_array(
        program,
        list(graphics_memory.values()),
        shared_index_buffer(context)
    )

    # 4. All done! Hide the details in an entity
    esper.create_entity(GLContext(
        framebuffer=framebuffer,
        texture=texture,
        vao=vao,
        offset_buffer=graphics_memory[VERTEX_IN_OFFSET][0],
        scale_buffer=graphics_memory[VERTEX_IN_SCALE][0],
        color_buffer=graphics_memory[VERTEX_IN_COLOR][0],
    ))

setup_gl()

# MARK: Rendering

Position = namedtuple("Position", "x y")
Size = namedtuple("Size", "width height")
Color = namedtuple("Color", "r g b a")

class BringToFront: pass

BLACK = Color(0, 0, 0, 255)
WHITE = Color(255, 255, 255, 255)

class CopyToGPU(esper.Processor):
    def _commit_uploads(self, gpu, offsets, scales, colors):
        # Normalize offsets + scales to NDC space
        offsets = (offsets / np.array(WINDOW_SIZE, dtype='f4')) * 2 - 1
        scales = (scales  / np.array(WINDOW_SIZE, dtype='f4')) * 2
        colors = colors / 255.0
        
        # ...validate..!!! The assumption is that no developer will surpass this...
        # conditions around the module make actually hitting this unlikely in steady state
        assert len(offsets) < MAX_RECTANGLES

        # ...and push.
        gpu.offset_buffer.write(offsets.tobytes())
        gpu.scale_buffer.write(scales.tobytes())
        gpu.color_buffer.write(colors.tobytes())

    def process(self):
        for _, gpu in esper.get_component(GLContext):
            offsets = []; scales = []; colors = []

            def push(position, size, color):
                offsets.append(position)
                scales.append(size)
                colors.append(color)

            deferred = []
            for ent, params in esper.get_components(Position, Size, Color):
                if esper.has_component(ent, BringToFront): deferred.append(params)
                else: push(*params)

            for params in deferred: push(*params)
            self._commit_uploads(gpu, *[np.array(a, dtype='f4') for a in (offsets, scales, colors)])

class Render(esper.Processor):
    def process(self):
        global count
        for _, gpu in esper.get_component(GLContext):
            instance_count = sum(1 for _ in esper.get_components(Position, Size, Color))

            gpu.framebuffer.clear()
            gpu.vao.render(vertices=6, instances=instance_count)
            gpu.texture.use()

            esper.dispatch_event(UI_FRAME_READY, gpu.texture.glo)

# MARK: Motion
Velocity = namedtuple("Velocity", "dx dy")

class Motion(esper.Processor):
    def process(self):
        for ent, (pos, vel) in esper.get_components(Position, Velocity):
            new_position = Position(pos.x + vel.dx, pos.y + vel.dy)
            esper.add_component(ent, new_position)

TargetPoint = namedtuple("TargetPoint", "x y")
ArrivedAtTarget = namedtuple("ArrivedAtTarget", "x y")

class Convergence(esper.Processor):
    def __init__(self, max_velocity=30, damping_radius=400, epsilon=10.0):
        super().__init__()
        self._max_velocity = max_velocity
        self._damping_radius = damping_radius
        self._epsilon = epsilon
    
    def process(self):
        for ent, (pos, target) in esper.get_components(Position, TargetPoint):
            target_vector = np.array(target, dtype='f') - np.array(pos)
            target_distance = np.linalg.norm(target_vector)
            target_unit_vector = target_vector / target_distance

            # 1. Have we arrived at our target, modulo some fudge factor?
            if target_distance < self._epsilon:
                esper.add_component(ent, ArrivedAtTarget(target.x, target.y))

            # 2. If not, accelerate in the correct direction
            try: dx, dy = esper.component_for_entity(ent, Velocity)
            except KeyError:
                dx = dy = 0

            new_velocity = [dx, dy] + target_vector

            # 3. Clamp the resulting velocity
            magnitude = np.linalg.norm(new_velocity)
            if magnitude > self._max_velocity:
                new_velocity = new_velocity / magnitude * self._max_velocity

            # 4. Damp, add, done.
            if target_distance < self._damping_radius:
                new_velocity *= target_distance / self._damping_radius

            esper.add_component(ent, Velocity(*new_velocity))

# MARK: Bounds

class OOB: pass
class Bounds(esper.Processor):
    def process(self):
        for ent, (position, size, velocity) in esper.get_components(Position, Size, Velocity):
            for dim in range(2):
                too_low = position[dim] + size[dim] < 0
                too_high = position[dim] > WINDOW_SIZE[dim]

                if too_low and velocity[dim] <= 0 or too_high and velocity[dim] >= 0:
                    esper.add_component(ent, OOB())
                else:
                    try: esper.remove_component(ent, OOB())
                    except KeyError: pass

@dataclass
class Respawnable:
    preferred_respawn_point: Optional[Position]
    randomizes_velocity_at_respawn: bool

class Respawn(esper.Processor):
    def __init__(self, randomized_velocity_magnitude=5):
        super().__init__()
        self._randomized_velocity_magnitude = randomized_velocity_magnitude

    def _generate_random_respawn_point(self, rect_size):
        x_zero, y_zero = [-s for s in rect_size]
        x_max, y_max = WINDOW_SIZE
        x_rand, y_rand = [random.randrange(0, s) for s in WINDOW_SIZE]

        match random.choice(["top", "bottom", "left", "right"]):
            case "top": return Position(x_rand, y_zero)
            case "bottom": return Position(x_rand, y_max)
            case "left": return Position(x_zero, y_rand)
            case "right": return Position(x_max, y_rand)
        
    def _generate_random_respawn_velocity(self):
        indices = np.arange(-100, -1) + np.arange(1, 100)
        unscaled_velocity = np.random.choice(indices, 2)
        scaled_velocity = unscaled_velocity / np.linalg.norm(unscaled_velocity) * self._randomized_velocity_magnitude

        return Velocity(*scaled_velocity)
        
    def process(self):
        for ent, (_oob, rect_size, spawn_parameters) in esper.get_components(OOB, Size, Respawnable):
            respawn_point = spawn_parameters.preferred_respawn_point
            if respawn_point is None:
                respawn_point = self._generate_random_respawn_point(rect_size)

            esper.add_component(ent, respawn_point)

            if spawn_parameters.randomizes_velocity_at_respawn:
                esper.add_component(ent, self._generate_random_respawn_velocity())

            esper.remove_component(ent, OOB)

# MARK: Transitions

DesiredColor = namedtuple("DesiredColor", "r g b a")

class ColorFade(esper.Processor):
    def __init__(self, fade_step_size=10.0):
        super().__init__()
        self._fade_step_size = fade_step_size
    
    def _interpolate_component_towards_desired(self, current, desired):
        delta = desired - current
        if abs(delta) < self._fade_step_size:
            return desired
        else:
            return round(current + np.sign(delta) * self._fade_step_size)
    
    def process(self):
        for ent, (current_color, desired_color) in esper.get_components(Color, DesiredColor):
            new_components = []
            for i in range(len(current_color)):
                new_component = self._interpolate_component_towards_desired(current_color[i], desired_color[i])
                new_components.append(new_component)

            new_color = Color(*new_components)
            esper.add_component(ent, new_color)

            if new_color == desired_color: esper.remove_component(ent, DesiredColor)

class Disappear: pass
class FadeOut(esper.Processor):
    def process(self):
        for ent, (current_color, _) in esper.get_components(Color, Disappear):
            if esper.has_component(ent, DesiredColor): continue
            elif current_color == BLACK: esper.delete_entity(ent)
            else: esper.add_component(ent, DesiredColor(*BLACK))

# MARK: Events

UI_STATE_IDLE = "ui_idle"
UI_STATE_CONVERGING = "ui_converge"
UI_STATE_OPENING = "ui_opening"
UI_STATE_RUNNING = "ui_running"

UI_FRAME_READY = "ui_frame_ready"

# MARK: Particles

@dataclass
class Particle:
    index: int

INITIAL_PARTICLE_COLOR = Color(128, 128, 128, 255)
CONVERGING_PARTICLE_COLOR = Color(*WHITE)

def create_particles(num_particles=20, particle_side_length=20):
    if any(True for _ in esper.get_component(Particle)): return # idempotency

    for i in range(num_particles):
        esper.create_entity(
            Position(0, 0), OOB(),
            Size(particle_side_length, particle_side_length),
            Color(*BLACK),
            DesiredColor(*INITIAL_PARTICLE_COLOR),
            Respawnable(None, True),
            Particle(i)
        )

def converge_particles():
    particle_count = sum(1 for _ in esper.get_component(Particle))
    gap_between_particles = WINDOW_SIZE[0] / (particle_count + 1)

    for ent, (particle, size) in esper.get_components(Particle, Size):
        # 1. Compute our target point
        center_coordinates = np.array((
            gap_between_particles * (particle.index + 1),
            WINDOW_SIZE[1] / 2
        ))

        target_coordinates = center_coordinates - size.width / 2
        esper.add_component(ent, TargetPoint(*target_coordinates))

        # 2. Fade to white
        esper.add_component(ent, DesiredColor(*CONVERGING_PARTICLE_COLOR))
    
class AlignParticles(esper.Processor):
    def process(self):
        num_particles = sum(1 for _ in esper.get_component(Particle))
        num_particles_on_target = sum(1 for _ in esper.get_components(Particle, ArrivedAtTarget)) 

        if num_particles > 0 and num_particles == num_particles_on_target:
            esper.dispatch_event(UI_STATE_OPENING)

def remove_particles():
    for ent, _ in esper.get_component(Particle):
        esper.delete_entity(ent)

esper.set_handler(UI_STATE_IDLE, create_particles)
esper.set_handler(UI_STATE_CONVERGING, converge_particles)
esper.set_handler(UI_STATE_OPENING, remove_particles)

# MARK: Curtains

class Curtain: pass

def create_curtains(curtain_velocity=100.0):
    for position in "top", "bottom":
        y_position = 0 if position == "top" else WINDOW_SIZE[1] / 2

        y_velocity = curtain_velocity
        if position == "top": y_velocity *= -1

        esper.create_entity(
            Curtain(),
            BringToFront(),
            Position(0, y_position),
            Velocity(0, y_velocity),
            Size(WINDOW_SIZE[0], WINDOW_SIZE[1] / 2),
            Color(*BLACK)
        )

class CurtainsOpen(esper.Processor):
    def process(self):
        if sum(1 for _ in esper.get_components(Curtain, OOB)) < 2: return

        for ent, _ in esper.get_component(Curtain): esper.delete_entity(ent)
        esper.dispatch_event(UI_STATE_RUNNING)

esper.set_handler(UI_STATE_OPENING, create_curtains)

# MARK: OKN lines

class Line: pass

def create_lines(num_visible_lines=21):
    num_lines = num_visible_lines + 1
    line_side_length = WINDOW_SIZE[0] / num_visible_lines

    for i in range(num_lines):
        esper.create_entity(
            Line(),
            Position((i - 1) * line_side_length, 0),
            Size(line_side_length, WINDOW_SIZE[1]),
            Color(*WHITE) if i % 2 == 0 else Color(*BLACK),
            Respawnable(Position(-line_side_length, 0), False)
        )

def advance_lines(line_velocity=5.0):
    for ent, _ in esper.get_component(Line):
        esper.add_component(ent, Velocity(line_velocity, 0))

def remove_lines():
    for ent, _ in esper.get_component(Line):
        esper.add_component(ent, Disappear())

esper.set_handler(UI_STATE_OPENING, create_lines)
esper.set_handler(UI_STATE_RUNNING, advance_lines)
esper.set_handler(UI_STATE_IDLE, remove_lines)

# MARK: Main

processors = [
    CopyToGPU,
    Render,
    Motion,
    Convergence, 
    Bounds,
    Respawn,
    ColorFade,
    FadeOut,
    AlignParticles,
    CurtainsOpen,
]

for processor in processors:
    esper.add_processor(processor())

esper.dispatch_event(UI_STATE_IDLE)