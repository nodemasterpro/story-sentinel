#!/bin/bash

# Script de diagnostic pour détecter l'installation Story

echo "=== Story Sentinel - Diagnostic d'Installation ==="
echo

echo "1. Recherche des services Story :"
systemctl list-units --type=service | grep -E '(story|geth)' || echo "Aucun service Story trouvé"
echo

echo "2. Recherche des binaires Story :"
for path in "/usr/local/bin/story" "/root/go/bin/story" "/home/*/go/bin/story"; do
    if [[ -x "$path" ]]; then
        echo "✓ Story trouvé: $path"
        echo "  Version: $($path version 2>/dev/null || echo 'Erreur')"
    fi
done

for path in "/usr/local/bin/story-geth" "/usr/local/bin/geth" "/root/go/bin/geth" "/home/*/go/bin/geth"; do
    if [[ -x "$path" ]]; then
        echo "✓ Story-Geth trouvé: $path" 
        echo "  Version: $($path version 2>/dev/null | head -1 || echo 'Erreur')"
    fi
done

echo
echo "3. Ports en écoute :"
netstat -tlnp 2>/dev/null | grep -E '(26657|22657|8545|2245)' || echo "Aucun port Story détecté"

echo
echo "4. Répertoires Story :"
for dir in "/root/.story" "/home/*/.story"; do
    if [[ -d "$dir" ]]; then
        echo "✓ Story home trouvé: $dir"
    fi
done

echo
echo "5. Processus Story en cours :"
ps aux | grep -E '(story|geth)' | grep -v grep || echo "Aucun processus Story détecté"