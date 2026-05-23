import requests
import argparse

parser = argparse.ArgumentParser(description="Recherche crt.sh")

parser.add_argument("domain", help="Domaine cible")

args = parser.parse_args()

domain = args.domain

url = f"https://crt.sh/?q=%.{domain}&output=json"

try:
    response = requests.get(url, timeout=15)

    if response.status_code != 200:
        print(f"Erreur HTTP : {response.status_code}")
        exit()

    data = response.json()

    subdomains = set()

    for entry in data:
        names = entry.get("name_value", "")

        for sub in names.split("\n"):
            sub = sub.strip()

            if sub.endswith(domain):
                subdomains.add(sub)

    print(f"\n[+] {len(subdomains)} sous-domaines trouvés\n")

    for sub in sorted(subdomains):
        print(sub)

except requests.exceptions.RequestException as e:
    print("Erreur réseau :", e)