# This is a shim loader intended to keep previously deployed seqr-platform
# charts that pull a new docker image running.

import time


def main():
    while True:
        time.sleep(5)


if __name__ == '__main__':
    main()
