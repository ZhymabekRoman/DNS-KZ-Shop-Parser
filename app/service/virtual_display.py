from pyvirtualdisplay import Display

def start_virt_display() -> Display:
    display = Display(visible=0, size=(800, 600))
    display.start()

    return display


def stop_virt_display(display: Display) -> None:
    display.stop()