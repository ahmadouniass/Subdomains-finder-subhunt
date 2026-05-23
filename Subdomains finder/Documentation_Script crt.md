# Documentation — Script crt.sh

## Description
Ce script Python interroge l’API de crt.sh afin de récupérer les sous-domaines d’un domaine à partir des logs Certificate Transparency.

## Dépendances

```bash
pip install requests
````

---

## Utilisation

```bash
python crtsh.py example.com
```

---

## Fonctionnement

Le script :

1. envoie une requête à crt.sh ;
2. récupère les résultats JSON ;
3. extrait les sous-domaines ;
4. supprime les doublons ;
5. affiche les résultats.

---

## URL utilisée

```text
https://crt.sh/?q=%.example.com&output=json
```

* `%` = wildcard
* `output=json` = réponse JSON

---

## Exemple de sortie

```text
api.example.com
mail.example.com
vpn.example.com
www.example.com
```

---

## Cas d’usage

* OSINT
* Bug bounty
* Reconnaissance
* Cartographie d’infrastructure

---

## Limitations

* seuls les domaines ayant un certificat apparaissent ;
* certains résultats peuvent être anciens ;
* crt.sh peut être lent.

---

## Outils complémentaires

* Amass
* Subfinder
* httpx
* Nmap
