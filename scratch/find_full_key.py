import requests
import re

def main():
    js_url = "https://panelharga.badanpangan.go.id/main.69d329b558fe5803.js"
    response = requests.get(js_url)
    if response.status_code == 200:
        match = re.search(r'"x-api-key"\s*:\s*"([^"]+)"', response.text)
        if match:
            print("FULL KEY FOUND:")
            print(match.group(1))
            print("Length of key:", len(match.group(1)))
        else:
            print("Key not found with regex.")
    else:
        print("Failed to download JS.")

if __name__ == "__main__":
    main()
