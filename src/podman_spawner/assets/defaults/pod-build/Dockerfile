# L'image de base. C'est une version très allégée de Debian.
FROM bitnami/minideb:trixie

ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
# Installation des dépendences.
# Par défaut, il n'y a pas de navigateur, on installe donc Firefox.
# Ne pas installer la version de base de firefox (qui utilise snap !)
RUN apt update; apt upgrade -y
RUN install_packages openjdk-21-jre openjdk-21-jdk junit5 firefox-esr ipython3 \
    bash-completion command-not-found python3 git tree locales nano passwd sudo \
    xdg-utils git-delta curl
RUN apt update; apt upgrade -y
RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \
    locale-gen en_US.UTF-8

# Ajout de Junit 5
# ADD https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/1.13.1/junit-platform-console-standalone-1.13.1.jar /root/junit


# Installation de uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Utilisateur par défaut
ARG USER=tester
# Regex check: Allow only alphanumeric characters and underscores
RUN echo "$USER" | grep -qE '^[a-zA-Z_][a-zA-Z0-9_]*$' || \
    (echo "ERROR: Invalid username format detected! ($USER)" && exit 1)
# Create the user and add to the sudo group
RUN useradd -m -s /bin/bash "$USER" && usermod -aG sudo "$USER"
# Allow the user to run sudo without a password
RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USER
WORKDIR /home/$USER

# Copy defaults user's home files.
COPY "home-dir/" "/home/$USER"
RUN ls -a "/home/$USER" && bash "/home/$USER/on_build.bash"




