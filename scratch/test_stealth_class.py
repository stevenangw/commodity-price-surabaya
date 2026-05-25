from playwright_stealth import Stealth
import inspect

print("Attributes in Stealth class:")
for name, obj in inspect.getmembers(Stealth):
    if not name.startswith("__"):
        print(f"- {name}: {type(obj)}")
