import sys
from pathlib import Path

# Permite `import app...` al correr pytest desde forensic-api/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
