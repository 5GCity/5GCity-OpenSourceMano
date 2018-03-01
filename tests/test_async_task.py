#!/usr/bin/env python3
# Recreate the conditions in which this will be used in OSM, called via tasks
import asyncio

if __name__ == "__main__":
    main()

async def do_something():
    pass

def main():

    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_something())
    loop.close()
    loop = None
