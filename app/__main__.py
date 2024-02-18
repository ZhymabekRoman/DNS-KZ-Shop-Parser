from app.process_shop import main
from app.service import start_virt_display, stop_virt_display

import asyncio

if __name__ == "__main__":
    display = start_virt_display()
    asyncio.run(main())
    stop_virt_display(display)

