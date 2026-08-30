#!/usr/bin/env python3
"""The smallest program that can fail.

Run this before you debug anything else. If it does not print, the problem is
not in your code, and every hour spent reading your code is wasted.

    python hello.py

NOTE FOR ANYONE READING THE CORPUS: this file is a .py, and the retrieval tools
index .md ONLY. It is in here on purpose. See project-journal-hello-world.md --
a memory file is how a non-markdown artifact becomes findable at all.
"""


def main():
    print("hello, world")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
