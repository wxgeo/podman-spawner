# Utilisation de pod, interface pour Podman

`pod` permet de générer à la volée des conteneurs.

## Sommaire

- [Avant de commencer](#avant-de-commencer)
- [Utilisation de `pod`](#utilisation-de-pod)
- [Utilisation de Podman (facultatif)](#utilisation-de-podman-facultatif)

## Avant de commencer

`pod` est une surcouche de Podman. Il faut donc commencer par installer Podman (alternative à Docker).

Pour l'installer :

```
    sudo apt install podman containers-storage
```

Le package `containers-storage` n'est pas strictement indispensable, mais il accélère considérablement
la génération d'images.

Vérifier que `podman info | grep graphDriverName` renvoie bien maintenant `overlay` (et non `vfs` par défaut).

Pour avoir accès au dépôt par défaut de Docker via Podman,
il faut maintenant configurer les registres de conteneurs :

```
    mkdir ~/.config/containers/
    echo 'unqualified-search-registries = ["docker.io"]' >> ~/.config/containers/registries.conf
```

## Utilisation de `pod`

### Installation

Si besoin, installer `uv`:

```
    curl -LsSf https://astral.sh/uv/install.sh | sh
```

Aller ensuite dans le dossier principal de `pod`, puis taper :

```
    uv tool install -e .
```

La commande `pod` est maintenant disponible pour l'utilisateur courant.

### Commandes

`pod` permet de générer à la volée un conteneur pour chaque test (groupe + version).

- Avant toute chose, il faut commencer par générer une image (template), qui servira ensuite de base
  pour tous les différents conteneurs. Cette image est générée à partir d'un fichier Dockerfile.

On va pour cela générer un dossier `pod-build`.

```
    pod init
```

On peut maintenant éditer le contenu de ce dossier et le mettre à jour.

Ensuite, on construit l'image :

```
    pod build
```

- Pour créer ou activer un conteneur :

```
    pod go <nom>
```

- Pour détruire un conteneur :

```
    pod rm <nom>
```

- Pour détruire tous les conteneurs vérifiant une regex :

```
    pod purge <regex>
```

- Pour détruire l'ensemble des conteneurs :

```
    pod purge-all
```

Enfin, `pod info <nom>` permet d'avoir des infos sur le conteneur ciblé, et `pod list` permet d'avoir la
liste des conteneurs.

## Utilisation de Podman (facultatif)

Podman s'utilise pratiquement comme Docker (mêmes commandes),
mais sans avoir besoin des permissions `root`.

### Création d'une image

On suppose Podman correctement installé et configuré.

On commence par générer une image,
puis on va l'utiliser pour démarrer des conteneurs
(un par projet étudiant, pour les isoler).

La génération de l'image se fait à partir du fichier `Dockerfile`,
en partant d'une version allégée de Debian 13.

Nous nommons `sae` notre image. Allez dans le répertoire contenant le `Dockerfile`, puis exécutez :

```
    podman build -t sae:latest .
```

Pour tester l'image (en permettant d'exécuter des applications graphiques) :

```
    podman run -it --rm --env="DISPLAY" --net=host sae:latest
```

Pour faciliter les choses, un Makefile a été défini.

``` 
    make build
    make test
```

La commande `podman images` permet de lister toutes les images existantes
(y compris les images temporaires correspondant aux couches successives
ayant servi à la création de notre image finale `sae`).

L'image qui nous intéresse s'appelle `localhost/sae` (tagguée `latest`) :

```
    podman images | grep localhost/sae
```

### Lancement d'une image

Pour démarrer un conteneur en arrière-plan à partir de l'image, on utilise la commande suivante :

```
    podman run -d -t localhost/sae:latest
```

En lui donnant un nom :

```
    podman run -d -t --name HELLO localhost/sae:latest
```

La liste des conteneurs démarrés s'obtient à l'aide de la commande `ps`.
Pour avoir ceux correspondant à notre image `sae` :

```
    podman ps | grep localhost/sae
```

Si l'on veut juste les identifiants :

```
    podman ps|grep localhost/sae|cut -d" " -f1
```

(Pour avoir l'inventaire de *tous* les conteneurs (dead or alive !), on utilise `podman ps -a`.)

Pour relancer un conteneur qui a quitté :

```
    podman start HELLO
```

Le conteneur redémarre en arrière-plan, il faut donc utiliser `podman attach HELLO` si besoin.

### Copie des fichiers

Si le conteneur s'appelle `HELLO`, on copie les fichiers locaux dessus via :

```
    podman cp ../rendus/0.1/a/ HELLO:/usr/src/app/
```

