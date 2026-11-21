"""支持 ``python -m pytoolbox`` 直接运行。"""

import sys

from pytoolbox.cli import main

if __name__ == "__main__":
    sys.exit(main())
