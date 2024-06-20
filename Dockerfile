# L'image de base. C'est une version très allégée d'Ubuntu.
FROM bitnami/minideb:bullseye

# Choix du répertoire courant du conteneur.
WORKDIR /usr/src/app

ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
# Installation des dépendences.
# Par défaut, il n'y a pas de navigateur, on installe donc Firefox.
# Ne pas installer la version de base de firefox (qui utilise snap !)
RUN apt update; apt upgrade
RUN install_packages openjdk-17-jre openjdk-17-jdk firefox-esr ipython3 \
    bash-completion command-not-found python git tree locales
RUN apt update; apt upgrade
RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \
    locale-gen en_US.UTF-8
# ----------------------------------------------------
# Installez éventuellement vos propres dépendances ici
# RUN apt-get install -y mon_paquet
# ----------------------------------------------------

# Copier les fichiers dans le conteneur.
#COPY launch.py /usr/bin/launch
COPY scripts/start.bash .start
COPY scripts/compile_all.bash compile_all
COPY scripts/run.bash run

# --------------------------------
# Partie à adapter
#COPY bin bin
# --------------------------------

# Commande à lancer après l'installation
CMD ["/bin/bash", ".start"]

