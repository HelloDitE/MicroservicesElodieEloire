# Rapport TP1 : Découverte de Terraform et déploiement Docker

## 1. Identification et utilisation des variables

### Variables définies
* **`service_name`** : Elle sert à définir le nom logique du microservice (par défaut `"catalog"`).
* **`external_port`** : Elle définit le port par lequel on accède au site depuis notre ordinateur (par défaut `8081`).

### Utilisation dans le conteneur
Elles sont injectées dynamiquement grâce à la syntaxe `${var.nom_de_la_variable}` :
1.  **Pour le nom du conteneur** : Terraform utilise `"${var.service_name}-service"`, ce qui deviendra `"catalog-service"` une fois construit.
2.  **Pour les ports** : Terraform utilise `var.external_port` pour configurer le port externe (`8081`).
3.  **Pour les réglages internes (Env)** : La variable est réutilisée pour créer une variable d'environnement `SERVICE_NAME=catalog` à l'intérieur du conteneur.

> **En résumé :** C'est du "chercher-remplacer" automatique. Si on change la variable en haut du fichier, le nom du conteneur, son port et sa configuration interne changent tous en même temps sans risque d'erreur.

---

## 2. Rôle du réseau Docker et séparation des ressources

### Rôle de `docker_network.ecommerce`
Cette ressource crée un réseau virtuel privé nommé `ecommerce-net`. C'est comme installer un switch ou un routeur virtuel dédié au projet.

### Pourquoi est-il défini séparément du conteneur ?
C'est pour garantir l'indépendance des ressources :
* **Cycle de vie différent** : Le réseau est l'infrastructure de base (la route), tandis que les conteneurs sont les applications (les voitures). On peut casser et remplacer une voiture (le conteneur) sans avoir besoin de détruire la route (le réseau).
* **Partage** : Comme indiqué dans le scénario du TP, ce réseau pourra être réutilisé par d'autres microservices (panier, commande) plus tard. S'il était défini *dans* le conteneur catalogue, le réseau disparaîtrait si on supprimait le catalogue, coupant la connexion pour tous les autres services.

---

## 3. Comparaison : Terraform vs Docker Compose vs Bash

**Terraform** permet un déploiement déclaratif, reproductible, versionnable et contrôlé, contrairement à Docker Compose ou Bash qui exécutent seulement des commandes impératives ou limitées.

| Critère / Outil | Terraform | Docker Compose | Scripts Bash + Docker CLI |
| :--- | :--- | :--- | :--- |
| **Approche** | **Déclarative**<br>(« je décris l’état final ») | **Déclarative** mais limitée | **Impérative**<br>(« j’exécute des commandes ») |
| **But principal** | Gérer une infrastructure complète (IaC) | Lancer des conteneurs localement | Automatiser manuellement des commandes |
| **Contrôle du cycle de vie** | Complet : `init` → `plan` → `apply` → `destroy` | Start/stop/recreate sans contrôle fin | Dépend des commandes écrites |
| **Prévisualisation** | `terraform plan` indique les changements | Impossible | Impossible |
| **Gestion d’un état** | **Oui (State file)**<br>Permet de savoir ce qui existe réellement | Non | Non |
| **Idempotence** | Très fort | Bon mais limité | Variable (risque d’erreur humaine) |
| **Gestion des dépendances** | Automatique (réseaux, conteneurs, volumes…) | Basique | À coder soi-même |
| **Versionnage Git** | Optimal : fichiers `.tf` = IaC | Possible, mais pas du vrai IaC | Scripts fragiles et peu lisibles |
| **Extensibilité Cloud** | Très forte (AWS, Azure, GCP, Kubernetes…) | Limité au local ou Swarm | Aucune |
| **Reproductibilité** | Environnement 100 % reproductible | Globalement bon | Dépend de l’environnement local |

---

## 4. Généralisation pour plusieurs microservices

Pour déployer automatiquement plusieurs microservices (catalogue, panier, commande, etc.) avec un seul `terraform apply`, voici la démarche :

1.  **Créer un `docker_image` et un `docker_container` par microservice** :
    * Un bloc pour `auth_service`
    * Un bloc pour `orders_service`
    * Un bloc pour `gateway_service`, etc.
2.  **Réutiliser le même réseau Docker** :
    * Tous les conteneurs se connectent au réseau `ecommerce-net` déjà créé par Terraform via le bloc `networks_advanced`.
3.  **Paramétrer chaque service avec des variables** :
    * Utiliser des variables pour le nom du service, le port externe, l'image et les variables d’environnement.

**Résultat :** Lancer tout le projet avec une seule commande :
```bash
terraform apply
