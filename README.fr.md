# PixOps OS

**Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform**

PixOps OS est une plateforme d'operations de paiement en temps reel pour les entreprises au Bresil, connectant Pix, banques, terminaux carte, PSP et acquereurs dans un ledger unifie oriente evenements pour la reconciliation, l'anti-fraude et l'intelligence financiere.

## Pourquoi Des Entreprises Internationales Operent au Bresil

Les entreprises internationales operent au Bresil car le pays combine:

- un des plus grands volumes de paiement au monde,
- une forte adoption digitale, acceleree par Pix,
- une forte demande PME/entreprise en reconciliation et controle,
- un ecosysteme fragmente entre banques, PSP, acquereurs et gateways.

Pour les acteurs globaux, le Bresil est strategique: grande echelle, forte complexite operationnelle et besoin clair de pilotage financier en temps reel.

## Positionnement Produit

- Ce n'est pas une banque et ne remplace pas une institution financiere.
- Couche operationnelle au-dessus des banques et fournisseurs de paiement.
- Ne promet pas de prevenir 100% des fraudes.
- Vise a reduire fraude operationnelle, faux justificatifs, erreur humaine et ecarts de reconciliation.

## Perimetre MVP

- onboarding multi-tenant (tenant, entreprise, magasin, operateur, caisse),
- flux vente -> payment intent -> charge Pix -> webhook -> reconciliation,
- event store append-only avec hash chain,
- ecritures ledger de base en logique double-entry,
- moteur initial de regles anti-fraude,
- dashboard operationnel temps reel,
- API publique pour tiers.

## Demarrage Rapide

```bash
docker compose up --build
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Documentation Technique

- [Architecture](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/architecture.md)
- [API](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/api.md)
- [Catalogue d'evenements](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/event-catalog.md)
- [Securite](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/security.md)
