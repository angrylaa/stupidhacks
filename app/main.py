"""
LidLight — entry point.
Dims the screen when the MacBook lid is fully open; brightens it when closing.
"""
from .menu_controller import LidLightApp


def main():
    LidLightApp().run()


if __name__ == "__main__":
    main()
