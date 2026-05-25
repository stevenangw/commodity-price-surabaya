import playwright_stealth.stealth
import inspect

print("Attributes in playwright_stealth.stealth:")
for name, obj in inspect.getmembers(playwright_stealth.stealth):
    if not name.startswith("__"):
        print(f"- {name}: {type(obj)}")
