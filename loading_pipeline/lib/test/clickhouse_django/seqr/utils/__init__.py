import os

# Falls through to the real seqr/utils/ for anything not stubbed in this directory.
__path__.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..', 'seqr', 'utils'))
