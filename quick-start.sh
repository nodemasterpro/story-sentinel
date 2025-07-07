#!/bin/bash

# Story Sentinel - Quick Start Script
# Installation et configuration rapide en une commande

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Story Sentinel - Quick Start          ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Ce script doit être exécuté en tant que root${NC}" 
   echo "Usage: sudo bash quick-start.sh"
   exit 1
fi

# Step 1: Download and install
echo -e "${YELLOW}Étape 1: Téléchargement et installation...${NC}"
if [ ! -f "install.sh" ]; then
    echo "Téléchargement des fichiers..."
    curl -sSL -o install.sh https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/install.sh
    curl -sSL -o test-installation.sh https://raw.githubusercontent.com/nodemasterpro/story-sentinel/main/test-installation.sh
    chmod +x install.sh test-installation.sh
fi

echo "Lancement de l'installation..."
bash install.sh

echo -e "${GREEN}✓ Installation terminée${NC}"
echo

# Step 2: Test installation
echo -e "${YELLOW}Étape 2: Test de l'installation...${NC}"
if bash test-installation.sh; then
    echo -e "${GREEN}✓ Tests réussis${NC}"
else
    echo -e "${RED}✗ Certains tests ont échoué${NC}"
    echo "Consultez les logs pour plus d'informations."
fi
echo

# Step 3: Configuration wizard
echo -e "${YELLOW}Étape 3: Assistant de configuration...${NC}"

# Discord or Telegram choice
echo "Choisissez votre méthode de notification:"
echo "1) Discord Webhook"
echo "2) Telegram Bot"
echo "3) Passer (configurer plus tard)"
read -p "Votre choix (1-3): " notification_choice

case $notification_choice in
    1)
        read -p "Entrez votre Discord Webhook URL: " discord_webhook
        if [[ -n "$discord_webhook" ]]; then
            sed -i "s|DISCORD_WEBHOOK=|DISCORD_WEBHOOK=$discord_webhook|" /etc/story-sentinel/.env
            echo -e "${GREEN}✓ Discord configuré${NC}"
        fi
        ;;
    2)
        read -p "Entrez votre Telegram Bot Token: " tg_token
        read -p "Entrez votre Telegram Chat ID: " tg_chat_id
        if [[ -n "$tg_token" && -n "$tg_chat_id" ]]; then
            sed -i "s|TG_BOT_TOKEN=|TG_BOT_TOKEN=$tg_token|" /etc/story-sentinel/.env
            sed -i "s|TG_CHAT_ID=|TG_CHAT_ID=$tg_chat_id|" /etc/story-sentinel/.env
            echo -e "${GREEN}✓ Telegram configuré${NC}"
        fi
        ;;
    3)
        echo -e "${YELLOW}Configuration des notifications ignorée${NC}"
        ;;
esac

# Operation mode
echo
echo "Choisissez le mode de fonctionnement:"
echo "1) Manuel (mises à jour sur commande)"
echo "2) Automatique (mises à jour automatiques des patches)"
read -p "Votre choix (1-2): " mode_choice

case $mode_choice in
    1)
        sed -i "s|MODE=manual|MODE=manual|" /etc/story-sentinel/.env
        echo -e "${GREEN}✓ Mode manuel configuré${NC}"
        ;;
    2)
        sed -i "s|MODE=manual|MODE=auto|" /etc/story-sentinel/.env
        echo -e "${GREEN}✓ Mode automatique configuré${NC}"
        ;;
esac

echo

# Step 4: Start service
echo -e "${YELLOW}Étape 4: Démarrage du service...${NC}"

systemctl start story-sentinel
systemctl enable story-sentinel

# Wait a moment for service to start
sleep 3

if systemctl is-active --quiet story-sentinel; then
    echo -e "${GREEN}✓ Service démarré avec succès${NC}"
else
    echo -e "${RED}✗ Échec du démarrage du service${NC}"
    echo "Consultez les logs: sudo journalctl -u story-sentinel -f"
fi

echo

# Step 5: Test functionality
echo -e "${YELLOW}Étape 5: Test de fonctionnement...${NC}"

# Test CLI
if story-sentinel status > /dev/null 2>&1; then
    echo -e "${GREEN}✓ CLI fonctionnel${NC}"
else
    echo -e "${RED}✗ Problème avec CLI${NC}"
fi

# Test API
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API accessible${NC}"
else
    echo -e "${YELLOW}⚠ API non accessible (normal si services Story ne sont pas en cours d'exécution)${NC}"
fi

echo

# Summary and next steps
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Installation Terminée !               ${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "${GREEN}🎉 Story Sentinel est maintenant installé et opérationnel !${NC}"
echo
echo -e "${YELLOW}Informations importantes:${NC}"
echo "  • Service: story-sentinel"
echo "  • Configuration: /etc/story-sentinel/"
echo "  • Logs: /var/log/story-sentinel/"
echo "  • API: http://localhost:8080"
echo
echo -e "${YELLOW}Commandes utiles:${NC}"
echo "  story-sentinel status          # Vérifier le statut"
echo "  story-sentinel check-updates   # Vérifier les mises à jour"
echo "  sudo systemctl status story-sentinel  # Statut du service"
echo "  sudo journalctl -u story-sentinel -f  # Logs en temps réel"
echo
echo -e "${YELLOW}API Endpoints:${NC}"
echo "  http://localhost:8080/health           # Santé"
echo "  http://localhost:8080/status           # Statut détaillé"
echo "  http://localhost:8080/next-upgrade.ics # Calendrier"
echo
echo -e "${YELLOW}Configuration avancée:${NC}"
echo "  sudo nano /etc/story-sentinel/.env     # Variables d'environnement"
echo "  sudo nano /etc/story-sentinel/config.yaml  # Configuration principale"
echo

# Show current status
echo -e "${YELLOW}Statut actuel:${NC}"
story-sentinel status || echo "Vérifiez que vos services Story sont en cours d'exécution"

echo
echo -e "${GREEN}Installation et configuration terminées avec succès !${NC}"