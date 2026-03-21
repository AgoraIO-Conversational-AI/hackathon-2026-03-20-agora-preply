#!/bin/bash
# Create SSM parameters for Preply Loop
# Run once before terraform apply
set -e

PREFIX="/preply-loop/dev"
REGION="${AWS_REGION:-us-east-1}"

echo "Creating SSM parameters under $PREFIX"
echo "Make sure you have the right values ready."
echo ""

# Generate random values for secrets
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DB_PASSWORD=$(openssl rand -base64 24)

put() {
    aws ssm put-parameter \
        --name "$PREFIX/$1" \
        --value "$2" \
        --type SecureString \
        --overwrite \
        --region "$REGION" > /dev/null
    echo "  $1 ✓"
}

echo "Auto-generated secrets:"
put "SECRET_KEY" "$SECRET_KEY"
put "DATABASE_USERNAME" "preplyuser"
put "DATABASE_PASSWORD" "$DB_PASSWORD"

echo ""
echo "Enter your API keys (or press Enter to skip):"

read -p "  ANTHROPIC_API_KEY: " val
[ -n "$val" ] && put "ANTHROPIC_API_KEY" "$val"

read -p "  OPENAI_API_KEY: " val
[ -n "$val" ] && put "OPENAI_API_KEY" "$val"

read -p "  CLASSTIME_ADMIN_TOKEN: " val
[ -n "$val" ] && put "CLASSTIME_ADMIN_TOKEN" "$val"

read -p "  CLASSTIME_ORG_ID: " val
[ -n "$val" ] && put "CLASSTIME_ORG_ID" "$val"

read -p "  CLASSTIME_SCHOOL_ID: " val
[ -n "$val" ] && put "CLASSTIME_SCHOOL_ID" "$val"

echo ""
echo "Agora (from https://console.agora.io):"

read -p "  AGORA_APP_ID: " val
[ -n "$val" ] && put "AGORA_APP_ID" "$val"

read -p "  AGORA_APP_CERTIFICATE: " val
[ -n "$val" ] && put "AGORA_APP_CERTIFICATE" "$val"

read -p "  AGORA_CUSTOMER_ID: " val
[ -n "$val" ] && put "AGORA_CUSTOMER_ID" "$val"

read -p "  AGORA_CUSTOMER_SECRET: " val
[ -n "$val" ] && put "AGORA_CUSTOMER_SECRET" "$val"

echo ""
echo "Avatar (Anam - https://app.anam.ai):"

read -p "  AVATAR_API_KEY: " val
[ -n "$val" ] && put "AVATAR_API_KEY" "$val"

read -p "  AVATAR_ID: " val
[ -n "$val" ] && put "AVATAR_ID" "$val"

read -p "  AVATAR_VENDOR [anam]: " val
put "AVATAR_VENDOR" "${val:-anam}"

echo ""
echo "ElevenLabs (TTS):"

read -p "  ELEVENLABS_API_KEY: " val
[ -n "$val" ] && put "ELEVENLABS_API_KEY" "$val"

read -p "  ELEVENLABS_VOICE_ID [cgSgspJ2msm6clMCkdW9]: " val
put "ELEVENLABS_VOICE_ID" "${val:-cgSgspJ2msm6clMCkdW9}"

echo ""
echo "Thymia (voice biomarkers - https://portal.thymia.ai):"

read -p "  THYMIA_API_KEY: " val
[ -n "$val" ] && put "THYMIA_API_KEY" "$val"

read -p "  THYMIA_BASE_URL [https://api.thymia.ai]: " val
put "THYMIA_BASE_URL" "${val:-https://api.thymia.ai}"

echo ""
echo "Temporal Cloud (sign up at cloud.temporal.io):"

read -p "  TEMPORAL_HOST (e.g. us-east-1.aws.api.temporal.io:7233): " val
[ -n "$val" ] && put "TEMPORAL_HOST" "$val"

read -p "  TEMPORAL_NAMESPACE: " val
[ -n "$val" ] && put "TEMPORAL_NAMESPACE" "$val"

read -p "  TEMPORAL_API_KEY: " val
[ -n "$val" ] && put "TEMPORAL_API_KEY" "$val"

echo ""
echo "Done! Now run:"
echo "  cd terraform && terraform init && terraform workspace new dev && terraform apply"
