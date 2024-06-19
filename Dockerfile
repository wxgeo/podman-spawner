# L'image de base. C'est une version très allégée d'Ubuntu.
FROM bitnami/minideb:bullseye

# Choix du répertoire courant du conteneur.
WORKDIR /usr/src/app

# Installation des dépendences.
# Par défaut, il n'y a pas de navigateur, on installe donc Firefox.
# Ne pas installer la version de base de firefox (qui utilise snap !)
RUN install_packages openjdk-17-jre firefox-esr ipython3 bash-completion command-not-found python git

# ----------------------------------------------------
# Installez éventuellement vos propres dépendances ici
# RUN apt-get install -y mon_paquet
# ----------------------------------------------------

# Copier les fichiers dans le conteneur.
#COPY launch.py /usr/bin/launch
COPY data/start.bash .start

# --------------------------------
# Partie à adapter
#COPY bin bin
# --------------------------------

# Commande à lancer après l'installation
CMD ["/bin/bash", ".start"]

