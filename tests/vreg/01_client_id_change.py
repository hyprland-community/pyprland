#!/bin/env python

import itertools
import pyglet

counter = itertools.count()


def show_window():
    window = pyglet.window.Window()

    current = next(counter)

    @window.event
    def on_key_press(symbol, modifiers):
        current = next(counter)
        window.close()

    @window.event
    def on_draw():

        window.clear()
        label = pyglet.text.Label(
            f"Hello {current}",
            font_name="Times New Roman",
            font_size=36,
            x=window.width // 2,
            y=window.height // 2,
            anchor_x="center",
            anchor_y="center",
        )
        window.set_wm_class("test")
        label.draw()

    pyglet.app.run()


for n in range(5):
    show_window()
