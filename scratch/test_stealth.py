import playwright_stealth
import inspect

print("Attributes in playwright_stealth:")
for name, obj in inspect.getmembers(playwright_stealth):
    if not name.startswith("__"):
        print(f"- {name}: {type(obj)}")
