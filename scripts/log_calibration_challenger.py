"""Use the gated Session 6 training workflow; historical registry evidence is unchanged."""
from hotel_cancel.registry_training import run
import json

if __name__ == "__main__":
    print(json.dumps(run(register=True), indent=2))
