# L'image de base. C'est une version très allégée d'Ubuntu.
FROM bitnami/minideb:bookworm

# Choix du répertoire courant du conteneur.
WORKDIR /usr/src/app

ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
# Installation des dépendences.
# Par défaut, il n'y a pas de navigateur, on installe donc Firefox.
# Ne pas installer la version de base de firefox (qui utilise snap !)
RUN apt update; apt upgrade -y
RUN install_packages openjdk-17-jre openjdk-17-jdk firefox-esr ipython3 \
    bash-completion command-not-found python3 git tree locales nano \
    xdg-utils python3-pip python3-venv pipx
RUN apt update; apt upgrade -y
RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \
    locale-gen en_US.UTF-8

# Installation de pipx
# RUN python3 -m pip install --user pipx && \
#    python3 -m pipx ensurepath

# ----------------------------------------------------
# Installez éventuellement vos propres dépendances ici
# RUN apt-get install -y mon_paquet
# ----------------------------------------------------

# Ajout de Junit 5
# ADD https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/1.13.1/junit-platform-console-standalone-1.13.1.jar /root/junit

# Ajout de delta (outil de diff)
RUN mkdir /root/assets
COPY assets/* /root/assets
RUN dpkg -i /root/assets/git-delta_0.18.2_amd64.deb
RUN mkdir /root/prototype && tar xzf /root/assets/edt.tar.gz -C /root/prototype
RUN cd /root/prototype/edt && pipx install -e .
# Copier les fichiers dans le conteneur.

#COPY launch.py /usr/bin/launch
COPY scripts/* /usr/local/bin
COPY config-files/* /root
RUN chmod u+x /usr/local/bin/*
# For pipx (`pipx ensurepath` does *not* work).
RUN echo 'export PATH="$PATH:/root/.local/bin"' >> /root/.bashrc
# --------------------------------
# Partie à adapter
#COPY bin bin
# --------------------------------



