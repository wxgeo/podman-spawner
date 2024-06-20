# Utilisation de Podman pour les SAÉ

## Utilisation de Podman
### Avant de commencer
Podman s'utilise pratiquement comme Docker (mêmes commandes), 
mais sans avoir besoin des permissions `root`.

Pour l'installer :
```
    sudo apt install podman containers-storage
```

Le package `containers-storage` n'est pas strictement indispensable, mais il accélère considérablement la génération d'images.

Vérifier que `podman info | grep graphDriverName` renvoie bien `overlay` (et non `vfs` par défaut).

Pour avoir accès au dépôt par défaut de Docker via Podman, 
il faut maintenant configurer les registres de containeurs :
```
    mkdir ~/.config/containers/
    echo 'unqualified-search-registries = ["docker.io"]' >> ~/.config/containers/registries.conf
```

On commence ensuite par générer une image, 
puis on va l'utiliser pour démarrer des conteneurs 
(un par projet étudiant, pour les isoler).


### Création d'une image
La génération de l'image se fait à partir du fichier `Dockerfile`, 
en partant d'une version allégée de Debian 11.

Nous nommons `sae` notre image.
```
    podman build -t sae:latest
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

## Automatisation
Nous allons maintenant générer à la volée un containeur pour chaque test (groupe + version).

Le script python `pod` facilitera les choses.

Pour créer ou activer un conteneur :

```
    pod go <groupe> <version>
```

Pour détruire un conteneur :
```
    pod rm <group> <version>
```





